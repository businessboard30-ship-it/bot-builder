import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []


class Ticket(BaseCog):
    @app_commands.command(name="ticket", description="Create a private support ticket")
    async def ticket(self, interaction: discord.Interaction, subject: str):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("Tickets are only available in a server.", ephemeral=True)
        existing = await self.db.fetchval(
            "SELECT 1 FROM tickets WHERE bot_id=$1::uuid AND guild_id=$2 AND opener_id=$3 AND status='open' LIMIT 1",
            self.bot.config.bot_id, guild.id, interaction.user.id,
        )
        if existing:
            return await interaction.response.send_message("You already have an open ticket.", ephemeral=True)
        staff_role = next((role for role in guild.roles if role.name.casefold() in {"staff", "moderator", "support"}), None)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            overwrites=overwrites,
            topic=subject[:900],
            reason="Support ticket created",
        )
        row = await self.db.fetchrow(
            "INSERT INTO tickets(bot_id,guild_id,opener_id,subject,status,channel_id) VALUES($1::uuid,$2,$3,$4,'open',$5) RETURNING id",
            self.bot.config.bot_id, guild.id, interaction.user.id, subject, channel.id,
        )
        await channel.send(
            view=panel(
                "Support ticket",
                f"{interaction.user.mention} opened ticket **#{row['id']}**: {subject}\nUse `/close_ticket {row['id']}` when resolved.",
            )
        )
        await interaction.response.send_message(f"Ticket opened: {channel.mention}", ephemeral=True)

    @app_commands.command(name="close_ticket", description="Close an open support ticket")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def close_ticket(self, interaction: discord.Interaction, ticket_id: int):
        row = await self.db.fetchrow(
            "UPDATE tickets SET status='closed' WHERE bot_id=$1::uuid AND guild_id=$2 AND id=$3 AND status='open' RETURNING channel_id",
            self.bot.config.bot_id, interaction.guild_id, ticket_id,
        )
        if not row:
            return await interaction.response.send_message("Open ticket not found.", ephemeral=True)
        await interaction.response.send_message(
            view=panel("Ticket closed", f"Ticket **#{ticket_id}** is being archived.") , ephemeral=True
        )
        channel = self.bot.get_channel(row["channel_id"])
        if channel:
            await channel.delete(reason=f"Ticket {ticket_id} closed")


async def setup(bot):
    await bot.add_cog(Ticket(bot))
