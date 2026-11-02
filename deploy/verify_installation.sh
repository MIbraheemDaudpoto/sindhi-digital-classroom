#!/bin/bash
# ==============================================================================
# SDC Pilot: Quick Verification Script for Field Technicians
# Verifies systemd status, port 8000 listening, SQLite WAL mode, canonical chunks,
# and HTTP health endpoints on Raspberry Pi 5.
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " SDC Field Diagnostic & Verification Tool"
echo " Date: $(date)"
echo " Host: $(hostname)"
echo "=========================================================="

FAILED=0

# 1. Check systemd service status
echo -n "[1/6] Checking sdc-pilot.service status... "
if systemctl is-active --quiet sdc-pilot.service; then
    echo "ACTIVE (OK)"
else
    echo "FAILED (Service not active)"
    FAILED=1
fi

# 2. Check Port 8000 Binding
echo -n "[2/6] Checking Port 8000 listening... "
if ss -tuln | grep -q ":8000"; then
    echo "LISTENING (OK)"
else
    echo "FAILED (Port 8000 not open)"
    FAILED=1
fi

# 3. Check SQLite DB exists and is in WAL mode
echo -n "[3/6] Checking SQLite WAL mode... "
DB_PATH="/home/pi/sdc-pilot/data/sdc_platform.db"
if [ -f "$DB_PATH" ]; then
    WAL_MODE=$(sqlite3 "$DB_PATH" "PRAGMA journal_mode;")
    if [ "$WAL_MODE" = "wal" ]; then
        echo "WAL MODE (OK)"
    else
        echo "WARNING (Journal mode is $WAL_MODE, not wal)"
    fi
else
    echo "FAILED (Database file not found at $DB_PATH)"
    FAILED=1
fi

# 4. Check canonical chunks count
echo -n "[4/6] Verifying canonical data tables... "
if [ -f "$DB_PATH" ]; then
    CHUNKS_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM sdc_chunks;")
    GLOSSARY_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM sdc_glossary;")
    EXERCISES_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM sdc_exercises;")
    VIDEOS_COUNT=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM sdc_videos;")
    echo "CHUNKS=$CHUNKS_COUNT, GLOSSARY=$GLOSSARY_COUNT, EXERCISES=$EXERCISES_COUNT, VIDEOS=$VIDEOS_COUNT (OK)"
else
    echo "SKIPPED"
fi

# 5. Check API health endpoint
echo -n "[5/6] Testing GET http://127.0.0.1:8000/api/health... "
HEALTH_RESP=$(curl -s --max-time 5 http://127.0.0.1:8000/api/health || echo "")
if echo "$HEALTH_RESP" | grep -q "ok"; then
    echo "HEALTHY (OK)"
else
    echo "FAILED (Endpoint not responding)"
    FAILED=1
fi

# 6. Check Classroom PWA HTML
echo -n "[6/6] Testing GET http://127.0.0.1:8000/classroom... "
CLASSROOM_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/classroom || echo "000")
if [ "$CLASSROOM_HTTP" = "200" ]; then
    echo "HTTP 200 (OK)"
else
    echo "FAILED (HTTP $CLASSROOM_HTTP)"
    FAILED=1
fi

echo "=========================================================="
if [ "$FAILED" -eq 0 ]; then
    echo " ALL DIAGNOSTIC CHECKS PASSED! System is ready for class."
    echo " Access from Android tablets: http://$(hostname -I | awk '{print $1}'):8000/classroom"
else
    echo " DIAGNOSTIC CHECKS FAILED! Run: sudo journalctl -u sdc-pilot.service -n 50"
fi
echo "=========================================================="
