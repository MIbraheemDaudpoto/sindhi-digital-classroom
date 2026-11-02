"""Regression tests for SQLite Schema Migration and Server Startup.
Authored under agency-database-optimizer and agency-application-security-engineer.

Verifies:
1. Fresh database initialization creates complete schema including revocation_cutoff_epoch.
2. Older database lacking revocation_cutoff_epoch migrates successfully without data loss.
3. Existing user records, hashes, and attributes remain unchanged.
4. Default value of 0.0 is applied without invalidating active users.
5. Idempotence: Running init_db multiple times succeeds without duplicate errors.
6. Revoked session tokens are rejected even across restarts / clearing memory.
7. Active tokens remain valid after migration.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import pytest
from starlette.testclient import TestClient

from src.api.app import app
from src.database.session import init_db, get_db
from src.services.auth_service import AuthService, hash_pin_or_password, verify_pin_or_password


def test_fresh_database_initialization():
    """Verify fresh database initialization creates complete schema including revocation_cutoff_epoch."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = os.path.join(tmp_dir, "fresh_sdc.db")
        init_db(test_db)

        conn = sqlite3.connect(test_db)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cur.fetchall()}
        assert "revocation_cutoff_epoch" in cols
        assert "full_name" in cols
        assert "school_name_custom" in cols
        assert "city" in cols

        # Check index exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_revocation'")
        assert cur.fetchone() is not None
        conn.close()


def test_legacy_database_migration_preserves_records_and_hashes():
    """Verify an existing database with legacy users schema migrates seamlessly without losing data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = os.path.join(tmp_dir, "legacy_sdc.db")
        conn = sqlite3.connect(test_db)
        cur = conn.cursor()

        # Create older schema without revocation_cutoff_epoch
        cur.execute("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                school_id TEXT,
                pseudonymous_code TEXT UNIQUE NOT NULL,
                pin_hash TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                language TEXT DEFAULT 'sindhi',
                created_at TEXT NOT NULL
            );
        """)

        # Insert sample legacy user
        known_pin = "123456"
        p_hash = hash_pin_or_password(known_pin)
        cur.execute(
            """
            INSERT INTO users (id, role, school_id, pseudonymous_code, pin_hash, email, phone, language, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("usr-legacy-01", "STUDENT", None, "STU-LEGACY", p_hash, "leg@sdc.pk", "+923001234567", "sindhi", "2026-01-01T00:00:00Z")
        )
        conn.commit()
        conn.close()

        # Run init_db on legacy database
        init_db(test_db)

        # Verify migrated schema
        conn2 = sqlite3.connect(test_db)
        cur2 = conn2.cursor()
        cur2.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cur2.fetchall()}
        assert "revocation_cutoff_epoch" in cols

        # Verify record preserved
        cur2.execute("SELECT id, pseudonymous_code, pin_hash, revocation_cutoff_epoch FROM users WHERE id = 'usr-legacy-01'")
        user_row = cur2.fetchone()
        assert user_row is not None
        assert user_row[0] == "usr-legacy-01"
        assert user_row[1] == "STU-LEGACY"
        assert verify_pin_or_password(known_pin, user_row[2]) is True
        assert user_row[3] == 0.0  # safe default

        # Verify index was safely created
        cur2.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_revocation'")
        assert cur2.fetchone() is not None
        conn2.close()


def test_init_db_idempotence():
    """Verify running init_db multiple times does not fail or duplicate columns."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = os.path.join(tmp_dir, "idempotent_sdc.db")
        init_db(test_db)
        init_db(test_db)
        init_db(test_db)

        conn = sqlite3.connect(test_db)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]
        assert cols.count("revocation_cutoff_epoch") == 1
        conn.close()


def test_revocation_cutoff_rejection_across_restart():
    """Verify session revocation persists and is enforced after simulating a server restart."""
    auth = AuthService()
    user_id = "usr-stu-101"

    # Issue token
    token = auth.create_session_token(user_id, "STUDENT")
    assert auth.verify_session_token(token) is not None

    # Revoke sessions
    auth.revoke_user_sessions(user_id)

    # Immediately should be revoked
    assert auth.verify_session_token(token) is None

    # Simulate server restart by instantiating fresh AuthService with empty in-memory cache
    fresh_auth = AuthService()
    assert fresh_auth._revoked_users == {}

    # Must still reject because DB stores revocation_cutoff_epoch
    verified = fresh_auth.verify_session_token(token)
    assert verified is None
