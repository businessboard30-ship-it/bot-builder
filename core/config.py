from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    database_url: str
    bot_id: str
    encryption_key: str
    bot_name: str
    prefix: str
    currency_name: str
    support_server_url: str | None
    admin_review_channel_id: int | None
    admin_user_ids: frozenset[int]

    @classmethod
    def from_env(cls) -> "Config":
        required = ("DISCORD_BOT_TOKEN", "DATABASE_URL", "BOT_ID", "TOKEN_ENCRYPTION_KEY")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(
            discord_bot_token=os.environ["DISCORD_BOT_TOKEN"],
            database_url=os.environ["DATABASE_URL"],
            bot_id=os.environ["BOT_ID"],
            encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
            bot_name=os.getenv("BOT_NAME", "Generated Bot"),
            prefix=os.getenv("PREFIX", "!"),
            currency_name=os.getenv("CURRENCY_NAME", "coins"),
            support_server_url=os.getenv("SUPPORT_SERVER_URL") or None,
            admin_review_channel_id=int(os.environ["ADMIN_REVIEW_CHANNEL_ID"]) if os.getenv("ADMIN_REVIEW_CHANNEL_ID") else None,
            admin_user_ids=frozenset(int(value) for value in os.getenv("ADMIN_USER_IDS", "").split(",") if value.strip()),
        )
