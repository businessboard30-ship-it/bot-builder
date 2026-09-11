"""LEVELING TABLES: user_levels(guild_id, user_id, xp, level, last_xp_gain)."""
# Cross-module note: leveling and economy may both reward message activity when enabled.
# They intentionally are not auto-integrated; the future wizard should ask the user how to coordinate them.
MODULE_VERSION = "1.0"
MODULE_ENV_VARS: list[str] = []

import random
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog

COOLDOWN = timedelta(seconds=60)

class Leveling(BaseCog):
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not self.db:
            return
        row = await self.db.fetchrow("SELECT * FROM user_levels WHERE guild_id=$1 AND user_id=$2", message.guild.id, message.author.id)
        now = datetime.now(timezone.utc)
        if row and row["last_xp_gain"] and now - row["last_xp_gain"] < COOLDOWN:
            return
        xp = (row["xp"] if row else 0) + random.randint(10, 20)
        old_level = row["level"] if row else 0
        level = int((xp / 100) ** 0.5)
        await self.db.execute("""INSERT INTO user_levels(guild_id,user_id,xp,level,last_xp_gain) VALUES($1,$2,$3,$4,$5) ON CONFLICT(guild_id,user_id) DO UPDATE SET xp=$3,level=$4,last_xp_gain=$5""", message.guild.id, message.author.id, xp, level, now)
        if level > old_level:
            await message.channel.send(f"Congratulations {message.author.mention}, you reached level {level}!")

    @app_commands.command(name="rank", description="Show a member's level and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        row = await self.db.fetchrow("SELECT xp, level FROM user_levels WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, member.id)
        await interaction.response.send_message(f"{member.display_name}: level {row['level'] if row else 0}, {row['xp'] if row else 0} XP")

    @app_commands.command(name="leaderboard", description="Show the server XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        rows = await self.db.fetch("SELECT user_id,xp,level FROM user_levels WHERE guild_id=$1 ORDER BY xp DESC LIMIT 10", interaction.guild_id)
        lines = [f"{i}. <@{r['user_id']}> — level {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows, 1)]
        await interaction.response.send_message("\n".join(lines) or "No XP recorded yet.")

async def setup(bot):
    await bot.add_cog(Leveling(bot))
