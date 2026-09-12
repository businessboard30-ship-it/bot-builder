import asyncio
import hashlib
import re
import urllib.request
import discord
from discord.ext import commands
from discord import app_commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []


class Autopost(BaseCog):
    @commands.Cog.listener()
    async def on_ready(self):
        if not getattr(self, "_autopost_started", False):
            self._autopost_started = True
            self.bot.loop.create_task(self._poll_feeds())

    async def _poll_feeds(self):
        while not self.bot.is_closed():
            rows = await self.db.fetch("SELECT id,channel_id,feed_url,last_item_key,attempts FROM autopost_feeds WHERE bot_id=$1::uuid AND enabled=TRUE", self.bot.config.bot_id)
            for row in rows:
                try:
                    request = urllib.request.Request(row["feed_url"], headers={"User-Agent": "BotBuilder/1.0"})
                    body = await asyncio.to_thread(urllib.request.urlopen, request, timeout=10)
                    xml = await asyncio.to_thread(body.read)
                    # Minimal mode intentionally posts only the first unseen item per poll; newer backlog items wait for a later feed update.
                    item = re.search(rb"<(?:item|entry)>.*?<(?:guid|id|link)[^>]*>(.*?)</(?:guid|id|link)>.*?<title>(.*?)</title>", xml, re.S)
                    if not item:
                        continue
                    key = hashlib.sha256(item.group(1)).hexdigest()
                    if key == row["last_item_key"]:
                        continue
                    channel = self.bot.get_channel(row["channel_id"])
                    if not isinstance(channel, discord.abc.Messageable):
                        raise RuntimeError("Autopost channel is unavailable")
                    await channel.send(view=panel("New feed item", item.group(2).decode(errors="ignore")[:1900]))
                    await self.db.execute("UPDATE autopost_feeds SET last_item_key=$2, attempts=0, last_error=NULL WHERE bot_id=$1::uuid AND id=$3", self.bot.config.bot_id, key, row["id"])
                except Exception as error:
                    attempts = row["attempts"] + 1
                    await self.db.execute("UPDATE autopost_feeds SET attempts=$2, last_error=$3 WHERE bot_id=$1::uuid AND id=$4", self.bot.config.bot_id, attempts, str(error)[:500], row["id"])
            await asyncio.sleep(300)

    @app_commands.command(name="autopost", description="Configure an autopost feed")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def autopost(self, interaction, feed_url: str, channel_id: str):
        await self.db.execute("INSERT INTO autopost_feeds(bot_id,guild_id,feed_url,channel_id,enabled) VALUES($1::uuid,$2,$3,$4,TRUE)", self.bot.config.bot_id, interaction.guild_id, feed_url, int(channel_id))
        await interaction.response.send_message("Autopost feed saved.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Autopost(bot))
