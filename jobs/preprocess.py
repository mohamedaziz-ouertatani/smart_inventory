from jobs.utils.db import get_conn

def upsert_weekly_demand(conn):
    sql = """
    INSERT INTO curated.weekly_demand (
        sku_id, location_id, week_start_date, units_sold, stockout_flag, data_quality_flags
    )
    SELECT
        s.sku_id,
        s.location_id,
        c.week_start_date,
        SUM(s.units_sold) AS units_sold,
        COALESCE(BOOL_OR(i.on_hand = 0), FALSE) AS stockout_flag,
        NULL::jsonb AS data_quality_flags
    FROM raw.sales_fact s
    JOIN raw.calendar_dim c ON c.date = s.date
    LEFT JOIN raw.inventory_snapshot i
      ON i.sku_id = s.sku_id AND i.location_id = s.location_id AND i.date = s.date
    GROUP BY s.sku_id, s.location_id, c.week_start_date
    ON CONFLICT (sku_id, location_id, week_start_date) DO UPDATE SET
      units_sold = EXCLUDED.units_sold,
      stockout_flag = EXCLUDED.stockout_flag,
      data_quality_flags = EXCLUDED.data_quality_flags;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()

def upsert_weekly_inventory(conn):
    sql = """
    WITH inv AS (
      SELECT
        i.sku_id,
        i.location_id,
        c.week_start_date,
        AVG(i.on_hand)::numeric(18,4) AS avg_on_hand,
        MAX(i.date) AS last_date
      FROM raw.inventory_snapshot i
      JOIN raw.calendar_dim c ON c.date = i.date
      GROUP BY i.sku_id, i.location_id, c.week_start_date
    ),
    last_vals AS (
      SELECT
        i.sku_id, i.location_id, c.week_start_date,
        i.on_hand AS end_on_hand,
        i.on_order AS end_on_order
      FROM raw.inventory_snapshot i
      JOIN raw.calendar_dim c ON c.date = i.date
      JOIN inv v ON v.sku_id = i.sku_id AND v.location_id = i.location_id AND v.last_date = i.date
    )
    INSERT INTO curated.weekly_inventory (
      sku_id, location_id, week_start_date, avg_on_hand, end_on_hand, end_on_order
    )
    SELECT
      v.sku_id, v.location_id, v.week_start_date, v.avg_on_hand,
      lv.end_on_hand, lv.end_on_order
    FROM inv v
    JOIN last_vals lv ON lv.sku_id = v.sku_id AND lv.location_id = v.location_id AND lv.week_start_date = v.week_start_date
    ON CONFLICT (sku_id, location_id, week_start_date) DO UPDATE SET
      avg_on_hand = EXCLUDED.avg_on_hand,
      end_on_hand = EXCLUDED.end_on_hand,
      end_on_order = EXCLUDED.end_on_order;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()

def recompute_weekly_features(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE curated.weekly_features;")
    conn.commit()

    sql = """
    INSERT INTO curated.weekly_features (
      sku_id, location_id, week_start_date,
      lag_1, lag_2, lag_3, lag_4, lag_5, lag_6, lag_7, lag_8, lag_52,
      roll_mean_4, roll_std_4, roll_mean_8, roll_std_8,
      iso_week, iso_year, holiday_flag, season,
      promo_flag, price
    )
    SELECT
      d.sku_id,
      d.location_id,
      d.week_start_date,
      LAG(d.units_sold, 1) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_1,
      LAG(d.units_sold, 2) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_2,
      LAG(d.units_sold, 3) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_3,
      LAG(d.units_sold, 4) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_4,
      LAG(d.units_sold, 5) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_5,
      LAG(d.units_sold, 6) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_6,
      LAG(d.units_sold, 7) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_7,
      LAG(d.units_sold, 8) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_8,
      LAG(d.units_sold, 52) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date)::numeric(18,4) AS lag_52,
      AVG(d.units_sold) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)::numeric(18,4) AS roll_mean_4,
      STDDEV_SAMP(d.units_sold) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)::numeric(18,4) AS roll_std_4,
      AVG(d.units_sold) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date ROWS BETWEEN 7 PRECEDING AND CURRENT ROW)::numeric(18,4) AS roll_mean_8,
      STDDEV_SAMP(d.units_sold) OVER (PARTITION BY d.sku_id, d.location_id ORDER BY d.week_start_date ROWS BETWEEN 7 PRECEDING AND CURRENT ROW)::numeric(18,4) AS roll_std_8,
      cal.iso_week,
      cal.iso_year,
      cal.holiday_flag,
      cal.season,
      NULL::boolean AS promo_flag,
      NULL::numeric(12,2) AS price
    FROM curated.weekly_demand d
    JOIN raw.calendar_dim cal
      ON cal.date = d.week_start_date
    ;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()

def main():
    with get_conn() as conn:
        print("Upserting curated.weekly_demand ...")
        upsert_weekly_demand(conn)
        print("Upserting curated.weekly_inventory ...")
        upsert_weekly_inventory(conn)
        print("Recomputing curated.weekly_features ...")
        recompute_weekly_features(conn)
        print("Preprocessing completed.")

if __name__ == "__main__":
    main()