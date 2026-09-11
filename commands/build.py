from __future__ import annotations

import importlib
import json
import discord
from discord import app_commands
from discord.ext import commands

from wizard.session_store import create_session, get_active_session
from wizard.views import render

MODULES = ("leveling", "welcome", "moderation", "economy")

class Build(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="build", description="Build or update a Discord bot")
    @app_commands.describe(action="Choose whether to start a build or check for updates")
    @app_commands.choices(action=[app_commands.Choice(name="new", value="new"), app_commands.Choice(name="update", value="update")])
    async def build(self, interaction: discord.Interaction, action: str = "new"):
        user_id = interaction.user.id
        if action == "update": return await self.update(interaction)
        row = await get_active_session(self.bot.db, user_id)
        if row:
            content, view = await render(self.bot, user_id, row)
            return await interaction.response.send_message("Welcome back! Resuming where you left off.\n" + content, view=view, ephemeral=True)
        count = len(await self.bot.db.fetch("SELECT bot_id FROM user_bots WHERE user_id=$1", user_id))
        if count >= 3:
            return await interaction.response.send_message("You already have 3 bots, the maximum. Use /mybots to review them.", ephemeral=True)
        row = await create_session(self.bot.db, user_id)
        content, view = await render(self.bot, user_id, row)
        await interaction.response.send_message(content, view=view, ephemeral=True)

    async def update(self, interaction):
        rows = await self.bot.db.fetch("SELECT bot_id, bot_name, modules_enabled, module_versions FROM user_bots WHERE user_id=$1 ORDER BY created_at", interaction.user.id)
        if not rows: return await interaction.response.send_message("You have no generated bots yet. Run /build to create one.", ephemeral=True)
        lines = ["**Bot updates**"]
        for row in rows:
            versions = row["module_versions"] or {}
            changed = []
            for module in row["modules_enabled"] or []:
                current = getattr(importlib.import_module(f"modules.{module}"), "MODULE_VERSION", "unknown")
                if versions.get(module) != current: changed.append(f"{module}: version {versions.get(module, 'unknown')} → {current} available")
            lines.append(f"**{row['bot_name']}** — " + ("; ".join(changed) if changed else "Already up to date"))
        lines.append("\nTODO: file regeneration and deployment packaging will be added in Prompt 3.")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

async def setup(bot): await bot.add_cog(Build(bot))
