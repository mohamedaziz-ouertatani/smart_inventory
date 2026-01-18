-- MLflow database schema
-- Create separate database for MLflow tracking server
-- Note: This file creates the mlflow database if running in an environment where
-- the script has sufficient privileges. In Docker, the MLflow server will create
-- its own tables automatically when using the backend-store-uri.

-- For PostgreSQL, we create a separate database for MLflow
-- This ensures isolation from the smart_inventory operational data
CREATE DATABASE mlflow;
