import asyncio
import secrets
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []


class GiveawayEntryButton(discord.ui.DynamicItem[discord.ui.Button], template=r"giveaway:(?P<bot_id>[0-9a-f-]+):(?P<giveaway_id>\d+)"):
    def __init__(self, item):
        super().__init__(item)

    @classmethod
    async def from_custom_id(cls, interaction, custom_id):
        return cls(discord.ui.Button(label="Enter giveaway", custom_id=custom_id, style=discord.ButtonStyle.success))

    async def callback(self, interaction):
        match = self.match.groupdict()
        inserted = await interaction.client.db.execute(
            "INSERT INTO giveaway_entries(bot_id,giveaway_id,user_id) SELECT $1::uuid,$2,$3 WHERE EXISTS "
            "(SELECT 1 FROM giveaways WHERE bot_id=$1::uuid AND id=$2 AND status='active') ON CONFLICT DO NOTHING",
            match["bot_id"], int(match["giveaway_id"]), interaction.user.id,
        )
        await interaction.response.send_message("You are entered." if inserted == "INSERT 0 1" else "This giveaway is no longer active or you are already entered.", ephemeral=True)


class Giveaways(BaseCog):
    @app_commands.command(name="giveaway", description="Create a giveaway")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(self, interaction: discord.Interaction, prize: str, minutes: app_commands.Range[int, 1, 10080] = 60):
        row = await self.db.fetchrow(
            "INSERT INTO giveaways(bot_id,guild_id,channel_id,host_id,prize,status,ends_at) VALUES($1::uuid,$2,$3,$4,$5,'active',NOW()+($6 * INTERVAL '1 minute')) RETURNING id",
            self.bot.config.bot_id, interaction.guild_id, interaction.channel_id, interaction.user.id, prize, minutes,
        )
        button = discord.ui.Button(label="Enter giveaway", style=discord.ButtonStyle.success, custom_id=f"giveaway:{self.bot.config.bot_id}:{row['id']}")
        await interaction.response.send_message(
            view=panel("Giveaway", f"**#{row['id']}**\nPrize: **{prize}**\nEnds in {minutes} minutes.", button=button)
        )
        message = await interaction.original_response()
        await self.db.execute("UPDATE giveaways SET message_id=$2 WHERE bot_id=$1::uuid AND id=$3", self.bot.config.bot_id, message.id, row["id"])

    @commands.Cog.listener()
    async def on_ready(self):
        if not getattr(self, "_giveaway_loop_started", False):
            self._giveaway_loop_started = True
            self.bot.loop.create_task(self._finish_loop())

    async def _finish_loop(self):
        while not self.bot.is_closed():
            rows = await self.db.fetch(
                "UPDATE giveaways SET status='ended' WHERE bot_id=$1::uuid AND status='active' AND ends_at <= NOW() RETURNING id,channel_id,prize",
                self.bot.config.bot_id,
            )
            for row in rows:
                winner = await self.db.fetchrow(
                    "SELECT user_id FROM giveaway_entries WHERE bot_id=$1::uuid AND giveaway_id=$2 ORDER BY md5(user_id::text || $3) LIMIT 1",
                    self.bot.config.bot_id, row["id"], secrets.token_hex(16),
                )
                channel = self.bot.get_channel(row["channel_id"])
                if channel is None:
                    try:
                        channel = await self.bot.fetch_channel(row["channel_id"])
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        channel = None
                if isinstance(channel, discord.abc.Messageable):
                    mention = f"<@{winner['user_id']}>" if winner else "No eligible entrants"
                    await channel.send(view=panel("Giveaway ended", f"Prize: **{row['prize']}**\nWinner: {mention}"))
            await asyncio.sleep(30)


async def setup(bot):
    bot.add_dynamic_items(GiveawayEntryButton)
    await bot.add_cog(Giveaways(bot))
