"""WELCOME TABLES: welcome_settings(bot_id, guild_id, channel_id, message_template, enabled)."""
MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []

import io
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.wizard_ui import _check_access, _decode, _encode, _id_pattern, _rerender
from modules.welcome_card import render_welcome_card


class WelcomeChannelSelect(discord.ui.DynamicItem[discord.ui.ChannelSelect], template=_id_pattern("welcome-channel")):
    def __init__(self, item: discord.ui.ChannelSelect):
        super().__init__(item)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, custom_id: str):
        return cls(discord.ui.ChannelSelect(custom_id=custom_id, channel_types=[discord.ChannelType.text], min_values=1, max_values=1))

    async def callback(self, interaction: discord.Interaction):
        bot_id, guild_id, invoker_id = _decode(self.match)
        if not await _check_access(interaction, invoker_id): return
        channel_id = self.values[0].id
        await interaction.client.db.execute("UPDATE welcome_settings SET channel_id=$1 WHERE bot_id=$2::uuid AND guild_id=$3", channel_id, bot_id, guild_id)
        await _rerender(interaction, content=f"Welcome channel updated to <#{channel_id}>.", view=self.view)


class Welcome(BaseCog):
    @app_commands.command(name="previewwelcome", description="Preview the welcome card")
    @app_commands.default_permissions(manage_guild=True)
    async def previewwelcome(self, interaction: discord.Interaction):
        image = render_welcome_card(await interaction.user.display_avatar.read(), interaction.user.display_name, interaction.guild.name, interaction.guild.member_count or 0)
        await interaction.response.send_message(file=discord.File(io.BytesIO(image), filename="welcome-preview.png"), ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.db: return
        row = await self.db.fetchrow("SELECT * FROM welcome_settings WHERE bot_id=$1::uuid AND guild_id=$2 AND enabled=TRUE", self.bot.config.bot_id, member.guild.id)
        if row:
            channel = member.guild.get_channel(row["channel_id"])
            if channel:
                text = row["message_template"].format(user=member.mention, server=member.guild.name, membercount=member.guild.member_count)
                image = render_welcome_card(await member.display_avatar.read(), member.display_name, member.guild.name, member.guild.member_count or 0)
                await channel.send(content=text, file=discord.File(io.BytesIO(image), filename='welcome.png'))

    @app_commands.command(name="setwelcome", description="Configure the server welcome message")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, enabled: bool = True):
        await self.db.execute("INSERT INTO welcome_settings(bot_id,guild_id,channel_id,message_template,enabled) VALUES($1::uuid,$2,$3,$4,$5) ON CONFLICT(bot_id,guild_id) DO UPDATE SET channel_id=$3,message_template=$4,enabled=$5", self.bot.config.bot_id, interaction.guild_id, channel.id, message, enabled)
        await interaction.response.send_message("Welcome settings saved.", ephemeral=True)


async def set_welcome_config(db, bot_id: str, guild_id: int, channel_id: int):
    await db.execute("UPDATE welcome_settings SET channel_id=$1 WHERE bot_id=$2::uuid AND guild_id=$3", channel_id, bot_id, guild_id)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
