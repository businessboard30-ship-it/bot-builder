from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from wizard.session_store import create_session, get_active_session
from wizard.views import render

log = logging.getLogger(__name__)

MODULES = ("leveling", "welcome", "moderation", "economy", "reaction_roles", "starboard", "ticket", "giveaways", "schedule", "analytics", "voice_xp", "autopost", "automod", "help")


def module_metadata(module: str) -> tuple[str, str]:
    module_path = Path(__file__).resolve().parents[1] / "modules" / f"{module}.py"
    source = module_path.read_text(encoding="utf-8")
    loaded = importlib.import_module(f"modules.{module}")
    version = getattr(loaded, "MODULE_VERSION", "unknown")
    import hashlib
    return version, hashlib.sha256(source.encode("utf-8")).hexdigest()


class Build(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="build", description="Build or update a Discord bot")
    @app_commands.describe(action="Choose whether to start a build or check for updates")
    @app_commands.choices(action=[app_commands.Choice(name="new", value="new"), app_commands.Choice(name="update", value="update")])
    async def build(self, interaction: discord.Interaction, action: str = "new"):
        user_id = interaction.user.id
        if action == "update":
            return await self.update(interaction)
        row = await get_active_session(self.bot.db, user_id)
        if row:
            content, view = await render(self.bot, user_id, row)
            return await interaction.response.send_message("Welcome back! Resuming where you left off.\n" + content, view=view, ephemeral=True)
        count = len(await self.bot.db.fetch("SELECT bot_id FROM user_bots WHERE user_id=$1", str(user_id)))
        if count >= 3:
            return await interaction.response.send_message("You already have 3 bots, the maximum. Use /mybots to review them.", ephemeral=True)
        row = await create_session(self.bot.db, user_id)
        content, view = await render(self.bot, user_id, row)
        await interaction.response.send_message(content, view=view, ephemeral=True)

    async def update(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch(
            "SELECT bot_id, bot_name, modules_enabled, module_versions, module_schema_hashes "
            "FROM user_bots WHERE user_id=$1 ORDER BY created_at",
            str(interaction.user.id),
        )
        if not rows:
            return await interaction.response.send_message("You have no generated bots yet. Run /build to create one.", ephemeral=True)

        messages: list[str] = []
        for row in rows:
            versions = row["module_versions"] or {}
            stored_hashes = row["module_schema_hashes"] or {}
            changed: list[tuple[str, str, str, str]] = []
            for module in row["modules_enabled"] or []:
                current_version, current_hash = module_metadata(module)
                if versions.get(module) != current_version or stored_hashes.get(module) != current_hash:
                    changed.append((module, versions.get(module, "unknown"), current_version, current_hash))
            if not changed:
                continue

            updated_versions = {**versions, **{module: current for module, _, current, _ in changed}}
            updated_hashes = {**stored_hashes, **{module: current_hash for module, _, _, current_hash in changed}}
            await self.bot.db.execute(
                "UPDATE user_bots SET modules_enabled=$2::jsonb, module_versions=$3::jsonb, module_schema_hashes=$4::jsonb, "
                "last_regenerated_at=NOW(), last_heartbeat=NULL, status='active' WHERE bot_id=$1",
                row["bot_id"], json.dumps(row["modules_enabled"] or []), json.dumps(updated_versions), json.dumps(updated_hashes),
            )
            summary = "\n".join(f"- {module}: {old} -> {new}" for module, old, new, _ in changed)
            messages.append(f"**{row['bot_name']} updated.**\n{summary}\nThe supervisor will reload the hosted module code on its next managed restart.")

        message = "\n\n".join(messages) if messages else "All of your generated bots are already up to date. Nothing was generated."
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Build(bot))
