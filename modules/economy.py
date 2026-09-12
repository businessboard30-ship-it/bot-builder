"""ECONOMY TABLES: user_economy(guild_id, user_id, balance, last_daily_claim)."""
# Cross-module note: economy and leveling may both reward message activity when enabled.
# They intentionally are not auto-integrated; the future wizard should ask the user how to coordinate them.
MODULE_VERSION = "1.0"
MODULE_ENV_VARS = ["CURRENCY_NAME"]

from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog

class Economy(BaseCog):
    @property
    def currency_name(self):
        return getattr(self.config, "currency_name", "coins")

    async def ensure(self, guild_id, user_id):
        await self.db.execute("INSERT INTO user_economy(bot_id,guild_id,user_id,balance) VALUES($1::uuid,$2,$3,0) ON CONFLICT DO NOTHING", self.config.bot_id, guild_id, user_id)

    @app_commands.command(name="balance", description="Show a member's balance")
    async def balance(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        await self.ensure(interaction.guild_id, member.id)
        row = await self.db.fetchrow("SELECT balance FROM user_economy WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.config.bot_id, interaction.guild_id, member.id)
        await interaction.response.send_message(f"{member.display_name} has {row['balance']} {self.currency_name}.")

    @app_commands.command(name="daily", description="Claim daily currency")
    async def daily(self, interaction: discord.Interaction):
        await self.ensure(interaction.guild_id, interaction.user.id)
        row = await self.db.fetchrow("SELECT last_daily_claim FROM user_economy WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.config.bot_id, interaction.guild_id, interaction.user.id)
        now = datetime.now(timezone.utc)
        if row["last_daily_claim"] and now - row["last_daily_claim"] < timedelta(days=1):
            await interaction.response.send_message("You already claimed your daily reward.", ephemeral=True)
            return
        await self.db.execute("UPDATE user_economy SET balance=balance+100,last_daily_claim=$4 WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.config.bot_id, interaction.guild_id, interaction.user.id, now)
        await interaction.response.send_message(f"You received 100 {self.currency_name}.")

    @app_commands.command(name="pay", description="Pay another member")
    async def pay(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0 or member.id == interaction.user.id:
            await interaction.response.send_message("Enter a positive amount and another member.", ephemeral=True)
            return
        await self.ensure(interaction.guild_id, interaction.user.id)
        await self.ensure(interaction.guild_id, member.id)
        result = await self.db.fetchrow("UPDATE user_economy SET balance=balance-$4 WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3 AND balance >= $4 RETURNING balance", self.config.bot_id, interaction.guild_id, interaction.user.id, amount)
        if not result:
            await interaction.response.send_message("You do not have enough currency.", ephemeral=True)
            return
        await self.db.execute("UPDATE user_economy SET balance=balance+$4 WHERE bot_id=$1::uuid AND guild_id=$2 AND user_id=$3", self.config.bot_id, interaction.guild_id, member.id, amount)
        await interaction.response.send_message(f"Paid {member.mention} {amount} {self.currency_name}.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
