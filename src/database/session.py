"""Database session and connection management for SDC.
Authored under agency-database-optimizer.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator, Optional

from src.config import settings
from src.database.schema import SCHEMA_SQL


def run_migrations(conn: sqlite3.Connection) -> None:
    """Run idempotent schema migrations before SCHEMA_SQL creates indexes or constraints.
    
    This guarantees that if an older database exists without newly added columns,
    the columns are added safely before indexes like `idx_users_revocation` are created.
    """
    # Helper to inspect table columns
    def get_table_columns(table_name: str) -> set:
        cur = conn.cursor()
        try:
            cur.execute(f"PRAGMA table_info({table_name});")
            return {row[1] for row in cur.fetchall()}
        except Exception:
            return set()

    # Helper to check if a table exists
    def table_exists(table_name: str) -> bool:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table_name,))
        return cur.fetchone() is not None

    # 1. users table migrations
    if table_exists("users"):
        existing_cols = get_table_columns("users")
        user_migrations = [
            ("full_name", "TEXT"),
            ("school_name_custom", "TEXT"),
            ("city", "TEXT"),
            ("revocation_cutoff_epoch", "REAL NOT NULL DEFAULT 0.0"),
        ]
        for col_name, col_def in user_migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def};")

    # 2. assignments table migrations
    if table_exists("assignments"):
        existing_cols = get_table_columns("assignments")
        assignment_migrations = [
            ("status", "TEXT DEFAULT 'PUBLISHED'"),
            ("generation_source", "TEXT DEFAULT 'MANUAL'"),
            ("target_class_level", "INTEGER"),
            ("subject", "TEXT"),
            ("questions_json", "TEXT"),
            ("rubric_json", "TEXT"),
            ("source_reference", "TEXT"),
        ]
        for col_name, col_def in assignment_migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE assignments ADD COLUMN {col_name} {col_def};")

    # 3. assignment_submissions table migrations
    if table_exists("assignment_submissions"):
        existing_cols = get_table_columns("assignment_submissions")
        submission_migrations = [
            ("answers_json", "TEXT"),
            ("grading_status", "TEXT DEFAULT 'GRADED'"),
            ("grading_details_json", "TEXT"),
            ("grading_confidence", "REAL"),
            ("attempt_number", "INTEGER DEFAULT 1"),
            ("is_late", "INTEGER DEFAULT 0"),
            ("retry_count", "INTEGER DEFAULT 0"),
        ]
        for col_name, col_def in submission_migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE assignment_submissions ADD COLUMN {col_name} {col_def};")

    # 4. attempts table migrations
    if table_exists("attempts"):
        existing_cols = get_table_columns("attempts")
        if "attempt_uuid" not in existing_cols:
            conn.execute("ALTER TABLE attempts ADD COLUMN attempt_uuid TEXT;")

    # 5. request-level model provenance for generated quizzes
    if table_exists("quiz_sessions"):
        quiz_migrations = [
            ("model_used", "TEXT"),
            ("inference_request_id", "TEXT"),
            ("inference_status", "TEXT DEFAULT 'NOT_RUN'"),
        ]
        existing_cols = get_table_columns("quiz_sessions")
        for col_name, col_def in quiz_migrations:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE quiz_sessions ADD COLUMN {col_name} {col_def};")


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes safely for fresh and existing databases."""
    target_path = Path(db_path) if db_path else settings.get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path), timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")

        # Run pre-schema migrations to guarantee columns exist before indexes referencing them
        run_migrations(conn)

        # Apply schema (tables if not exist, indexes if not exist)
        conn.executescript(SCHEMA_SQL)

        # Run migrations again post-script in case new tables were created in this run
        run_migrations(conn)

        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connection.
    Enforces WAL mode, synchronous NORMAL, busy_timeout=5000, and foreign keys on every connection.
    """
    target_path = Path(db_path) if db_path else settings.get_db_path()
    conn = sqlite3.connect(str(target_path), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
