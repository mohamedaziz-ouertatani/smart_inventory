"""
MLflow-tracked training with ETS and ARIMA/SARIMA forecasting.
Per SKU-location, fits seasonal naive, ETS, and ARIMA models, performs rolling backtest,
selects best model by WAPE, logs to MLflow, and writes forecasts/metrics to database.
"""
from datetime import date, timedelta
import argparse
import uuid
import os
from typing import List, Tuple, Dict, Optional
import warnings
import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
import mlflow
import mlflow.pyfunc
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from jobs.utils.db import get_conn

# Constants
H_DEFAULT = 4
BACKTEST_WEEKS = 26
FALLBACK_WINDOW = 8
MIN_HISTORY = 52  # Minimum weeks of history for ETS/ARIMA

warnings.filterwarnings('ignore')  # Suppress statsmodels warnings


def fetch_latest_week(conn) -> date:
    """Get the latest week from curated.weekly_demand."""
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(week_start_date) FROM curated.weekly_demand;")
        row = cur.fetchone()
        if not row or not row[0]:
            raise RuntimeError("No weekly demand data found")
        return row[0]


def fetch_weekly_demand(conn) -> List[Tuple[str, str, date, int]]:
    """Fetch all weekly demand data."""
    sql = """
      SELECT sku_id, location_id, week_start_date, units_sold
      FROM curated.weekly_demand
      ORDER BY sku_id, location_id, week_start_date
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def group_by_sku_loc(rows: List[Tuple[str, str, date, int]]) -> Dict[Tuple[str,str], List[Tuple[date,int]]]:
    """Group time series by (sku_id, location_id)."""
    data: Dict[Tuple[str,str], List[Tuple[date,int]]] = {}
    for sku_id, loc_id, ws, units in rows:
        data.setdefault((sku_id, loc_id), []).append((ws, units))
    return data


def seasonal_naive_forecast(ts: List[Tuple[date,int]], target_week: date) -> float:
    """Seasonal naive forecast: uses value from 52 weeks ago, or recent average if unavailable."""
    ref_week = target_week - timedelta(weeks=52)
    values = {w:u for (w,u) in ts}
    if ref_week in values:
        return float(values[ref_week])
    prior_weeks = [w for (w,_) in ts if w < target_week]
    prior_weeks.sort()
    recent = prior_weeks[-FALLBACK_WINDOW:] if len(prior_weeks) >= FALLBACK_WINDOW else prior_weeks
    avg = np.mean([values[w] for w in recent]) if recent else 0.0
    return float(max(avg, 0.0))


def fit_ets(series: pd.Series, seasonal_periods: int = 52) -> Optional[ExponentialSmoothing]:
    """Fit ETS model (Exponential Smoothing) with additive seasonality."""
    try:
        if len(series) < seasonal_periods + 1:
            return None
        model = ExponentialSmoothing(
            series,
            seasonal_periods=seasonal_periods,
            trend='add',
            seasonal='add',
            damped_trend=True
        )
        fitted = model.fit(optimized=True, use_brute=False)
        return fitted
    except Exception:
        return None


def fit_sarima(series: pd.Series, seasonal_periods: int = 52) -> Optional[SARIMAX]:
    """Fit SARIMA model with simple order (1,0,0)x(1,0,0,52)."""
    try:
        if len(series) < seasonal_periods + 2:
            return None
        model = SARIMAX(
            series,
            order=(1, 0, 0),
            seasonal_order=(1, 0, 0, seasonal_periods),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        fitted = model.fit(disp=False, maxiter=50)
        return fitted
    except Exception:
        return None


def rolling_backtest_model(
    ts_sorted: List[Tuple[date, int]],
    latest_week: date,
    model_fn,
    seasonal_periods: int = 52
) -> Tuple[List[Tuple[date, float, float, float]], float]:
    """
    Perform rolling-origin backtest for a given model function.
    Returns list of (week, actual, forecast, residual) and residual_std.
    """
    if not ts_sorted:
        return [], 0.0
    
    values_dict = {w: u for (w, u) in ts_sorted}
    weeks = sorted([w for (w, _) in ts_sorted])
    per_week = []
    
    # Compute cutoff for backtest period (last BACKTEST_WEEKS)
    cutoff = latest_week - timedelta(weeks=BACKTEST_WEEKS)
    
    for w in weeks:
        if w >= cutoff and w < latest_week:
            target = w + timedelta(weeks=1)
            if target in values_dict:
                # Train on data up to w
                train_ts = [(wk, val) for (wk, val) in ts_sorted if wk <= w]
                if len(train_ts) < seasonal_periods:
                    continue
                
                # Create series
                train_series = pd.Series(
                    [val for (_, val) in train_ts],
                    index=pd.to_datetime([wk for (wk, _) in train_ts])
                )
                
                # Fit model and forecast 1 step
                try:
                    fitted = model_fn(train_series, seasonal_periods)
                    if fitted is None:
                        continue
                    forecast = fitted.forecast(steps=1)
                    if isinstance(forecast, pd.Series):
                        f = float(forecast.iloc[0])
                    else:
                        f = float(forecast)
                    f = max(0.0, f)
                except Exception:
                    continue
                
                a = float(values_dict[target])
                residual = a - f
                per_week.append((target, a, f, residual))
    
    residuals = [r for (_, _, _, r) in per_week]
    residual_std = float(np.std(residuals, ddof=1)) if len(residuals) >= 2 else (
        float(abs(residuals[0])) if residuals else 0.0
    )
    return per_week, residual_std


def rolling_backtest_seasonal_naive(
    ts_sorted: List[Tuple[date, int]],
    latest_week: date
) -> Tuple[List[Tuple[date, float, float, float]], float]:
    """Perform rolling backtest for seasonal naive."""
    if not ts_sorted:
        return [], 0.0
    
    values_dict = {w: u for (w, u) in ts_sorted}
    weeks = sorted([w for (w, _) in ts_sorted])
    per_week = []
    
    cutoff = latest_week - timedelta(weeks=BACKTEST_WEEKS)
    
    for w in weeks:
        if w >= cutoff and w < latest_week:
            target = w + timedelta(weeks=1)
            if target in values_dict:
                # Train on data up to w
                train_ts = [(wk, val) for (wk, val) in ts_sorted if wk <= w]
                f = seasonal_naive_forecast(train_ts, target)
                a = float(values_dict[target])
                residual = a - f
                per_week.append((target, a, f, residual))
    
    residuals = [r for (_, _, _, r) in per_week]
    residual_std = float(np.std(residuals, ddof=1)) if len(residuals) >= 2 else (
        float(abs(residuals[0])) if residuals else 0.0
    )
    return per_week, residual_std


def compute_metrics(per_week: List[Tuple[date, float, float, float]]) -> Dict[str, float]:
    """Compute aggregate WAPE, sMAPE, bias from per-week results."""
    if not per_week:
        return {"wape": 999.0, "smape": 999.0, "bias": 999.0}
    
    total_abs_error = 0.0
    total_actual = 0.0
    total_smape_denom = 0.0
    total_bias_num = 0.0
    
    for (_, actual, forecast, residual) in per_week:
        total_abs_error += abs(residual)
        total_actual += abs(actual)
        total_smape_denom += (abs(actual) + abs(forecast))
        total_bias_num += (forecast - actual)
    
    wape = total_abs_error / total_actual if total_actual > 0 else 999.0
    smape = (2.0 * total_abs_error) / total_smape_denom if total_smape_denom > 0 else 999.0
    bias = total_bias_num / total_actual if total_actual > 0 else 0.0
    
    return {"wape": wape, "smape": smape, "bias": bias}


def generate_forecast_horizon(
    ts_sorted: List[Tuple[date, int]],
    latest_week: date,
    horizon: int,
    model_fn,
    seasonal_periods: int = 52
) -> List[Tuple[date, float]]:
    """Generate H-week ahead forecasts using fitted model."""
    if not ts_sorted:
        return []
    
    # Train on full history
    train_series = pd.Series(
        [val for (_, val) in ts_sorted],
        index=pd.to_datetime([wk for (wk, _) in ts_sorted])
    )
    
    try:
        fitted = model_fn(train_series, seasonal_periods)
        if fitted is None:
            # Fallback to seasonal naive
            return [(latest_week + timedelta(weeks=h), seasonal_naive_forecast(ts_sorted, latest_week + timedelta(weeks=h))) 
                    for h in range(1, horizon+1)]
        
        forecast = fitted.forecast(steps=horizon)
        if isinstance(forecast, pd.Series):
            forecast_vals = forecast.values
        else:
            forecast_vals = [forecast] if horizon == 1 else list(forecast)
        
        return [(latest_week + timedelta(weeks=h), max(0.0, float(forecast_vals[h-1]))) 
                for h in range(1, horizon+1)]
    except Exception:
        # Fallback to seasonal naive
        return [(latest_week + timedelta(weeks=h), seasonal_naive_forecast(ts_sorted, latest_week + timedelta(weeks=h))) 
                for h in range(1, horizon+1)]


def generate_forecast_horizon_seasonal_naive(
    ts_sorted: List[Tuple[date, int]],
    latest_week: date,
    horizon: int
) -> List[Tuple[date, float]]:
    """Generate H-week ahead forecasts using seasonal naive."""
    return [(latest_week + timedelta(weeks=h), seasonal_naive_forecast(ts_sorted, latest_week + timedelta(weeks=h))) 
            for h in range(1, horizon+1)]


def plot_backtest_results(per_week: List[Tuple[date, float, float, float]], title: str) -> str:
    """Create a plot of actual vs forecast for backtest period."""
    if not per_week:
        return None
    
    weeks = [w for (w, _, _, _) in per_week]
    actuals = [a for (_, a, _, _) in per_week]
    forecasts = [f for (_, _, f, _) in per_week]
    
    plt.figure(figsize=(10, 6))
    plt.plot(weeks, actuals, label='Actual', marker='o')
    plt.plot(weeks, forecasts, label='Forecast', marker='x')
    plt.xlabel('Week')
    plt.ylabel('Units')
    plt.title(title)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save to temp file
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.png')
    plt.savefig(path)
    plt.close()
    os.close(fd)
    return path


def write_batch_run_start(conn, job_type: str) -> uuid.UUID:
    """Start a batch run in ops.batch_run."""
    run_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute("""
          INSERT INTO ops.batch_run (run_id, job_type, status, started_at)
          VALUES (%s, %s, 'running', NOW())
        """, (str(run_id), job_type))
    conn.commit()
    return run_id


def write_batch_run_finish(conn, run_id: uuid.UUID, status: str = 'succeeded', notes: str | None = None):
    """Finish a batch run."""
    with conn.cursor() as cur:
        cur.execute("""
          UPDATE ops.batch_run
          SET status = %s, finished_at = NOW(), notes = COALESCE(%s, notes)
          WHERE run_id = %s
        """, (status, notes, str(run_id)))
    conn.commit()


def insert_metrics(
    conn,
    run_id: uuid.UUID,
    sku_id: str,
    loc_id: str,
    per_week_metrics: List[Tuple[date, float, float, float]],
    model_name: str,
    model_stage: str = 'Production'
):
    """Write per-week backtest metrics to ops.metrics_accuracy."""
    rows = []
    for week, actual, forecast, residual in per_week_metrics:
        wape = float(abs(residual) / (actual if actual != 0 else 1.0))
        denom = (abs(actual) + abs(forecast))
        smape = float((2.0 * abs(residual)) / (denom if denom != 0 else 1.0))
        bias = float((forecast - actual) / (actual if actual != 0 else 1.0))
        rows.append((
            str(run_id), sku_id, loc_id, week, actual, forecast, wape, smape, bias, model_name, model_stage
        ))
    if not rows:
        return
    
    sql = """
      INSERT INTO ops.metrics_accuracy (
        run_id, sku_id, location_id, week_start_date, actual_units, forecast_units, wape, smape, bias, model_name, model_stage
      ) VALUES %s
      ON CONFLICT (run_id, sku_id, location_id, week_start_date) DO UPDATE SET
        actual_units = EXCLUDED.actual_units,
        forecast_units = EXCLUDED.forecast_units,
        wape = EXCLUDED.wape,
        smape = EXCLUDED.smape,
        bias = EXCLUDED.bias,
        model_name = EXCLUDED.model_name,
        model_stage = EXCLUDED.model_stage,
        recorded_at = NOW()
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=10000)
    conn.commit()


def insert_forecasts(
    conn,
    run_id: uuid.UUID,
    sku_id: str,
    loc_id: str,
    horizon_rows: List[Tuple[date, float]],
    residual_std: float,
    model_name: str,
    model_stage: str = 'Production'
):
    """Write horizon forecasts to ops.forecast."""
    rows = []
    for horizon_week, f in horizon_rows:
        rows.append((
            str(run_id), sku_id, loc_id, horizon_week, f, f, residual_std, model_name, model_stage
        ))
    if not rows:
        return
    
    sql = """
      INSERT INTO ops.forecast (
        run_id, sku_id, location_id, horizon_week_start, forecast_units, baseline_units, residual_std, model_name, model_stage
      ) VALUES %s
      ON CONFLICT (run_id, sku_id, location_id, horizon_week_start) DO UPDATE SET
        forecast_units = EXCLUDED.forecast_units,
        baseline_units = EXCLUDED.baseline_units,
        residual_std = EXCLUDED.residual_std,
        model_name = EXCLUDED.model_name,
        model_stage = EXCLUDED.model_stage,
        generated_at = NOW()
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=10000)
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=H_DEFAULT, help="Forecast horizon in weeks (1..8)")
    args = parser.parse_args()
    H = max(1, min(args.horizon, 8))
    
    # MLflow setup
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow_experiment = os.getenv("MLFLOW_EXPERIMENT_NAME", "smart-inventory")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(mlflow_experiment)
    
    with get_conn() as conn:
        run_id = write_batch_run_start(conn, "train_ml")
        latest = fetch_latest_week(conn)
        rows = fetch_weekly_demand(conn)
        grouped = group_by_sku_loc(rows)
        
        forecasts_inserted = 0
        metrics_inserted = 0
        model_selections = []
        
        for (sku_id, loc_id), ts in grouped.items():
            ts_sorted = sorted(ts, key=lambda x: x[0])
            
            # Start MLflow run for this SKU-location
            with mlflow.start_run(run_name=f"{sku_id}_{loc_id}"):
                mlflow.log_param("sku_id", sku_id)
                mlflow.log_param("location_id", loc_id)
                mlflow.log_param("horizon", H)
                mlflow.log_param("backtest_weeks", BACKTEST_WEEKS)
                mlflow.log_param("history_length", len(ts_sorted))
                
                # Fit and evaluate models
                models_results = {}
                
                # 1. Seasonal Naive
                per_week_sn, residual_std_sn = rolling_backtest_seasonal_naive(ts_sorted, latest)
                metrics_sn = compute_metrics(per_week_sn)
                models_results['seasonal_naive'] = {
                    'per_week': per_week_sn,
                    'residual_std': residual_std_sn,
                    'metrics': metrics_sn,
                    'model_name': 'seasonal_naive_v1'
                }
                
                # Log seasonal naive metrics
                mlflow.log_metric("seasonal_naive_wape", metrics_sn['wape'])
                mlflow.log_metric("seasonal_naive_smape", metrics_sn['smape'])
                mlflow.log_metric("seasonal_naive_bias", metrics_sn['bias'])
                
                # 2. ETS (if sufficient history)
                if len(ts_sorted) >= MIN_HISTORY:
                    try:
                        per_week_ets, residual_std_ets = rolling_backtest_model(
                            ts_sorted, latest, fit_ets, seasonal_periods=52
                        )
                        if per_week_ets:
                            metrics_ets = compute_metrics(per_week_ets)
                            models_results['ets'] = {
                                'per_week': per_week_ets,
                                'residual_std': residual_std_ets,
                                'metrics': metrics_ets,
                                'model_name': 'ets_additive_v1'
                            }
                            mlflow.log_metric("ets_wape", metrics_ets['wape'])
                            mlflow.log_metric("ets_smape", metrics_ets['smape'])
                            mlflow.log_metric("ets_bias", metrics_ets['bias'])
                    except Exception as e:
                        mlflow.log_param("ets_error", str(e)[:200])
                
                # 3. SARIMA (if sufficient history)
                if len(ts_sorted) >= MIN_HISTORY:
                    try:
                        per_week_sarima, residual_std_sarima = rolling_backtest_model(
                            ts_sorted, latest, fit_sarima, seasonal_periods=52
                        )
                        if per_week_sarima:
                            metrics_sarima = compute_metrics(per_week_sarima)
                            models_results['sarima'] = {
                                'per_week': per_week_sarima,
                                'residual_std': residual_std_sarima,
                                'metrics': metrics_sarima,
                                'model_name': 'arima_sarima_v1'
                            }
                            mlflow.log_metric("sarima_wape", metrics_sarima['wape'])
                            mlflow.log_metric("sarima_smape", metrics_sarima['smape'])
                            mlflow.log_metric("sarima_bias", metrics_sarima['bias'])
                    except Exception as e:
                        mlflow.log_param("sarima_error", str(e)[:200])
                
                # Model selection: lowest WAPE, tie-break by sMAPE
                best_model_key = None
                best_wape = float('inf')
                best_smape = float('inf')
                
                for key, result in models_results.items():
                    wape = result['metrics']['wape']
                    smape = result['metrics']['smape']
                    if wape < best_wape or (wape == best_wape and smape < best_smape):
                        best_wape = wape
                        best_smape = smape
                        best_model_key = key
                
                if best_model_key is None:
                    best_model_key = 'seasonal_naive'
                
                selected_result = models_results[best_model_key]
                mlflow.log_param("selected_model", best_model_key)
                mlflow.log_metric("selected_wape", best_wape)
                mlflow.log_metric("selected_smape", best_smape)
                
                # Generate horizon forecasts using selected model
                if best_model_key == 'seasonal_naive':
                    horizon_rows = generate_forecast_horizon_seasonal_naive(ts_sorted, latest, H)
                elif best_model_key == 'ets':
                    horizon_rows = generate_forecast_horizon(ts_sorted, latest, H, fit_ets)
                elif best_model_key == 'sarima':
                    horizon_rows = generate_forecast_horizon(ts_sorted, latest, H, fit_sarima)
                else:
                    horizon_rows = generate_forecast_horizon_seasonal_naive(ts_sorted, latest, H)
                
                # Plot backtest results and log artifact
                plot_path = plot_backtest_results(
                    selected_result['per_week'],
                    f"Backtest: {sku_id} {loc_id} ({best_model_key})"
                )
                if plot_path:
                    mlflow.log_artifact(plot_path, "plots")
                    os.remove(plot_path)
                
                # Write to database
                insert_metrics(
                    conn, run_id, sku_id, loc_id,
                    selected_result['per_week'],
                    selected_result['model_name'],
                    'Production'
                )
                metrics_inserted += len(selected_result['per_week'])
                
                insert_forecasts(
                    conn, run_id, sku_id, loc_id,
                    horizon_rows,
                    selected_result['residual_std'],
                    selected_result['model_name'],
                    'Production'
                )
                forecasts_inserted += len(horizon_rows)
                
                model_selections.append(f"{sku_id}-{loc_id}: {best_model_key}")
        
        notes = f"Inserted forecasts={forecasts_inserted}, metrics={metrics_inserted}, horizon={H}, backtest_weeks={BACKTEST_WEEKS}"
        write_batch_run_finish(conn, run_id, status="succeeded", notes=notes)
        print(f"✓ ML training run {run_id} completed.")
        print(f"  {notes}")
        print(f"  Model selections: {len(model_selections)} SKU-locations")
        print(f"  MLflow tracking URI: {mlflow_uri}")


if __name__ == "__main__":
    main()
