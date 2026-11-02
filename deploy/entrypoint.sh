#!/bin/bash
set -e

echo "=========================================================="
echo " Starting Sindhi Digital Classroom (SDC) LMS Production"
echo "=========================================================="

# 1. Resolve Port (Hugging Face Spaces defaults to 7860, Render/Railway to 8000 or $PORT)
if [ -n "$PORT" ]; then
    APP_PORT="$PORT"
elif [ -n "$SPACE_ID" ]; then
    APP_PORT="7860"
else
    APP_PORT="8000"
fi

# 2. Ensure data directory exists and has correct permissions
mkdir -p /app/data
mkdir -p /app/data/backups

# 3. Seed / Initialize Database if missing from persistent volume
if [ ! -f "/app/data/sdc_platform.db" ]; then
    echo "[Entrypoint] No existing database found at /app/data/sdc_platform.db."
    if [ -f "/app/seed_data/sdc_platform.db" ]; then
        echo "[Entrypoint] Copying pre-seeded production database..."
        cp /app/seed_data/sdc_platform.db /app/data/sdc_platform.db
    else
        echo "[Entrypoint] Initializing database via startup lifespan..."
    fi
fi

# 4. Verify SQLite Integrity
if [ -f "/app/data/sdc_platform.db" ]; then
    echo "[Entrypoint] Verifying SQLite database integrity..."
    python -c "
import sqlite3
conn = sqlite3.connect('/app/data/sdc_platform.db')
check = conn.execute('PRAGMA integrity_check').fetchone()[0]
print(f'[Entrypoint] Database integrity check: {check}')
if check != 'ok':
    raise RuntimeError('Database integrity check failed!')
"
fi

echo "[Entrypoint] Launching SDC FastAPI on 0.0.0.0:${APP_PORT}..."
exec uvicorn src.api.app:app --host 0.0.0.0 --port "${APP_PORT}"

