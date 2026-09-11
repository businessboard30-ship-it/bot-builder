from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    database_url: str
    prefix: str = "!"
    bot_name: str = "Bot Builder"
    currency_name: str = "coins"
    encryption_key: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        missing = [name for name in ("DISCORD_BOT_TOKEN", "DATABASE_URL") if not os.getenv(name)]
        if missing:
            details = ", ".join(missing)
            raise ValueError(
                f"Missing {details}. Check your Railway/Fly.io environment variables tab and add them before starting the bot."
            )
        return cls(
            discord_bot_token=os.environ["DISCORD_BOT_TOKEN"],
            database_url=os.environ["DATABASE_URL"],
            prefix=os.getenv("PREFIX", "!"),
            bot_name=os.getenv("BOT_NAME", "Bot Builder"),
            currency_name=os.getenv("CURRENCY_NAME", "coins"),
            encryption_key=os.getenv("ENCRYPTION_KEY"),
        )


__all__ = ["Config"]
