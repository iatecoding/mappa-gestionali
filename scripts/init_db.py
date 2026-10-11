#!/usr/bin/env python3
"""Create the local SQLite catalogue from the versioned schema."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "catalog.sqlite")
    parser.add_argument("--force", action="store_true", help="recreate an existing empty/nonempty database")
    args = parser.parse_args()

    if args.database.exists() and not args.force:
        print(f"Database già presente: {args.database}. Usa --force per ricrearlo.")
        return 1
    args.database.parent.mkdir(parents=True, exist_ok=True)
    if args.database.exists():
        args.database.unlink()

    schema = (ROOT / "schemas" / "001_initial.sql").read_text(encoding="utf-8")
    connection = sqlite3.connect(args.database)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        connection.execute("INSERT INTO schema_meta(key, value) VALUES (?, ?)", ("schema_version", "1"))
        connection.commit()
    finally:
        connection.close()
    print(f"Creato database: {args.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
