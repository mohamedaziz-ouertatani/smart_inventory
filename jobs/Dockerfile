# Python jobs image for ingestion and preprocessing
FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY jobs/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy job sources
COPY jobs ./jobs

# Default command; will be overridden by `docker compose run jobs <command>`
CMD ["sleep", "infinity"]