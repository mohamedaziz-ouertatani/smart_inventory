# Compute replenishment recommendations from forecasts
import uuid
from datetime import date, timedelta
import math
from typing import Dict, Tuple, Optional

import psycopg2
import psycopg2.extras

from jobs.utils.db import get_conn

Z_DEFAULTS = {0.90: 1.2816, 0.95: 1.6449, 0.99: 2.3263}
def z_from_service_level(sl: float) -> float:
    if sl >= 0.99: return Z_DEFAULTS[0.99]
    if sl >= 0.95: return Z_DEFAULTS[0.95]
    if sl >= 0.90: return Z_DEFAULTS[0.90]
    return 1.2816

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

def fetch_latest_week(conn) -> date:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(week_start_date) FROM curated.weekly_demand;")
        row = cur.fetchone()
        if not row or not row[0]:
            raise RuntimeError("No weekly demand data found")
        return row[0]

def fetch_settings(conn) -> Dict[Tuple[str,str], Tuple[int, float]]:
    sql = "SELECT sku_id, location_id, lead_time_weeks, service_level FROM raw.sku_location_settings"
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return {(sku, loc): (lt, float(sl)) for sku, loc, lt, sl in rows}

def fetch_inventory_latest(conn, latest: date) -> Dict[Tuple[str,str], Tuple[int, int]]:
    sql = """
      SELECT sku_id, location_id, end_on_hand, end_on_order
      FROM curated.weekly_inventory
      WHERE week_start_date = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (latest,))
        rows = cur.fetchall()
    return {(sku, loc): (int(oh), int(oo)) for sku, loc, oh, oo in rows}

def fetch_latest_inference_run(conn) -> Optional[uuid.UUID]:
    with conn.cursor() as cur:
        cur.execute("""
          SELECT run_id
          FROM ops.batch_run
          WHERE job_type = 'batch_inference' AND status = 'succeeded'
          ORDER BY started_at DESC
          LIMIT 1
        """)
        row = cur.fetchone()
        return uuid.UUID(row[0]) if row and row[0] else None

def fetch_forecasts_for_lt(conn, run_id: uuid.UUID, sku: str, loc: str, latest: date, lt: int) -> Tuple[float, float]:
    sql = """
      SELECT horizon_week_start, forecast_units::float, residual_std::float
      FROM ops.forecast
      WHERE run_id = %s AND sku_id = %s AND location_id = %s
        AND horizon_week_start > %s
      ORDER BY horizon_week_start ASC
      LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (str(run_id), sku, loc, latest, lt))
        rows = cur.fetchall()
    if not rows:
        return 0.0, 0.0
    mu = sum([float(r[1]) for r in rows])
    residual_std = float(rows[0][2]) if rows[0][2] is not None else 0.0
    return mu, residual_std

def insert_recommendations(conn, run_id: uuid.UUID, rows: list[tuple]):
    sql = """
      INSERT INTO ops.replenishment_recommendation (
        run_id, sku_id, location_id, as_of_week_start,
        lead_time_weeks, service_level, rop_units,
        on_hand, on_order, order_qty,
        mu_lt, sigma_lt, z_value, policy
      ) VALUES %s
      ON CONFLICT (run_id, sku_id, location_id, as_of_week_start) DO UPDATE SET
        lead_time_weeks = EXCLUDED.lead_time_weeks,
        service_level = EXCLUDED.service_level,
        rop_units = EXCLUDED.rop_units,
        on_hand = EXCLUDED.on_hand,
        on_order = EXCLUDED.on_order,
        order_qty = EXCLUDED.order_qty,
        mu_lt = EXCLUDED.mu_lt,
        sigma_lt = EXCLUDED.sigma_lt,
        z_value = EXCLUDED.z_value,
        computed_at = NOW()
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=10000)
    conn.commit()

def main():
    with get_conn() as conn:
        run_id = write_batch_run_start(conn, "compute_policy")
        latest = fetch_latest_week(conn)
        settings = fetch_settings(conn)
        inventory = fetch_inventory_latest(conn, latest)
        inf_run = fetch_latest_inference_run(conn)
        if inf_run is None:
            write_batch_run_finish(conn, run_id, status="failed", notes="No successful batch_inference run found")
            raise RuntimeError("No successful batch_inference run found")

        out_rows: list[tuple] = []
        for (sku, loc), (lt, sl) in settings.items():
            on_hand, on_order = inventory.get((sku, loc), (0, 0))
            mu_lt, residual_std = fetch_forecasts_for_lt(conn, inf_run, sku, loc, latest, lt if lt > 0 else 1)
            z = z_from_service_level(sl)
            sigma_lt = float(residual_std * math.sqrt(lt if lt > 0 else 1))
            rop = float(mu_lt + z * sigma_lt)
            order_qty = int(max(rop - on_hand - on_order, 0))
            out_rows.append((
                str(run_id), sku, loc, latest,
                lt, sl, rop,
                on_hand, on_order, order_qty,
                mu_lt, sigma_lt, z, 'ROP = mu_LT + z*sigma_LT; qty = max(ROP - on_hand - on_order, 0)'
            ))

        insert_recommendations(conn, run_id, out_rows)
        notes = f"Computed {len(out_rows)} recommendations as_of={latest}"
        write_batch_run_finish(conn, run_id, status="succeeded", notes=notes)
        print(f"Policy run {run_id} completed. {notes}")

if __name__ == "__main__":
    main()