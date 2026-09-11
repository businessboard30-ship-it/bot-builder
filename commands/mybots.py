from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

class MyBots(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="mybots", description="List your Bot Builder bots")
    async def mybots(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch("SELECT bot_name, modules_enabled, created_at, last_regenerated_at FROM user_bots WHERE user_id=$1 ORDER BY created_at", interaction.user.id)
        if not rows: return await interaction.response.send_message("You have no bots yet. Run /build to create one.", ephemeral=True)
        embed = discord.Embed(title="Your bots", color=discord.Color.blurple())
        for row in rows:
            created = row["created_at"].strftime("%Y-%m-%d")
            regenerated = row["last_regenerated_at"].strftime("%Y-%m-%d") if row["last_regenerated_at"] else "Never"
            embed.add_field(name=row["bot_name"], value=f"Modules: {', '.join(row['modules_enabled'] or [])}\nCreated: {created}\nLast regenerated: {regenerated}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot): await bot.add_cog(MyBots(bot))
