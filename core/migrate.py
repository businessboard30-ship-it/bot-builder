"""Runs every SQL file in sql/ against the database on startup.

Safe to run every time the app starts: every statement in the sql/ files
uses CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS, so re-running
an already-applied file does nothing.
"""

from __future__ import annotations

import logging
from pathlib import Path

import asyncpg

log = logging.getLogger("migrate")

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


async def run_migrations(database_url: str) -> None:
    conn = await asyncpg.connect(database_url)
    try:
        sql_files = sorted(SQL_DIR.glob("*.sql"))
        if not sql_files:
            log.warning("No SQL files found in %s", SQL_DIR)
            return

        for path in sql_files:
            sql = path.read_text()
            if not sql.strip():
                continue
            try:
                await conn.execute(sql)
                log.info("Migration applied: %s", path.name)
            except Exception:
                log.exception("Migration failed on %s", path.name)
                raise
    finally:
        await conn.close()
