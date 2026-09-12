import time
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []


class VoiceXp(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        # In-progress sessions are intentionally memory-only; a restart loses only partial-session XP.
        self.sessions: dict[tuple[int, int], float] = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or before.channel == after.channel:
            return
        key = (member.guild.id, member.id)
        if before.channel and key in self.sessions:
            minutes = max(1, int((time.monotonic() - self.sessions.pop(key)) / 60))
            await self.db.execute("INSERT INTO voice_xp(bot_id,guild_id,user_id,xp) VALUES($1::uuid,$2,$3,$4) ON CONFLICT(bot_id,guild_id,user_id) DO UPDATE SET xp=voice_xp.xp+EXCLUDED.xp", self.bot.config.bot_id, member.guild.id, member.id, minutes)
        if after.channel:
            self.sessions[key] = time.monotonic()

    @app_commands.command(name="voicexp", description="Show voice XP")
    async def voicexp(self, interaction):
        row = await self.db.fetchrow("SELECT xp FROM voice_xp WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.bot.config.bot_id, interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(view=panel("Voice XP", f"Current XP: {row['xp'] if row else 0}"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(VoiceXp(bot))
