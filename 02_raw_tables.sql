-- =====================
-- RAW SCHEMA (source-of-truth ingested data)
-- =====================

-- SKU dimension: master data for products
CREATE TABLE IF NOT EXISTS raw.sku_dim (
  sku_id            TEXT PRIMARY KEY,
  name              TEXT NOT NULL,
  category          TEXT,
  unit_cost         NUMERIC(12,2),
  unit_price        NUMERIC(12,2),
  abc_class         CHAR(1) CHECK (abc_class IN ('A','B','C')) DEFAULT 'B',
  shelf_life_days   INTEGER,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ
);

-- Location dimension: warehouses/stores
CREATE TABLE IF NOT EXISTS raw.location_dim (
  location_id       TEXT PRIMARY KEY,
  name              TEXT NOT NULL,
  type              TEXT CHECK (type IN ('warehouse','store','dc')) DEFAULT 'warehouse',
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ
);

-- Calendar dimension: daily granularity; weekly keys derived
CREATE TABLE IF NOT EXISTS raw.calendar_dim (
  date              DATE PRIMARY KEY,
  iso_year          INTEGER NOT NULL,
  iso_week          INTEGER NOT NULL CHECK (iso_week BETWEEN 1 AND 53),
  week_start_date   DATE NOT NULL, -- ISO week start (Monday)
  month             INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
  year              INTEGER NOT NULL,
  holiday_flag      BOOLEAN DEFAULT FALSE,
  season            TEXT
);
CREATE INDEX IF NOT EXISTS idx_calendar_week_start ON raw.calendar_dim (week_start_date);

-- Fixed settings per SKU-location (lead time, service level targets)
CREATE TABLE IF NOT EXISTS raw.sku_location_settings (
  sku_id            TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id       TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  lead_time_weeks   INTEGER NOT NULL CHECK (lead_time_weeks >= 0 AND lead_time_weeks <= 52),
  service_level     NUMERIC(4,3) NOT NULL CHECK (service_level >= 0 AND service_level <= 1),
  PRIMARY KEY (sku_id, location_id)
);

-- Sales facts: daily fulfilled units (may be zero due to stockouts)
CREATE TABLE IF NOT EXISTS raw.sales_fact (
  sku_id            TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id       TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  date              DATE NOT NULL REFERENCES raw.calendar_dim (date) ON UPDATE CASCADE ON DELETE RESTRICT,
  units_sold        INTEGER NOT NULL CHECK (units_sold >= 0),
  source            TEXT, -- optional provenance
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (sku_id, location_id, date)
);
CREATE INDEX IF NOT EXISTS idx_sales_sku_loc_date ON raw.sales_fact (sku_id, location_id, date);
CREATE INDEX IF NOT EXISTS idx_sales_date ON raw.sales_fact (date);

-- Inventory snapshots: daily on-hand counts (one per day per SKU-location for MVP)
CREATE TABLE IF NOT EXISTS raw.inventory_snapshot (
  sku_id            TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id       TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  date              DATE NOT NULL REFERENCES raw.calendar_dim (date) ON UPDATE CASCADE ON DELETE RESTRICT,
  on_hand           INTEGER NOT NULL CHECK (on_hand >= 0),
  on_order          INTEGER NOT NULL DEFAULT 0 CHECK (on_order >= 0),
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (sku_id, location_id, date)
);
CREATE INDEX IF NOT EXISTS idx_inv_sku_loc_date ON raw.inventory_snapshot (sku_id, location_id, date);

-- Purchase orders: optional for MVP, supports open/inbound shipments
CREATE TABLE IF NOT EXISTS raw.purchase_orders (
  po_id             BIGSERIAL PRIMARY KEY,
  sku_id            TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id       TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  order_date        DATE NOT NULL,
  qty               INTEGER NOT NULL CHECK (qty > 0),
  expected_delivery_date DATE,
  status            raw.po_status NOT NULL DEFAULT 'open',
  vendor            TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_po_sku_loc_status ON raw.purchase_orders (sku_id, location_id, status);
CREATE INDEX IF NOT EXISTS idx_po_expected_delivery ON raw.purchase_orders (expected_delivery_date);