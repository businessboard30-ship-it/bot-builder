import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []
MAX_ATTEMPTS = 4


class Schedule(BaseCog):
    @app_commands.command(name="schedule", description="Schedule a message")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def schedule(self, interaction: discord.Interaction, channel_id: str, message: str, minutes: app_commands.Range[int, 1, 525600] = 60):
        await self.db.execute(
            "INSERT INTO scheduled_messages(bot_id,guild_id,channel_id,message,status,run_at) VALUES($1::uuid,$2,$3,$4,'pending',NOW()+($5 * INTERVAL '1 minute'))",
            self.bot.config.bot_id, interaction.guild_id, int(channel_id), message, minutes,
        )
        await interaction.response.send_message(f"Message scheduled for {minutes} minutes from now.", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        if not getattr(self, "_schedule_loop_started", False):
            self._schedule_loop_started = True
            self.bot.loop.create_task(self._dispatch_loop())

    async def _dispatch_loop(self):
        while not self.bot.is_closed():
            rows = await self.db.fetch(
                "SELECT id,channel_id,message,attempts FROM scheduled_messages WHERE bot_id=$1::uuid AND status='pending' AND run_at <= NOW() FOR UPDATE SKIP LOCKED",
                self.bot.config.bot_id,
            )
            for row in rows:
                channel = self.bot.get_channel(row["channel_id"])
                if channel is None:
                    try:
                        channel = await self.bot.fetch_channel(row["channel_id"])
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        channel = None
                try:
                    if not isinstance(channel, discord.abc.Messageable):
                        raise RuntimeError("Scheduled channel is unavailable")
                    await channel.send(view=panel("Scheduled message", row["message"]))
                    await self.db.execute("UPDATE scheduled_messages SET status='sent' WHERE bot_id=$1::uuid AND id=$2", self.bot.config.bot_id, row["id"])
                except (discord.DiscordException, RuntimeError) as error:
                    attempts = row["attempts"] + 1
                    await self.db.execute(
                        "UPDATE scheduled_messages SET attempts=$3, status=$4, run_at=CASE WHEN $4='pending' THEN NOW() + ($5 * INTERVAL '1 second') ELSE run_at END, last_error=$6 WHERE bot_id=$1::uuid AND id=$2",
                        self.bot.config.bot_id, row["id"], attempts, "pending" if attempts < MAX_ATTEMPTS else "failed", min(300, 15 * (2 ** (attempts - 1))), str(error)[:500],
                    )
            await asyncio.sleep(30)


async def setup(bot):
    await bot.add_cog(Schedule(bot))
