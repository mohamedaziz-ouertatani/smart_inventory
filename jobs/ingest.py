from datetime import date, timedelta
import argparse
import random
import math
from tqdm import tqdm
from jobs.utils.db import get_conn, execute_values_insert

def iso_week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def seed_sku_dim(conn, n_skus: int):
    rows = []
    for i in range(n_skus):
        sku_id = f"SKU{i+1:04d}"
        name = f"Product {i+1}"
        category = f"CAT{(i % 10) + 1}"
        unit_cost = round(random.uniform(2.0, 50.0), 2)
        unit_price = round(unit_cost * random.uniform(1.2, 2.5), 2)
        abc_class = random.choices(["A", "B", "C"], weights=[0.2, 0.5, 0.3], k=1)[0]
        shelf_life_days = None
        rows.append((sku_id, name, category, unit_cost, unit_price, abc_class, shelf_life_days))
    sql = """
        INSERT INTO raw.sku_dim (sku_id, name, category, unit_cost, unit_price, abc_class, shelf_life_days)
        VALUES %s
        ON CONFLICT (sku_id) DO UPDATE SET
          name = EXCLUDED.name,
          category = EXCLUDED.category,
          unit_cost = EXCLUDED.unit_cost,
          unit_price = EXCLUDED.unit_price,
          abc_class = EXCLUDED.abc_class,
          shelf_life_days = EXCLUDED.shelf_life_days,
          updated_at = NOW()
    """
    execute_values_insert(conn, sql, rows)

def seed_location_dim(conn, n_locations: int):
    rows = []
    for i in range(n_locations):
        loc_id = f"LOC{i+1}"
        name = f"Location {i+1}"
        typ = random.choice(["warehouse", "store", "dc"])
        rows.append((loc_id, name, typ))
    sql = """
        INSERT INTO raw.location_dim (location_id, name, type)
        VALUES %s
        ON CONFLICT (location_id) DO UPDATE SET
          name = EXCLUDED.name,
          type = EXCLUDED.type,
          updated_at = NOW()
    """
    execute_values_insert(conn, sql, rows)

def seed_calendar(conn, start_date: date, end_date: date):
    rows = []
    d = start_date
    while d <= end_date:
        iso_y, iso_w, _ = d.isocalendar()
        ws = iso_week_start(d)
        month = d.month
        year = d.year
        holiday_flag = False
        season = {12:"winter",1:"winter",2:"winter",3:"spring",4:"spring",5:"spring",6:"summer",7:"summer",8:"summer",9:"fall",10:"fall",11:"fall"}[d.month]
        rows.append((d, iso_y, iso_w, ws, month, year, holiday_flag, season))
        d += timedelta(days=1)
    sql = """
        INSERT INTO raw.calendar_dim (date, iso_year, iso_week, week_start_date, month, year, holiday_flag, season)
        VALUES %s
        ON CONFLICT (date) DO UPDATE SET
          iso_year = EXCLUDED.iso_year,
          iso_week = EXCLUDED.iso_week,
          week_start_date = EXCLUDED.week_start_date,
          month = EXCLUDED.month,
          year = EXCLUDED.year,
          holiday_flag = EXCLUDED.holiday_flag,
          season = EXCLUDED.season
    """
    execute_values_insert(conn, sql, rows)

def seed_settings(conn, n_skus: int, n_locations: int):
    rows = []
    for i in range(n_skus):
        sku_id = f"SKU{i+1:04d}"
        abc_class = random.choices(["A", "B", "C"], weights=[0.2, 0.5, 0.3], k=1)[0]
        for j in range(n_locations):
            loc_id = f"LOC{j+1}"
            lead_time_weeks = random.choice([1,2,3,4])
            service_level = 0.95 if abc_class == "A" else 0.90
            rows.append((sku_id, loc_id, lead_time_weeks, service_level))
    sql = """
        INSERT INTO raw.sku_location_settings (sku_id, location_id, lead_time_weeks, service_level)
        VALUES %s
        ON CONFLICT (sku_id, location_id) DO UPDATE SET
          lead_time_weeks = EXCLUDED.lead_time_weeks,
          service_level = EXCLUDED.service_level
    """
    execute_values_insert(conn, sql, rows)

def seed_sales_and_inventory(conn, n_skus: int, n_locations: int, start_date: date, end_date: date):
    sales_rows = []
    inv_rows = []
    rng = random.Random(42)
    for i in tqdm(range(n_skus), desc="Generating sales/inventory"):
        sku_id = f"SKU{i+1:04d}"
        base = rng.uniform(5, 50)
        trend = rng.uniform(-0.05, 0.05)
        for j in range(n_locations):
            loc_id = f"LOC{j+1}"
            d = start_date
            week_index = 0
            on_hand = rng.randint(100, 500)
            on_order = 0
            while d <= end_date:
                iso_y, iso_w, _ = d.isocalendar()
                season_factor = 1.0 + 0.3 * math.sin((iso_w / 52.0) * 2 * math.pi)
                weekly_mean = max(0.0, base * (1 + trend * week_index) * season_factor)
                weekday_factor = 1.0 + 0.1 * (0 if d.weekday() < 5 else -1)
                daily_mean = weekly_mean / 7.0 * weekday_factor
                units = max(0, int(rng.gauss(daily_mean, daily_mean * 0.3)))
                if on_hand <= 0:
                    units = 0
                on_hand -= units
                if rng.random() < 0.02:
                    on_order += rng.randint(50, 200)
                if d.weekday() == 0 and on_order > 0:
                    on_hand += on_order
                    on_order = 0
                sales_rows.append((sku_id, loc_id, d, units, "sim"))
                inv_rows.append((sku_id, loc_id, d, max(0, on_hand), on_order))
                d += timedelta(days=1)
                week_index += (1 if d.weekday() == 0 else 0)

    sales_sql = """
        INSERT INTO raw.sales_fact (sku_id, location_id, date, units_sold, source)
        VALUES %s
        ON CONFLICT (sku_id, location_id, date) DO UPDATE SET
          units_sold = EXCLUDED.units_sold,
          source = EXCLUDED.source
    """
    execute_values_insert(conn, sales_sql, sales_rows)

    inv_sql = """
        INSERT INTO raw.inventory_snapshot (sku_id, location_id, date, on_hand, on_order)
        VALUES %s
        ON CONFLICT (sku_id, location_id, date) DO UPDATE SET
          on_hand = EXCLUDED.on_hand,
          on_order = EXCLUDED.on_order
    """
    execute_values_insert(conn, inv_sql, inv_rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skus", type=int, default=1000)
    parser.add_argument("--locations", type=int, default=3)
    parser.add_argument("--weeks", type=int, default=156)
    parser.add_argument("--start", type=str, default=None)
    args = parser.parse_args()

    if args.start:
        start_date = date.fromisoformat(args.start)
    else:
        today = date.today()
        start_date = iso_week_start(today - timedelta(weeks=args.weeks))
    end_date = date.today()

    with get_conn() as conn:
        print("Seeding sku_dim...")
        seed_sku_dim(conn, args.skus)
        print("Seeding location_dim...")
        seed_location_dim(conn, args.locations)
        print("Seeding calendar_dim...")
        seed_calendar(conn, start_date, end_date)
        print("Seeding settings...")
        seed_settings(conn, args.skus, args.locations)
        print("Seeding sales & inventory (this may take a few minutes)...")
        seed_sales_and_inventory(conn, args.skus, args.locations, start_date, end_date)
        print("Done.")

if __name__ == "__main__":
    main()