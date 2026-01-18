#!/usr/bin/env bash
# Apply database migrations via psql
# Used in CI and environments where docker-entrypoint-initdb.d isn't available

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/../db/migrations"

# Default connection parameters (can be overridden via environment variables)
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-smart_inventory}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"

echo "=== Database Migration Script ==="
echo "Host: ${PGHOST}:${PGPORT}"
echo "Database: ${PGDATABASE}"
echo "User: ${PGUSER}"
echo ""

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if PGPASSWORD="${PGPASSWORD}" psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -c "SELECT 1" > /dev/null 2>&1; then
    echo "PostgreSQL is ready!"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: PostgreSQL did not become ready in time"
    exit 1
  fi
  echo "Waiting... (attempt $i/30)"
  sleep 2
done

echo ""
echo "Applying migrations from: ${MIGRATIONS_DIR}"

# Apply migrations in order
for migration in "${MIGRATIONS_DIR}"/*.sql; do
  if [ -f "$migration" ]; then
    echo "Applying: $(basename "$migration")"
    if PGPASSWORD="${PGPASSWORD}" psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -f "$migration"; then
      echo "✓ $(basename "$migration") applied successfully"
    else
      echo "✗ Failed to apply $(basename "$migration")"
      exit 1
    fi
  fi
done

echo ""
echo "=== All migrations applied successfully ==="
