from __future__ import annotations

import importlib
import io
import json
import logging
import discord
from discord import app_commands
from discord.ext import commands

from wizard.session_store import create_session, get_active_session
from core.generator import generate_update_package, module_schema_hash
from wizard.views import render, safe_filename

log = logging.getLogger(__name__)

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
        rows = await self.bot.db.fetch("SELECT bot_id, bot_name, modules_enabled, module_versions, module_schema_hashes FROM user_bots WHERE user_id=$1 ORDER BY created_at", interaction.user.id)
        if not rows:
            return await interaction.response.send_message("You have no generated bots yet. Run /build to create one.", ephemeral=True)

        updated_any = False
        response_sent = False
        for row in rows:
            versions = row["module_versions"] or {}
            stored_hashes = row["module_schema_hashes"] or {}
            changed_modules = []
            schema_changed_modules = []
            for module in row["modules_enabled"] or []:
                current = getattr(importlib.import_module(f"modules.{module}"), "MODULE_VERSION", "unknown")
                if versions.get(module) != current:
                    current_hash = module_schema_hash(module)
                    schema_changed = stored_hashes.get(module) not in (None, current_hash)
                    changed_modules.append((module, versions.get(module, "unknown"), current, schema_changed, current_hash))
                    if schema_changed:
                        schema_changed_modules.append(module)

            if not changed_modules:
                continue
            updated_any = True
            names = [item[0] for item in changed_modules]
            summary = "\n".join(
                f"- {module}: {old} -> {new} ({'database changes' if schema_changed else 'code only, no database changes'})"
                for module, old, new, schema_changed, _ in changed_modules
            )
            try:
                package_bytes = generate_update_package(names, schema_changed_modules)
                updated_versions = {**versions, **{module: current for module, _, current, _, _ in changed_modules}}
                updated_hashes = {**stored_hashes, **{module: current_hash for module, _, _, _, current_hash in changed_modules}}
                await self.bot.db.execute(
                    "UPDATE user_bots SET module_versions=$2::jsonb, module_schema_hashes=$3::jsonb, last_regenerated_at=NOW() WHERE bot_id=$1",
                    row["bot_id"], json.dumps(updated_versions), json.dumps(updated_hashes),
                )
                attachment = discord.File(io.BytesIO(package_bytes), filename=f"{safe_filename(row['bot_name'])}-update.zip")
                migration_note = "A migration.sql file is included for modules with changed SQL." if schema_changed_modules else "No migration.sql was generated because these updates contain no database changes."
                message = f"**{row['bot_name']} has updates.**\n{summary}\n{migration_note}"
                if response_sent:
                    await interaction.followup.send(message, file=attachment, ephemeral=True)
                else:
                    await interaction.response.send_message(message, file=attachment, ephemeral=True)
                    response_sent = True
            except Exception:
                log.exception("Bot update generation failed for %s", row["bot_id"])
                message = f"I could not generate the update package for **{row['bot_name']}**. Please try again and check the bot logs."
                if response_sent:
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
                    response_sent = True
                continue

        if not updated_any:
            await interaction.response.send_message("All of your generated bots are already up to date. Nothing was generated.", ephemeral=True)

async def setup(bot): await bot.add_cog(Build(bot))
