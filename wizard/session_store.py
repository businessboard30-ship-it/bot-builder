from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from core.database import Database


async def create_session(db: Database, user_id: int) -> dict[str, Any]:
    row = await db.fetchrow(
        """INSERT INTO wizard_sessions(user_id) VALUES($1)
        ON CONFLICT(user_id) DO UPDATE SET current_step=1, answers='{}'::jsonb,
        started_at=NOW(), expires_at=NOW()+INTERVAL '24 hours', status='active'
        RETURNING *""", user_id)
    return dict(row)


async def get_active_session(db: Database, user_id: int) -> dict[str, Any] | None:
    row = await db.fetchrow(
        """UPDATE wizard_sessions SET status='expired' WHERE user_id=$1
        AND status='active' AND expires_at <= NOW()
        RETURNING user_id""", user_id)
    if row:
        return None
    row = await db.fetchrow("SELECT * FROM wizard_sessions WHERE user_id=$1 AND status='active'", user_id)
    return dict(row) if row else None


async def update_session(db: Database, user_id: int, step: int, answers: dict[str, Any]) -> None:
    await db.execute(
        "UPDATE wizard_sessions SET current_step=$2, answers=$3::jsonb, expires_at=NOW()+INTERVAL '24 hours' WHERE user_id=$1 AND status='active'",
        user_id, step, json.dumps(answers))


async def expire_old_sessions(db: Database) -> None:
    await db.execute("UPDATE wizard_sessions SET status='expired' WHERE status='active' AND expires_at <= NOW()")


async def complete_session(db: Database, user_id: int) -> None:
    await db.execute("UPDATE wizard_sessions SET status='completed', expires_at=NOW() WHERE user_id=$1 AND status='active'", user_id)
