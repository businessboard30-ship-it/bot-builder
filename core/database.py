from __future__ import annotations

from typing import Any

import asyncpg


class Database:
    def __init__(self, pool: asyncpg.Pool, bot_id: str):
        self.pool = pool
        self.bot_id = bot_id

    async def heartbeat(self) -> None:
        await self.pool.execute(
            "UPDATE user_bots SET last_heartbeat = NOW(), status = 'active' WHERE bot_id = $1::uuid",
            self.bot_id,
        )

    async def close(self) -> None:
        await self.pool.close()

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        return await self.pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        return await self.pool.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        return await self.pool.execute(query, *args)


async def create_pool(database_url: str, bot_id: str) -> Database:
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5, command_timeout=15)
    return Database(pool, bot_id)
