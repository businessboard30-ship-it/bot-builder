from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands, tasks

from wizard import session_store
from wizard.views import ModuleView
from commands.mybots import ManageBotButton, ModuleToggle
from commands.payment_review import PaymentReviewButton
from dotenv import load_dotenv

from core.config import Config
from core.database import Database, close_pool, create_pool
from core.migrate import run_migrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot-builder")


def enabled_modules() -> list[str]:
    raw = os.getenv("MODULES_ENABLED")
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    path = Path("modules_enabled.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("modules", [])
    return ["leveling", "welcome", "moderation", "economy"]


class BotBuilder(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=config.prefix, intents=intents)
        self.config = config
        self.db: Database | None = None

    @tasks.loop(hours=1)
    async def session_expiry_loop(self):
        if self.db:
            await session_store.expire_old_sessions(self.db)

    @session_expiry_loop.before_loop
    async def wait_for_ready(self):
        await self.wait_until_ready()

    async def setup_hook(self):
        self.db = await create_pool(self.config.database_url, self.config.bot_id)
        self.add_dynamic_items(ManageBotButton, ModuleToggle, PaymentReviewButton)
        self.session_expiry_loop.start()
        for extension in ("commands.build", "commands.mybots", "commands.payment_review"):
            try:
                await self.load_extension(extension)
                log.info("Loaded extension: %s", extension)
            except Exception:
                log.exception("Could not load extension: %s; continuing", extension)
        for module in enabled_modules():
            try:
                await self.load_extension(f"modules.{module}")
                log.info("Loaded module: %s", module)
            except Exception:
                log.exception("Could not load module: %s; continuing", module)
        # Re-register persistent wizard views so stable custom_ids survive a restart.
        for row in await self.db.fetch("SELECT user_id FROM wizard_sessions WHERE status='active'"):
            self.add_view(ModuleView(self, row["user_id"]))
        await self.tree.sync()

    async def on_guild_join(self, guild: discord.Guild):
        log.info("Joined guild: %s (%s)", guild.name, guild.id)
        for admin_id in self.config.admin_user_ids:
            try:
                user = await self.fetch_user(admin_id)
                await user.send(
                    f"✅ Added to a new server:\n**{guild.name}**\nServer ID: `{guild.id}`\nMembers: {guild.member_count}"
                )
            except (discord.Forbidden, discord.HTTPException):
                log.warning("Could not DM admin %s about new guild join", admin_id)

    async def close(self):
        if not self.session_expiry_loop.is_being_cancelled():
            self.session_expiry_loop.cancel()
        if self.db is not None:
            await close_pool(self.db)
        await super().close()


async def main():
    load_dotenv()
    config = Config.from_env()
    await run_migrations(config.database_url)
    bot = BotBuilder(config)

    @bot.event
    async def on_ready():
        log.info("%s is online as %s", config.bot_name, bot.user)

    try:
        await bot.start(config.discord_bot_token)
    except discord.LoginFailure:
        log.error("Discord rejected the bot token. Check DISCORD_BOT_TOKEN in your environment variables.")
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
