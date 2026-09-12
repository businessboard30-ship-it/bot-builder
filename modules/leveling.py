"""LEVELING TABLES: user_levels(bot_id, guild_id, user_id, xp, level, last_xp_gain)."""
MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []

import io
import random
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.wizard_ui import _check_access, _decode, _id_pattern, _rerender
from modules.level_card import render_level_card


class LevelingAnnounceChannelSelect(discord.ui.DynamicItem[discord.ui.ChannelSelect], template=_id_pattern("leveling-channel")):
    def __init__(self, item: discord.ui.ChannelSelect): super().__init__(item)
    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, custom_id: str):
        return cls(discord.ui.ChannelSelect(custom_id=custom_id, channel_types=[discord.ChannelType.text], min_values=1, max_values=1))
    async def callback(self, interaction: discord.Interaction):
        bot_id, guild_id, invoker_id = _decode(self.match)
        if not await _check_access(interaction, invoker_id): return
        channel_id = self.values[0].id
        await interaction.client.db.execute("UPDATE leveling_settings SET announce_channel_id=$1 WHERE bot_id=$2::uuid AND guild_id=$3", channel_id, bot_id, guild_id)
        await _rerender(interaction, content=f"Level announcements will use <#{channel_id}>.", view=self.view)


class Leveling(BaseCog):
    @app_commands.command(name="previewrank", description="Preview the rank card")
    @app_commands.default_permissions(manage_guild=True)
    async def previewrank(self, interaction: discord.Interaction):
        row = await self.db.fetchrow("SELECT xp,level FROM user_levels WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.bot.config.bot_id, interaction.guild_id, interaction.user.id)
        xp = row["xp"] if row else 0
        level = row["level"] if row else 0
        image = render_level_card(await interaction.user.display_avatar.read(), interaction.user.display_name, level, xp % 100, 100)
        await interaction.response.send_message(file=discord.File(io.BytesIO(image), filename="rank-preview.png"), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not self.db: return
        row = await self.db.fetchrow("SELECT * FROM user_levels WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.bot.config.bot_id, message.guild.id, message.author.id)
        now = datetime.now(timezone.utc)
        if row and row["last_xp_gain"] and now - row["last_xp_gain"] < timedelta(seconds=60): return
        xp = (row["xp"] if row else 0) + random.randint(10, 20)
        level = int((xp / 100) ** 0.5)
        await self.db.execute("INSERT INTO user_levels(bot_id,guild_id,user_id,xp,level,last_xp_gain) VALUES($1::uuid,$2,$3,$4,$5,$6) ON CONFLICT(bot_id,guild_id,user_id) DO UPDATE SET xp=$4,level=$5,last_xp_gain=$6", self.bot.config.bot_id, message.guild.id, message.author.id, xp, level, now)

    @app_commands.command(name="rank", description="Show a member's level and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        row = await self.db.fetchrow("SELECT xp,level FROM user_levels WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.bot.config.bot_id, interaction.guild_id, member.id)
        xp = row['xp'] if row else 0
        level = row['level'] if row else 0
        image = render_level_card(await member.display_avatar.read(), member.display_name, level, xp % 100, 100)
        await interaction.response.send_message(file=discord.File(io.BytesIO(image), filename='rank.png'))

async def set_leveling_config(db, bot_id: str, guild_id: int, announce_channel_id: int):
    await db.execute("INSERT INTO leveling_settings(bot_id,guild_id,announce_channel_id) VALUES($1::uuid,$2,$3) ON CONFLICT(bot_id,guild_id) DO UPDATE SET announce_channel_id=$3", bot_id, guild_id, announce_channel_id)

async def setup(bot): await bot.add_cog(Leveling(bot))
