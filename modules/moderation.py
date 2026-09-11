"""MODERATION TABLES: mod_warnings(guild_id, user_id, moderator_id, reason, timestamp)."""
MODULE_VERSION = "1.0"
MODULE_ENV_VARS: list[str] = []

from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog

class Moderation(BaseCog):
    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"Kicked {member.mention}.")

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"Banned {member.mention}.")

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        if minutes < 1 or minutes > 40320:
            await interaction.response.send_message("Choose a duration from 1 to 40320 minutes.", ephemeral=True)
            return
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(f"Timed out {member.mention}.")

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await self.db.execute("INSERT INTO mod_warnings(guild_id,user_id,moderator_id,reason,timestamp) VALUES($1,$2,$3,$4,$5)", interaction.guild_id, member.id, interaction.user.id, reason, datetime.now(timezone.utc))
        await interaction.response.send_message(f"Warned {member.mention}: {reason}")

    @app_commands.command(name="warnings", description="View a member's warnings")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        rows = await self.db.fetch("SELECT reason,timestamp FROM mod_warnings WHERE guild_id=$1 AND user_id=$2 ORDER BY timestamp DESC", interaction.guild_id, member.id)
        await interaction.response.send_message("\n".join(f"{r['timestamp']:%Y-%m-%d}: {r['reason']}" for r in rows) or "No warnings found.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
