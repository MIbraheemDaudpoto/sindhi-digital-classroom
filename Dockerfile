# ==============================================================================
# Sindhi Digital Classroom (SDC) LMS — Production Dockerfile
# Optimized for 100% Free / Zero-Card Cloud Hosts:
# - Hugging Face Spaces (Port 7860, No Card, 16GB RAM)
# - Render / Railway / Fly.io / Koyeb / Docker VPS (Port 8000 / $PORT)
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    ENVIRONMENT=production \
    DATABASE_PATH=/app/data/sdc_platform.db

# Install minimal OS dependencies for SQLite & Healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source, static assets, and scripts
COPY src/ ./src/
COPY static/ ./static/
COPY scripts/ ./scripts/
COPY deploy/entrypoint.sh ./deploy/entrypoint.sh

# Pre-seed curriculum and RAG data if present in data/
COPY data/ ./seed_data/

# Make entrypoint script executable
RUN chmod +x ./deploy/entrypoint.sh

# Create non-root system user for container security
RUN useradd -m -u 1000 sdcuser && \
    mkdir -p /app/data /app/data/backups && \
    chown -R sdcuser:sdcuser /app

# Switch to non-root user
USER sdcuser

# Expose standard web ports: 8000 (Render/PaaS/VPS) and 7860 (Hugging Face Spaces)
EXPOSE 8000 7860

# Container Healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Launch through hardened production entrypoint
ENTRYPOINT ["/app/deploy/entrypoint.sh"]

