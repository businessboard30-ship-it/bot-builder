import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []


class Starboard(BaseCog):
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⭐" or not payload.guild_id or payload.user_id == self.bot.user.id:
            return
        settings = await self.db.fetchrow(
            "SELECT channel_id, threshold FROM starboard_settings WHERE bot_id=$1::uuid AND guild_id=$2",
            self.bot.config.bot_id, payload.guild_id,
        )
        if not settings or payload.channel_id == settings["channel_id"]:
            return
        source_channel = self.bot.get_channel(payload.channel_id)
        target_channel = self.bot.get_channel(settings["channel_id"])
        if not isinstance(source_channel, discord.TextChannel) or not isinstance(target_channel, discord.TextChannel):
            return
        source = await source_channel.fetch_message(payload.message_id)
        reaction = next((item for item in source.reactions if str(item.emoji) == "⭐"), None)
        if not reaction or reaction.count < settings["threshold"]:
            return
        inserted = await self.db.fetchrow(
            "INSERT INTO starboard_posts(bot_id,guild_id,original_message_id,starboard_message_id) "
            "VALUES($1::uuid,$2,$3,NULL) ON CONFLICT DO NOTHING RETURNING original_message_id",
            self.bot.config.bot_id, payload.guild_id, source.id,
        )
        if not inserted:
            return
        repost = await target_channel.send(
            view=panel(
                "Starboard",
                f"⭐ **{reaction.count}** {source.author.mention} in {source.channel.mention}\n{source.content[:1800]}",
            )
        )
        await self.db.execute(
            "UPDATE starboard_posts SET starboard_message_id=$4 WHERE bot_id=$1::uuid AND guild_id=$2 AND original_message_id=$3",
            self.bot.config.bot_id, payload.guild_id, source.id, repost.id,
        )

    @app_commands.command(name="starboard", description="Configure the starboard channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def starboard(self, interaction: discord.Interaction, channel_id: str, threshold: app_commands.Range[int, 1, 100] = 3):
        await self.db.execute(
            "INSERT INTO starboard_settings(bot_id,guild_id,channel_id,threshold) VALUES($1::uuid,$2,$3,$4) "
            "ON CONFLICT(bot_id,guild_id) DO UPDATE SET channel_id=$3, threshold=$4",
            self.bot.config.bot_id, interaction.guild_id, int(channel_id), threshold,
        )
        await interaction.response.send_message("Starboard saved.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Starboard(bot))
