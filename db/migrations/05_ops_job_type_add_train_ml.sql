-- Migration: Add 'train_ml' to allowed job_type values in ops.batch_run
-- Ensures ops.batch_run accepts the new ML training job type.
-- Safe to run multiple times due to IF EXISTS on drop.
BEGIN;
-- Drop existing CHECK constraint if present
ALTER TABLE ops.batch_run DROP CONSTRAINT IF EXISTS batch_run_job_type_check;
-- Recreate CHECK constraint including the new 'train_ml' value
-- Preserves all existing job types and adds train_ml
ALTER TABLE ops.batch_run
ADD CONSTRAINT batch_run_job_type_check CHECK (
        job_type IN (
            'train',
            'batch_inference',
            'compute_policy',
            'monitor',
            'train_ml'
        )
    );
COMMIT;