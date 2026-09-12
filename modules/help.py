from discord import app_commands
from discord.ext import commands
from core.command_reference import render_help
from core.base_cog import BaseCog

MODULE_VERSION = "1.0"
MODULE_ENV_VARS: list[str] = []

class Help(BaseCog):
    @app_commands.command(name="help", description="Show the commands enabled for this bot")
    async def help(self, interaction):
        enabled = getattr(self.bot, "enabled_module_names", [])
        await interaction.response.send_message(render_help(enabled), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))
