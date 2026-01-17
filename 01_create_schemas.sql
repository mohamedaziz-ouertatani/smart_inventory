-- Create logical schemas and shared extensions
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS ops;

-- UUID generation for run tracking and alerts
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enums scoped to schemas
-- Purchase order status in raw
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'po_status') THEN
    CREATE TYPE raw.po_status AS ENUM ('open', 'closed', 'cancelled');
  END IF;
END
$$;

-- Alert enums in ops
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_type') THEN
    CREATE TYPE ops.alert_type AS ENUM ('stockout_risk', 'overstock_risk', 'drift', 'data_quality');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_severity') THEN
    CREATE TYPE ops.alert_severity AS ENUM ('low', 'medium', 'high');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_status') THEN
    CREATE TYPE ops.alert_status AS ENUM ('open', 'ack', 'closed');
  END IF;
END
$$;