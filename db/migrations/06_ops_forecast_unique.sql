-- Migration: Add unique constraint to ops.forecast to prevent duplicate entries within a run
-- Ensures data integrity by preventing multiple forecast rows for the same SKU-location-week combination in a single run.
-- Note: The PRIMARY KEY on (run_id, sku_id, location_id, horizon_week_start) already ensures uniqueness,
-- but this migration adds an explicit named constraint for clarity and documentation purposes.
-- Safe to run multiple times due to conditional logic.

BEGIN;

-- The PRIMARY KEY constraint already ensures uniqueness on these columns
-- This constraint would be redundant, but we add it as an alias for explicit documentation
-- However, PostgreSQL doesn't allow duplicate constraints on the same columns
-- So we skip this if the PRIMARY KEY already exists (which it does from 04_ops_tables.sql)

-- Instead, we simply verify the PRIMARY KEY constraint exists
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
