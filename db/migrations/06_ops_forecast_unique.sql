-- Migration: Document uniqueness constraint on ops.forecast
-- This migration serves as documentation for the uniqueness constraint on ops.forecast.
-- The PRIMARY KEY on (run_id, sku_id, location_id, horizon_week_start) already ensures uniqueness.
-- No actual schema changes are made by this migration - it only verifies the constraint exists.
-- Safe to run multiple times.

BEGIN;

-- Verify that the PRIMARY KEY constraint exists
-- The PRIMARY KEY constraint already ensures uniqueness on these columns
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = 'ops'
          AND t.relname = 'forecast'
          AND c.contype = 'p'
          AND c.conkey = ARRAY[
              (SELECT attnum FROM pg_attribute WHERE attrelid = 'ops.forecast'::regclass AND attname = 'run_id'),
              (SELECT attnum FROM pg_attribute WHERE attrelid = 'ops.forecast'::regclass AND attname = 'sku_id'),
              (SELECT attnum FROM pg_attribute WHERE attrelid = 'ops.forecast'::regclass AND attname = 'location_id'),
              (SELECT attnum FROM pg_attribute WHERE attrelid = 'ops.forecast'::regclass AND attname = 'horizon_week_start')
          ]
    ) THEN
        RAISE NOTICE 'PRIMARY KEY constraint on ops.forecast already ensures uniqueness on (run_id, sku_id, location_id, horizon_week_start)';
    ELSE
        RAISE WARNING 'PRIMARY KEY constraint missing on ops.forecast - this should not happen';
    END IF;
END $$;

COMMIT;
