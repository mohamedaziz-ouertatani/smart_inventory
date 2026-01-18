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

1. Create a new SQL file in `db/migrations/` with sequential naming (e.g., `05_new_feature.sql`)
2. Migrations are automatically applied on fresh volumes or via `scripts/db_init.sh`

## License

[Add your license here]
