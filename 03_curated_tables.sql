-- =====================
-- CURATED SCHEMA (cleaned aggregates and ML-ready features)
-- =====================
-- Weekly demand per SKU-location (aggregated from raw.sales_fact)
CREATE TABLE IF NOT EXISTS curated.weekly_demand (
  sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  week_start_date DATE NOT NULL,
  units_sold INTEGER NOT NULL CHECK (units_sold >= 0),
  stockout_flag BOOLEAN DEFAULT FALSE,
  -- true if inventory_snapshot.on_hand == 0 during week at least one day
  data_quality_flags JSONB,
  -- e.g., {"missing_days":2,"imputed":true}
  PRIMARY KEY (sku_id, location_id, week_start_date),
  -- NOTE: Reference the calendar_dim primary key 'date', not 'week_start_date'
  FOREIGN KEY (week_start_date) REFERENCES raw.calendar_dim (date) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_weekly_demand_sku_loc_week ON curated.weekly_demand (sku_id, location_id, week_start_date);
-- Weekly inventory summary (optional but useful for policy computation)
CREATE TABLE IF NOT EXISTS curated.weekly_inventory (
  sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  week_start_date DATE NOT NULL,
  avg_on_hand NUMERIC(18, 4) NOT NULL CHECK (avg_on_hand >= 0),
  end_on_hand INTEGER NOT NULL CHECK (end_on_hand >= 0),
  end_on_order INTEGER NOT NULL CHECK (end_on_order >= 0),
  PRIMARY KEY (sku_id, location_id, week_start_date),
  FOREIGN KEY (week_start_date) REFERENCES raw.calendar_dim (date) ON UPDATE CASCADE ON DELETE RESTRICT
);
-- ML feature table (materialized; computed by preprocessing job)
-- Simple-first features aligned with baseline: lags, rolling stats, calendar features.
CREATE TABLE IF NOT EXISTS curated.weekly_features (
  sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  week_start_date DATE NOT NULL,
  -- features to predict t+1..t+8 horizons
  -- Lag features (units_sold lagged by weeks)
  lag_1 NUMERIC(18, 4),
  lag_2 NUMERIC(18, 4),
  lag_3 NUMERIC(18, 4),
  lag_4 NUMERIC(18, 4),
  lag_5 NUMERIC(18, 4),
  lag_6 NUMERIC(18, 4),
  lag_7 NUMERIC(18, 4),
  lag_8 NUMERIC(18, 4),
  lag_52 NUMERIC(18, 4),
  -- Rolling stats (window size examples)
  roll_mean_4 NUMERIC(18, 4),
  roll_std_4 NUMERIC(18, 4),
  roll_mean_8 NUMERIC(18, 4),
  roll_std_8 NUMERIC(18, 4),
  -- Calendar features
  iso_week INTEGER CHECK (
    iso_week BETWEEN 1 AND 53
  ),
  iso_year INTEGER,
  holiday_flag BOOLEAN,
  season TEXT,
  -- Optional promo/price features (null if unavailable)
  promo_flag BOOLEAN,
  price NUMERIC(12, 2),
  -- Meta
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (sku_id, location_id, week_start_date),
  FOREIGN KEY (week_start_date) REFERENCES raw.calendar_dim (date) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_weekly_features_sku_loc_week ON curated.weekly_features (sku_id, location_id, week_start_date);