MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []

import json

import discord
from discord.ext import commands
from discord import app_commands
from core.base_cog import BaseCog
from core.components_v2 import panel
from datetime import timedelta


class Automod(BaseCog):
    @app_commands.command(name="automod", description="Configure automod")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod(self, interaction, enabled: bool = True, blocked_words: str = "", window_minutes: app_commands.Range[int, 1, 60] = 10, timeout_at: app_commands.Range[int, 1, 20] = 3, kick_at: app_commands.Range[int, 2, 30] = 5, ban_at: app_commands.Range[int, 3, 50] = 7):
        if not (timeout_at < kick_at < ban_at):
            return await interaction.response.send_message("Thresholds must be timeout < kick < ban.", ephemeral=True)
        words = [word.casefold() for word in blocked_words.split(",") if word.strip()][:100]
        await self.db.execute(
            "INSERT INTO automod_settings(bot_id,guild_id,enabled,blocked_words,violation_window_minutes,timeout_threshold,kick_threshold,ban_threshold) VALUES($1::uuid,$2,$3,$4::jsonb,$5,$6,$7,$8) "
            "ON CONFLICT(bot_id,guild_id) DO UPDATE SET enabled=$3, blocked_words=$4::jsonb, violation_window_minutes=$5, timeout_threshold=$6, kick_threshold=$7, ban_threshold=$8",
            self.bot.config.bot_id, interaction.guild_id, enabled, json.dumps(words), window_minutes, timeout_at, kick_at, ban_at,
        )
        await interaction.response.send_message(
            f"Automod {'enabled' if enabled else 'disabled'} with {len(words)} blocked words; escalation {timeout_at}/{kick_at}/{ban_at} in {window_minutes}m.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        row = await self.db.fetchrow(
            "SELECT enabled, blocked_words, violation_window_minutes, timeout_threshold, kick_threshold, ban_threshold FROM automod_settings WHERE bot_id=$1::uuid AND guild_id=$2",
            self.bot.config.bot_id, message.guild.id,
        )
        if not row or not row["enabled"]:
            return
        content = message.content.casefold()
        words = row["blocked_words"] or []
        invite_link = "discord.gg/" in content or "discord.com/invite/" in content
        if any(word and word in content for word in words) or invite_link:
            violation_count = await self.db.fetchval(
                "INSERT INTO automod_violations(bot_id,guild_id,user_id,reason) VALUES($1::uuid,$2,$3,$4) RETURNING id",
                self.bot.config.bot_id, message.guild.id, message.author.id, "invite" if invite_link else "blocked_word",
            )
            violation_count = await self.db.fetchval(
                "SELECT COUNT(*) FROM automod_violations WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3 "
                "AND created_at >= NOW() - ($4 * INTERVAL '1 minute')",
                self.bot.config.bot_id, message.guild.id, message.author.id, row["violation_window_minutes"],
            )
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            try:
                if violation_count >= row["ban_threshold"] and isinstance(message.author, discord.Member):
                    await message.author.ban(reason="Automod repeated violations")
                elif violation_count >= row["kick_threshold"] and isinstance(message.author, discord.Member):
                    await message.author.kick(reason="Automod repeated violations")
                elif violation_count >= row["timeout_threshold"] and isinstance(message.author, discord.Member):
                    await message.author.timeout(discord.utils.utcnow() + timedelta(minutes=10), reason="Automod repeated violations")
            except discord.HTTPException:
                pass
            try:
                await message.channel.send(
                    view=panel("Automod action", f"{message.author.mention}, that message was removed by automod."), delete_after=5
                )
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(Automod(bot))
