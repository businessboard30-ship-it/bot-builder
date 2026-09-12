from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from core.config import Config
from core.database import Database, create_pool
from core.token_encryption import decrypt_token
from modules.welcome import WelcomeChannelSelect
from modules.leveling import LevelingAnnounceChannelSelect
from modules.reaction_roles import ReactionRoleButton

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("generated-bot")


def enabled_modules() -> list[str]:
    raw = os.getenv("MODULES_ENABLED")
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    path = Path("modules_enabled.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("modules", [])
    return []


class GeneratedBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=config.prefix, intents=intents)
        self.config = config
        self.enabled_module_names = enabled_modules()
        self.db: Database | None = None

    async def setup_hook(self):
        self.db = await create_pool(self.config.database_url, self.config.bot_id)
        self.add_dynamic_items(WelcomeChannelSelect, LevelingAnnounceChannelSelect, ReactionRoleButton)
        @self.tree.command(name="support", description="Get this bot's support server")
        async def support(interaction: discord.Interaction):
            if self.config.support_server_url:
                await interaction.response.send_message(f"Support server: {self.config.support_server_url}")
            else:
                await interaction.response.send_message("This bot does not have a support server configured.", ephemeral=True)
        @self.tree.command(name="invite", description="Get this bot's invite link")
        async def invite(interaction: discord.Interaction):
            permissions = discord.Permissions(administrator=True).value
            url = f"https://discord.com/oauth2/authorize?client_id={self.user.id}&scope=bot%20applications.commands&permissions={permissions}"
            await interaction.response.send_message(f"Bot invite link: {url}", ephemeral=True)
        for module in ["help", *self.enabled_module_names]:
            try:
                await self.load_extension(f"modules.{module}")
                log.info("Loaded module: %s", module)
            except Exception:
                log.exception("Could not load module: %s", module)
        await self.tree.sync()
        self.heartbeat_loop.start()

    @tasks.loop(seconds=30)
    async def heartbeat_loop(self):
        if self.db:
            await self.db.heartbeat()

    async def close(self):
        self.heartbeat_loop.cancel()
        if self.db:
            await self.db.close()
        await super().close()


async def main():
    load_dotenv()
    encrypted = os.getenv("DISCORD_BOT_TOKEN_ENCRYPTED")
    if encrypted:
        os.environ["DISCORD_BOT_TOKEN"] = decrypt_token(encrypted, os.environ["TOKEN_ENCRYPTION_KEY"])
    config = Config.from_env()
    backoff = 15

    while True:
        bot = GeneratedBot(config)
        try:
            await bot.start(config.discord_bot_token)
            backoff = 15
        except discord.LoginFailure:
            log.error("Discord rejected the bot token; retrying in %ss", backoff)
        except (discord.HTTPException, OSError) as error:
            log.error("Discord connection failed (%s); retrying in %ss", error, backoff)
        finally:
            if not bot.is_closed():
                await bot.close()
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 300)


if __name__ == "__main__":
    asyncio.run(main())
