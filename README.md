# smart_inventory

Smart Inventory Management System with demand forecasting and inventory optimization.

## Features

- **API**: Fastify-based REST API with JWT authentication
- **Database**: PostgreSQL with automatic migration initialization
- **Jobs**: Python-based data ingestion, preprocessing, forecasting (Seasonal Naive, ETS, ARIMA/SARIMA), and policy computation
- **MLflow**: Experiment tracking and model registry for ML forecasting models
- **CI/CD**: Automated testing and validation on every push and pull request

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20.x (for local development)
- Python 3.11+ (for local job development)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/mohamedaziz-ouertatani/smart_inventory.git
   cd smart_inventory
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

3. **Start the stack**
   ```bash
   # Start PostgreSQL (migrations auto-apply on fresh volumes)
   docker compose up -d postgres
   
   # Start API
   docker compose up -d api
   
   # Start MLflow tracking server
   docker compose up -d mlflow
   
   # Check health
   curl http://localhost:3000/health
   curl http://localhost:5000/health
   ```

4. **Run data jobs**
   ```bash
   # Install Python dependencies
   pip install -r jobs/requirements.txt
   
   # Run ingestion (adjust parameters for your needs)
   python -m jobs.ingest --skus 100 --locations 3 --weeks 52
   
   # Run preprocessing
   python -m jobs.preprocess
   
   # Train baseline model (seasonal naive)
   python -m jobs.train_baseline --horizon 4
   
   # Train ML models (ETS, ARIMA with MLflow tracking)
   python -m jobs.train_ml --horizon 4
   
   # Compute policies
   python -m jobs.compute_policy
   ```

5. **Access MLflow UI**
   ```bash
   # Open in browser
   open http://localhost:5000
   
   # View experiment runs, metrics, and artifacts
   ```

6. **Test API endpoints**
   ```bash
   # Get JWT token
   TOKEN=$(curl -s -X POST http://localhost:3000/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username":"viewer","password":"viewer123"}' | jq -r '.token')
   
   # Test authenticated endpoints
   curl -H "Authorization: Bearer $TOKEN" http://localhost:3000/auth/me
   curl -H "Authorization: Bearer $TOKEN" "http://localhost:3000/forecasts?latest_only=true&limit=10"
   curl -H "Authorization: Bearer $TOKEN" "http://localhost:3000/recommendations?latest_only=true&limit=10"
   ```

### Database Migrations

Migrations are automatically applied when using Docker Compose with fresh volumes.

For manual migration application (useful in CI or custom environments):
```bash
./scripts/db_init.sh
```

The script uses environment variables for connection parameters (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD).

## CI/CD

The repository includes a GitHub Actions workflow that runs on every push and pull request:

- ✅ Builds and type-checks the API
- ✅ Applies database migrations
- ✅ Runs the complete data pipeline with a small test dataset
- ✅ Tests authentication and protected API endpoints
- ✅ Validates data integrity

The CI pipeline typically completes in 3-5 minutes.

### CI Environment

CI uses ephemeral credentials defined in `.env.ci`. These are safe for testing and should **never** be used in production.

## Project Structure

```
.
├── .github/workflows/    # CI/CD workflows
├── db/migrations/        # SQL migration files (applied in order)
├── jobs/                 # Python data processing jobs
│   ├── ingest.py        # Data ingestion
│   ├── preprocess.py    # Data preprocessing
│   ├── train_baseline.py # Baseline model training (seasonal naive)
│   ├── train_ml.py      # ML model training (ETS, ARIMA/SARIMA with MLflow)
│   └── compute_policy.py # Policy computation
├── scripts/             # Utility scripts
│   └── db_init.sh       # Manual migration script
├── src/                 # TypeScript API source
│   ├── routes/          # API route handlers
│   ├── plugins/         # Fastify plugins
│   └── server.ts        # Main server entry point
├── docker-compose.yml   # Docker orchestration
├── Dockerfile.mlflow    # MLflow tracking server image
└── .env.example         # Environment variables template
```

## MLflow Tracking

The system includes MLflow for experiment tracking and model registry:

- **Tracking Server**: Runs on port 5000 with PostgreSQL backend
- **Artifacts**: Stored in a Docker volume (`mlartifacts`)
- **Per-SKU-Location Models**: Each SKU-location combination gets its own model evaluation
- **Model Selection**: Best model chosen by lowest WAPE (tie-break by sMAPE)
- **Metrics Tracked**: WAPE, sMAPE, bias for each model (seasonal naive, ETS, ARIMA/SARIMA)
- **Artifacts**: Backtest plots showing actual vs forecast

### Using MLflow

```bash
# Start MLflow service
docker compose up -d mlflow

# Train ML models with tracking
python -m jobs.train_ml --horizon 4

# View results in browser
open http://localhost:5000

# In MLflow UI:
# - View experiment "smart-inventory"
# - Compare model metrics across runs
# - Download artifacts (plots, residuals)
# - Track model selections per SKU-location
```

## Development

### API Development

```bash
npm install
npm run dev   # Watch mode with hot reload
npm run build # Build TypeScript
npm start     # Run production build
```

### Adding New Migrations

1. Create a new SQL file in `db/migrations/` with sequential naming (e.g., `08_new_feature.sql`)
2. Migrations are automatically applied on fresh volumes or via `scripts/db_init.sh`

## Runbook: After Merge / Fresh Deployment

This section provides step-by-step commands to deploy and run the complete system from scratch.

### 1. Ensure MLflow Database Exists

The MLflow tracking server requires a dedicated database. Create it if it doesn't exist:

```bash
# If using Docker Compose (with postgres service running):
docker exec -e PGPASSWORD=0000 smartinv-postgres psql -U postgres -c "CREATE DATABASE mlflow;"

# If running locally:
PGPASSWORD=0000 psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE mlflow;"
```

**Note**: The command will fail if the database already exists, which is safe to ignore.

### 2. Rebuild and Start Services

```bash
# Build and start all services (Postgres, API, MLflow)
docker compose up -d --build

# Verify all services are healthy
docker compose ps
```

Expected output should show:
- `smartinv-postgres` - healthy
- `smartinv-api` - healthy  
- `smartinv-mlflow` - healthy

### 3. Ingest and Preprocess Data

```bash
# Ingest sample data (adjust parameters for production)
# For production: --skus 1000 --locations 3 --weeks 156
# For testing: --skus 20 --locations 2 --weeks 26
docker compose -f docker-compose.yml -f docker-compose.jobs.override.yml run --rm jobs \
  python -m jobs.ingest --skus 1000 --locations 3 --weeks 156

# Preprocess raw data into curated tables
docker compose -f docker-compose.yml -f docker-compose.jobs.override.yml run --rm jobs \
  python -m jobs.preprocess
```

### 4. Train Models and Compute Policies

```bash
# Train ML models with MLflow tracking (ETS, ARIMA, Seasonal Naive)
# This will:
# - Perform rolling backtests over 26 weeks
# - Select best model per SKU-location by WAPE
# - Write forecasts to ops.forecast
# - Write accuracy metrics to ops.metrics_accuracy
# - Log runs, params, metrics, and plots to MLflow
docker compose -f docker-compose.yml -f docker-compose.jobs.override.yml run --rm jobs \
  python -m jobs.train_ml --horizon 4

# Compute replenishment policies based on forecasts
docker compose -f docker-compose.yml -f docker-compose.jobs.override.yml run --rm jobs \
  python -m jobs.compute_policy
```

### 5. Verify Results

#### Check Database

```bash
# Connect to database
docker exec -e PGPASSWORD=0000 -it smartinv-postgres psql -U postgres -d smart_inventory

# Run verification queries:

# 1. Check forecast distribution by model
SELECT model_name, model_stage, COUNT(*) as forecast_count
FROM ops.forecast
GROUP BY model_name, model_stage
ORDER BY forecast_count DESC;

# 2. Check average accuracy metrics
SELECT
    model_name,
    COUNT(*) as metrics_count,
    AVG(wape) as avg_wape,
    AVG(smape) as avg_smape,
    AVG(bias) as avg_bias
FROM ops.metrics_accuracy
GROUP BY model_name;

# 3. Check batch run history
SELECT job_type, status, started_at, finished_at, notes
FROM ops.batch_run
ORDER BY started_at DESC
LIMIT 10;
```

#### Check MLflow UI

```bash
# Open MLflow in browser
open http://localhost:5000

# Or use curl to verify API
curl http://localhost:5000/health
```

In the MLflow UI:
1. Select experiment "smart-inventory"
2. View runs for each SKU-location
3. Compare metrics (WAPE, sMAPE, bias) across models
4. Download backtest plots from artifacts
5. Inspect model parameters and selections

#### Test API Endpoints

```bash
# Get JWT token
TOKEN=$(curl -s -X POST http://localhost:3000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"viewer","password":"viewer123"}' | jq -r '.token')

# Fetch latest forecasts
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/forecasts?latest_only=true&limit=10" | jq '.'

# Fetch recommendations
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/recommendations?latest_only=true&limit=10" | jq '.'

# Check specific SKU-location forecast
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/forecasts?sku_id=SKU001&location_id=WH001" | jq '.'
```

### Troubleshooting

**MLflow database doesn't exist:**
```bash
docker exec -e PGPASSWORD=0000 smartinv-postgres psql -U postgres -c "CREATE DATABASE mlflow;"
docker compose restart mlflow
```

**MLflow shows "Invalid Host header":**
- Ensure `MLFLOW_ALLOW_MULTIPLE_HOSTNAMES=true` in docker-compose.yml
- Restart MLflow: `docker compose restart mlflow`

**Migrations not applied:**
```bash
# Manually apply migrations
docker exec -e PGPASSWORD=0000 smartinv-postgres \
  psql -U postgres -d smart_inventory -f /docker-entrypoint-initdb.d/01_create_schemas.sql
# Repeat for 02-07...
```

**Jobs can't connect to MLflow:**
- Verify `MLFLOW_TRACKING_URI=http://mlflow:5000` in jobs environment
- Check `docker compose logs mlflow` for errors
- Ensure mlflow service is healthy: `docker compose ps mlflow`

---

## Automated Scheduling and Dashboards

**Enable Scheduler:**
- `docker compose up -d --build scheduler`
  - *Starts the scheduler container. It will run the full pipeline (ingestion, preprocessing, forecasting, policy computation) every Sunday at 04:00 UTC.*

**Disable Scheduler:**
- `docker compose stop scheduler` (temporarily stops)
- `docker compose rm scheduler` (removes the container)

**View Scheduler Logs:**
- `docker compose logs -f scheduler`
  - *Shows real-time details about when each job runs and its output.*

**Enable Metabase (Dashboards):**
- `docker compose up -d metabase`
  - *Brings up Metabase for data visualizations and custom dashboards*
- Open your browser to [http://localhost:3001](http://localhost:3001)
- Connect to the same Postgres DB as the rest of the stack (host: postgres, db: smart_inventory, credentials from `.env`)

**Sample SQL for Dashboards (paste in Metabase SQL editor):**

- **Forecasts (last 12 weeks):**
  ```sql
  SELECT sku_id, location_id, horizon_week_start, forecast_units, model_name
  FROM ops.forecast
  WHERE horizon_week_start > NOW() - INTERVAL '12 weeks'
  ORDER BY sku_id, location_id, horizon_week_start;
  ```
- **Accuracy by model:**
  ```sql
  SELECT model_name, AVG(wape) as avg_wape, AVG(smape) as avg_smape
  FROM ops.metrics_accuracy
  GROUP BY model_name
  ORDER BY avg_wape;
  ```
- **Replenishment recommendations (latest only):**
  ```sql
  SELECT *
  FROM ops.replenishment_recommendation
  WHERE as_of_week_start = (SELECT MAX(as_of_week_start) FROM ops.replenishment_recommendation);
  ```

**Tips:**
- Metabase auto-discovers your schema, so you can use its GUI to build tables, trends, and charts quickly—or just run the raw SQL above.
- Scheduler will retry jobs every week. Logs let you debug silent failures.

---

## License

[Add your license here]