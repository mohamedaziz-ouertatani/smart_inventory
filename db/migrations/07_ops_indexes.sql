-- Migration: Enhance performance indexes for common query patterns on ops tables
-- Upgrades existing indexes to include DESC ordering for better performance on latest-data queries.
-- Recreates indexes idx_forecast_sku_loc_week and idx_metrics_sku_loc_week with DESC on date columns.
-- Safe to run multiple times due to conditional DROP IF EXISTS.

BEGIN;

-- Drop and recreate idx_forecast_sku_loc_week with DESC ordering on horizon_week_start
-- This optimizes queries that fetch the latest forecasts for a SKU-location combination
DROP INDEX IF EXISTS ops.idx_forecast_sku_loc_week;
CREATE INDEX idx_forecast_sku_loc_week
ON ops.forecast (sku_id, location_id, horizon_week_start DESC);

-- Drop and recreate idx_metrics_sku_loc_week with DESC ordering on week_start_date
-- This optimizes queries that fetch the latest accuracy metrics for a SKU-location combination
DROP INDEX IF EXISTS ops.idx_metrics_sku_loc_week;
CREATE INDEX idx_metrics_sku_loc_week
ON ops.metrics_accuracy (sku_id, location_id, week_start_date DESC);

COMMIT;
