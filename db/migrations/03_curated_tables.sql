-- CURATED SCHEMA (cleaned aggregates and ML-ready features)
-- Weekly demand per SKU-location
CREATE TABLE IF NOT EXISTS curated.weekly_demand (
    sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
    location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    units_sold INTEGER NOT NULL CHECK (units_sold >= 0),
    stockout_flag BOOLEAN DEFAULT FALSE,
    data_quality_flags JSONB,
    PRIMARY KEY (sku_id, location_id, week_start_date),
    -- Reference calendar_dim primary key 'date' (ISO Monday dates exist as daily rows)
    FOREIGN KEY (week_start_date) REFERENCES raw.calendar_dim (date) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_weekly_demand_sku_loc_week ON curated.weekly_demand (sku_id, location_id, week_start_date);
-- Weekly inventory summary
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
-- ML feature table (generated artifact; fully recomputed per run)
CREATE TABLE IF NOT EXISTS curated.weekly_features (
    sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
    location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    -- Lag features
    lag_1 NUMERIC(18, 4),
    lag_2 NUMERIC(18, 4),
    lag_3 NUMERIC(18, 4),
    lag_4 NUMERIC(18, 4),
    lag_5 NUMERIC(18, 4),
    lag_6 NUMERIC(18, 4),
    lag_7 NUMERIC(18, 4),
    lag_8 NUMERIC(18, 4),
    lag_52 NUMERIC(18, 4),
    -- Rolling stats
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
    -- Optional promo/price features
    promo_flag BOOLEAN,
    price NUMERIC(12, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (sku_id, location_id, week_start_date),
    FOREIGN KEY (week_start_date) REFERENCES raw.calendar_dim (date) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_weekly_features_sku_loc_week ON curated.weekly_features (sku_id, location_id, week_start_date);