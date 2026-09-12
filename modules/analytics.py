import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []


class Analytics(BaseCog):
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild and not message.author.bot:
            await self.db.execute("INSERT INTO analytics_events(bot_id,guild_id,event_type) VALUES($1::uuid,$2,$3)", self.bot.config.bot_id, message.guild.id, "message")

    @app_commands.command(name="analytics", description="Show bot analytics")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def analytics(self, interaction: discord.Interaction, days: app_commands.Range[int, 1, 90] = 7):
        rows = await self.db.fetch(
            "SELECT event_type, COUNT(*) AS count FROM analytics_events WHERE bot_id=$1::uuid AND guild_id=$2 AND created_at >= NOW() - ($3 * INTERVAL '1 day') GROUP BY event_type ORDER BY count DESC",
            self.bot.config.bot_id, interaction.guild_id, days,
        )
        lines = [f"{row['event_type']}: {row['count']}" for row in rows] or ["No events recorded."]
        await interaction.response.send_message(view=panel(f"Analytics · {days} days", "\n".join(lines)), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Analytics(bot))
