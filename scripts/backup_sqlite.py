"""Create and verify a consistent SQLite backup without modifying its source."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys


def backup_database(source: Path, output_dir: Path) -> Path:
    source = source.resolve(strict=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = output_dir / f"{source.stem}_{stamp}.db"
    temporary = output_dir / f".{destination.name}.tmp"
    if destination.exists() or temporary.exists():
        raise FileExistsError("Backup destination already exists; refusing to overwrite it.")

    try:
        source_uri = source.as_uri() + "?mode=ro"
        source_conn = sqlite3.connect(source_uri, uri=True)
        backup_conn = sqlite3.connect(temporary)
        try:
            source_conn.backup(backup_conn)
            check = backup_conn.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {check}")
            foreign_key_errors = backup_conn.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_errors:
                print(f"Notice: SQLite backup recorded {len(foreign_key_errors)} legacy foreign-key reference(s).", file=sys.stderr)
            backup_conn.commit()
        finally:
            backup_conn.close()
            source_conn.close()
        temporary.replace(destination)
        return destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True, help="SQLite database to back up")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for the new verified backup")
    args = parser.parse_args()
    try:
        backup = backup_database(args.database, args.output_dir)
    except Exception as exc:
        print(f"Backup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"Verified SQLite backup created: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
