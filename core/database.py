"""Small asyncpg database wrapper for generated bots."""
from __future__ import annotations

import asyncpg


class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> asyncpg.Pool:
        self.pool = await asyncpg.create_pool(self.database_url)
        return self.pool

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool is not connected.")
        return self.pool

    async def fetch(self, query: str, *args):
        return await self._require_pool().fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        return await self._require_pool().fetchrow(query, *args)

    async def execute(self, query: str, *args):
        return await self._require_pool().execute(query, *args)

    async def executemany(self, query: str, args):
        return await self._require_pool().executemany(query, args)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *_exc):
        await self.close()


async def create_pool(database_url: str) -> Database:
    database = Database(database_url)
    await database.connect()
    return database


async def close_pool(database: Database | None) -> None:
    if database:
        await database.close()


async def init_database(database: Database) -> None:
    """Run the combined schema during startup when desired."""
    from pathlib import Path

    schema = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    await database.execute(schema.read_text(encoding="utf-8"))


__all__ = ["Database", "create_pool", "close_pool", "init_database"]
