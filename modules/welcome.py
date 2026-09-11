"""WELCOME TABLES: welcome_settings(guild_id, channel_id, message_template, enabled)."""
MODULE_VERSION = "1.0"
MODULE_ENV_VARS: list[str] = []

import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog

class Welcome(BaseCog):
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        row = await self.db.fetchrow("SELECT * FROM welcome_settings WHERE guild_id=$1 AND enabled=TRUE", member.guild.id)
        if not row:
            return
        channel = member.guild.get_channel(row["channel_id"])
        if channel:
            text = row["message_template"].format(user=member.mention, server=member.guild.name, membercount=member.guild.member_count)
            await channel.send(embed=discord.Embed(description=text, color=discord.Color.blurple()))

    @app_commands.command(name="setwelcome", description="Configure the server welcome message")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, enabled: bool = True):
        await self.db.execute("""INSERT INTO welcome_settings(guild_id,channel_id,message_template,enabled) VALUES($1,$2,$3,$4) ON CONFLICT(guild_id) DO UPDATE SET channel_id=$2,message_template=$3,enabled=$4""", interaction.guild_id, channel.id, message, enabled)
        await interaction.response.send_message("Welcome settings saved.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
