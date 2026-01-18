# Baseline training and batch inference (seasonal naive + moving average fallback)
from datetime import date, timedelta
import argparse
import uuid
import math
from typing import List, Tuple, Dict

import numpy as np
import psycopg2
import psycopg2.extras

from jobs.utils.db import get_conn

H_DEFAULT = 4
BACKTEST_WEEKS = 26
FALLBACK_WINDOW = 8

def fetch_latest_week(conn) -> date:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(week_start_date) FROM curated.weekly_demand;")
        row = cur.fetchone()
        if not row or not row[0]:
            raise RuntimeError("No weekly demand data found")
        return row[0]

def fetch_weekly_demand(conn) -> List[Tuple[str, str, date, int]]:
    sql = """
      SELECT sku_id, location_id, week_start_date, units_sold
      FROM curated.weekly_demand
      ORDER BY sku_id, location_id, week_start_date
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()

def group_by_sku_loc(rows: List[Tuple[str, str, date, int]]) -> Dict[Tuple[str,str], List[Tuple[date,int]]]:
    data: Dict[Tuple[str,str], List[Tuple[date,int]]] = {}
    for sku_id, loc_id, ws, units in rows:
        data.setdefault((sku_id, loc_id), []).append((ws, units))
    return data

def seasonal_naive_forecast(ts: List[Tuple[date,int]], target_week: date) -> float:
    ref_week = target_week - timedelta(weeks=52)
    values = {w:u for (w,u) in ts}
    if ref_week in values:
        return float(values[ref_week])
    prior_weeks = [w for (w,_) in ts if w < target_week]
    if not prior_weeks:
        return 0.0
    prior_weeks.sort()
    recent = prior_weeks[-FALLBACK_WINDOW:] if len(prior_weeks) >= FALLBACK_WINDOW else prior_weeks
    avg = np.mean([values[w] for w in recent]) if recent else 0.0
    return float(max(avg, 0.0))

def compute_backtest(ts: List[Tuple[date,int]], latest_week: date) -> Tuple[List[Tuple[date,float,float,float]], float]:
    if not ts:
        return [], 0.0
    values = {w:u for (w,u) in ts}
    weeks = [w for (w,_) in ts]
    weeks.sort()
    per_week = []
    for w in reversed(weeks):
        if w >= latest_week - timedelta(weeks=BACKTEST_WEEKS):
            target = w + timedelta(weeks=1)
            if target in values:
                f = seasonal_naive_forecast(ts, target)
                a = float(values[target])
                residual = a - f
                per_week.append((target, a, f, residual))
    residuals = [r for (_,_,_,r) in per_week]
    residual_std = float(np.std(residuals, ddof=1)) if len(residuals) >= 2 else (float(abs(residuals[0])) if residuals else 0.0)
    return list(reversed(per_week)), residual_std

def write_batch_run_start(conn, job_type: str) -> uuid.UUID:
    run_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute("""
          INSERT INTO ops.batch_run (run_id, job_type, status, started_at)
          VALUES (%s, %s, 'running', NOW())
        """, (str(run_id), job_type))
    conn.commit()
    return run_id

def write_batch_run_finish(conn, run_id: uuid.UUID, status: str = 'succeeded', notes: str | None = None):
    with conn.cursor() as cur:
        cur.execute("""
          UPDATE ops.batch_run
          SET status = %s, finished_at = NOW(), notes = COALESCE(%s, notes)
          WHERE run_id = %s
        """, (status, notes, str(run_id)))
    conn.commit()

def insert_metrics(conn, run_id: uuid.UUID, sku_id: str, loc_id: str, per_week_metrics: List[Tuple[date,float,float,float]]):
    rows = []
    for week, actual, forecast, residual in per_week_metrics:
        wape = float(abs(residual) / (actual if actual != 0 else 1.0))
        denom = (abs(actual) + abs(forecast))
        smape = float((2.0 * abs(residual)) / (denom if denom != 0 else 1.0))
        bias = float((forecast - actual) / (actual if actual != 0 else 1.0))
        rows.append((
            str(run_id), sku_id, loc_id, week, actual, forecast, wape, smape, bias, 'seasonal_naive_v1', 'Production'
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

def insert_forecasts(conn, run_id: uuid.UUID, sku_id: str, loc_id: str, horizon_rows: List[Tuple[date,float]], residual_std: float):
    rows = []
    for horizon_week, f in horizon_rows:
        rows.append((
            str(run_id), sku_id, loc_id, horizon_week, f, f, residual_std, 'seasonal_naive_v1', 'Production'
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

    with get_conn() as conn:
        run_id = write_batch_run_start(conn, "batch_inference")
        latest = fetch_latest_week(conn)
        rows = fetch_weekly_demand(conn)
        grouped = group_by_sku_loc(rows)

        forecasts_inserted = 0
        metrics_inserted = 0

        for (sku_id, loc_id), ts in grouped.items():
            ts_sorted = sorted(ts, key=lambda x: x[0])
            per_week_metrics, residual_std = compute_backtest(ts_sorted, latest)

            insert_metrics(conn, run_id, sku_id, loc_id, per_week_metrics)
            metrics_inserted += len(per_week_metrics)

            horizon_rows: List[Tuple[date,float]] = []
            for h in range(1, H+1):
                target = latest + timedelta(weeks=h)
                f = seasonal_naive_forecast(ts_sorted, target)
                horizon_rows.append((target, max(0.0, f)))
            insert_forecasts(conn, run_id, sku_id, loc_id, horizon_rows, residual_std)
            forecasts_inserted += len(horizon_rows)

        notes = f"Inserted forecasts={forecasts_inserted}, metrics={metrics_inserted}, horizon={H}, backtest_weeks={BACKTEST_WEEKS}"
        write_batch_run_finish(conn, run_id, status="succeeded", notes=notes)
        print(f"Baseline run {run_id} completed. {notes}")

if __name__ == "__main__":
    main()