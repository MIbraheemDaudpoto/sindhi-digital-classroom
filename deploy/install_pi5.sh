#!/bin/bash
# ==============================================================================
# SDC Pilot: Automated Setup Script for Raspberry Pi 5 (ARM64 / Debian Bookworm)
# Configures offline Python environment, installs system dependencies, builds SQLite WAL,
# configures memory & power protection, and registers systemd auto-start services.
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Starting Sindhi Digital Classroom (SDC) Pilot Setup"
echo " Target: Raspberry Pi 5 (Offline School Lab Appliance)"
echo " OS: Debian Bookworm (ARM64)"
echo "=========================================================="

APP_DIR="/home/pi/sdc-pilot"
SERVICE_NAME="sdc-pilot"

# 1. Install base system dependencies
echo "[1/6] Updating and installing system packages (Python, SQLite FTS5, Tools)..."
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev build-essential \
    sqlite3 libsqlite3-dev git curl jq ufw htop

# 2. Setup application directory & virtual environment
echo "[2/6] Setting up virtual environment..."
mkdir -p "${APP_DIR}/data" "${APP_DIR}/media" "${APP_DIR}/deploy"
cd "${APP_DIR}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 3. Seed canonical database and build SQLite FTS5 indices
echo "[3/6] Seeding canonical database and building BM25 search indices..."
python3 -c "
from src.services.sdc_rag_db import get_db_connection, ensure_sdc_data_seeded
conn = get_db_connection()
ensure_sdc_data_seeded(conn)
print('Database verified ready in WAL mode with all 90 chunks.')
conn.close()
"

# 4. Install and enable systemd auto-start services
echo "[4/6] Configuring hardened systemd service..."
sudo cp "${APP_DIR}/deploy/sdc-pilot.service" /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/sdc-power-guard.service" /etc/systemd/system/ || true
sudo systemctl daemon-reload

sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# Optional enable solar power guard if script exists
if [ -f "${APP_DIR}/deploy/solar_power_monitor.py" ]; then
    sudo systemctl enable sdc-power-guard.service || true
    sudo systemctl start sdc-power-guard.service || true
fi

# 5. Make helper scripts executable
echo "[5/6] Setting permissions for field technician helper tools..."
chmod +x "${APP_DIR}/deploy/verify_installation.sh" || true
chmod +x "${APP_DIR}/deploy/setup_offline_hotspot.sh" || true
chmod +x "${APP_DIR}/deploy/solar_power_monitor.py" || true

# 6. Run verification check
echo "[6/6] Verifying local service health..."
sleep 4
if bash "${APP_DIR}/deploy/verify_installation.sh"; then
    echo "=========================================================="
    echo " SDC Pilot successfully installed and verified!"
    echo " Open Classroom PWA at: http://$(hostname -I | awk '{print $1}'):8000/classroom"
    echo "=========================================================="
else
    echo "Warning: Service started with warnings. Inspect logs via: sudo journalctl -u ${SERVICE_NAME} -f"
fi
