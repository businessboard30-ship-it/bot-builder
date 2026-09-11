from discord.ext import commands


class BaseCog(commands.Cog):
    """Shared base for feature modules; business logic belongs in each cog."""

    def __init__(self, bot):
        self.bot = bot

    @property
    def db(self):
        return self.bot.db

    @property
    def config(self):
        return self.bot.config
