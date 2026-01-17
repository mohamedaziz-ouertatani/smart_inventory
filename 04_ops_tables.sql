-- =====================
-- OPS SCHEMA (model outputs, recommendations, metrics, alerts)
-- =====================
-- Batch run tracking to support idempotency and grouping of outputs
CREATE TABLE IF NOT EXISTS ops.batch_run (
  run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type TEXT NOT NULL CHECK (
    job_type IN (
      'train',
      'batch_inference',
      'compute_policy',
      'monitor'
    )
  ),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_batch_run_job_type_started ON ops.batch_run (job_type, started_at);
-- Forecasts per SKU-location-horizon
CREATE TABLE IF NOT EXISTS ops.forecast (
  run_id UUID NOT NULL REFERENCES ops.batch_run (run_id) ON UPDATE CASCADE ON DELETE CASCADE,
  sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  horizon_week_start DATE NOT NULL,
  -- week being forecasted
  forecast_units NUMERIC(18, 4) NOT NULL CHECK (forecast_units >= 0),
  baseline_units NUMERIC(18, 4),
  -- seasonal naive baseline
  residual_std NUMERIC(18, 4),
  -- std of recent residuals for uncertainty
  model_name TEXT NOT NULL,
  -- e.g., 'demand_forecast_v1'
  model_stage TEXT NOT NULL CHECK (model_stage IN ('Production', 'Staging', 'None')),
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (run_id, sku_id, location_id, horizon_week_start)
);
CREATE INDEX IF NOT EXISTS idx_forecast_sku_loc_week ON ops.forecast (sku_id, location_id, horizon_week_start);
CREATE INDEX IF NOT EXISTS idx_forecast_model ON ops.forecast (model_name, model_stage, generated_at);
-- Replenishment recommendations
CREATE TABLE IF NOT EXISTS ops.replenishment_recommendation (
  run_id UUID NOT NULL REFERENCES ops.batch_run (run_id) ON UPDATE CASCADE ON DELETE CASCADE,
  sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  as_of_week_start DATE NOT NULL,
  -- week when recommendation is made
  lead_time_weeks INTEGER NOT NULL CHECK (
    lead_time_weeks >= 0
    AND lead_time_weeks <= 52
  ),
  service_level NUMERIC(4, 3) NOT NULL CHECK (
    service_level >= 0
    AND service_level <= 1
  ),
  rop_units NUMERIC(18, 4) NOT NULL CHECK (rop_units >= 0),
  on_hand INTEGER NOT NULL CHECK (on_hand >= 0),
  on_order INTEGER NOT NULL CHECK (on_order >= 0),
  order_qty INTEGER NOT NULL CHECK (order_qty >= 0),
  mu_lt NUMERIC(18, 4) NOT NULL,
  -- expected demand over lead time
  sigma_lt NUMERIC(18, 4) NOT NULL,
  -- demand std over lead time
  z_value NUMERIC(8, 4) NOT NULL,
  -- service level to z
  policy TEXT NOT NULL DEFAULT 'ROP = mu_LT + z*sigma_LT; qty = max(ROP - on_hand - on_order, 0)',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (run_id, sku_id, location_id, as_of_week_start)
);
CREATE INDEX IF NOT EXISTS idx_reco_sku_loc_week ON ops.replenishment_recommendation (sku_id, location_id, as_of_week_start);
-- Accuracy metrics (rolling evaluation)
CREATE TABLE IF NOT EXISTS ops.metrics_accuracy (
  run_id UUID NOT NULL REFERENCES ops.batch_run (run_id) ON UPDATE CASCADE ON DELETE CASCADE,
  sku_id TEXT NOT NULL REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id TEXT NOT NULL REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  week_start_date DATE NOT NULL,
  -- evaluation week
  actual_units NUMERIC(18, 4) NOT NULL CHECK (actual_units >= 0),
  forecast_units NUMERIC(18, 4) NOT NULL CHECK (forecast_units >= 0),
  wape NUMERIC(8, 4) NOT NULL CHECK (wape >= 0),
  smape NUMERIC(8, 4) NOT NULL CHECK (smape >= 0),
  bias NUMERIC(8, 4) NOT NULL,
  model_name TEXT NOT NULL,
  model_stage TEXT NOT NULL CHECK (model_stage IN ('Production', 'Staging', 'None')),
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (run_id, sku_id, location_id, week_start_date)
);
CREATE INDEX IF NOT EXISTS idx_metrics_sku_loc_week ON ops.metrics_accuracy (sku_id, location_id, week_start_date);
-- Alerts (stockout risk, drift, data quality)
CREATE TABLE IF NOT EXISTS ops.alerts (
  alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type ops.alert_type NOT NULL,
  sku_id TEXT REFERENCES raw.sku_dim (sku_id) ON UPDATE CASCADE ON DELETE CASCADE,
  location_id TEXT REFERENCES raw.location_dim (location_id) ON UPDATE CASCADE ON DELETE CASCADE,
  week_start_date DATE,
  -- if time-bound
  severity ops.alert_severity NOT NULL DEFAULT 'medium',
  message TEXT NOT NULL,
  status ops.alert_status NOT NULL DEFAULT 'open',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_alerts_type_status ON ops.alerts (type, status);
CREATE INDEX IF NOT EXISTS idx_alerts_sku_loc_week ON ops.alerts (sku_id, location_id, week_start_date);