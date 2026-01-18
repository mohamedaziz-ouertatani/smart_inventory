-- Migration: Add 'train_ml' to allowed job_type values in ops.batch_run
-- Ensures ops.batch_run accepts the new ML training job type.
-- Safe to run multiple times due to IF EXISTS on drop.
BEGIN;
-- Drop existing CHECK constraint if present
ALTER TABLE ops.batch_run DROP CONSTRAINT IF EXISTS batch_run_job_type_check;
-- Recreate CHECK constraint including the new 'train_ml' value
ALTER TABLE ops.batch_run
ADD CONSTRAINT batch_run_job_type_check CHECK (
        job_type IN (
            'ingest',
            'preprocess',
            'batch_inference',
            'compute_policy',
            'train_ml'
        )
    );
COMMIT;