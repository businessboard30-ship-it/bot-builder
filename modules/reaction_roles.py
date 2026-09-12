import discord
from discord import app_commands
from discord.ext import commands
from core.base_cog import BaseCog
from core.components_v2 import panel

MODULE_VERSION = "1.1"
MODULE_ENV_VARS: list[str] = []


class ReactionRoleButton(discord.ui.DynamicItem[discord.ui.Button], template=r"rr:(?P<bot_id>[0-9a-f-]+):(?P<guild_id>\d+):(?P<message_id>\d+):(?P<emoji>[^:]+)"):
    def __init__(self, item):
        super().__init__(item)

    @classmethod
    async def from_custom_id(cls, interaction, custom_id):
        return cls(discord.ui.Button(custom_id=custom_id, label="Toggle role", style=discord.ButtonStyle.secondary))

    async def callback(self, interaction):
        match = self.match.groupdict()
        row = await interaction.client.db.fetchrow("SELECT role_id FROM reaction_roles WHERE bot_id=$1::uuid AND guild_id=$2 AND message_id=$3 AND emoji=$4", match["bot_id"], int(match["guild_id"]), int(match["message_id"]), match["emoji"])
        role = interaction.guild.get_role(row["role_id"]) if row else None
        if not role:
            return await interaction.response.send_message("That role is no longer available.", ephemeral=True)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            result = "removed"
        else:
            await interaction.user.add_roles(role)
            result = "added"
        await interaction.response.send_message(f"Role {result}.", ephemeral=True)


class ReactionRoles(BaseCog):
    @app_commands.command(name="reactionrole", description="Create a reaction-role panel")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def reactionrole(self, interaction: discord.Interaction, message_id: str, emoji: str, role: str):
        message = await interaction.channel.fetch_message(int(message_id))
        role_object = interaction.guild.get_role(int(role))
        if not role_object:
            return await interaction.response.send_message("Role not found.", ephemeral=True)
        await self.db.execute("INSERT INTO reaction_roles(bot_id,guild_id,message_id,emoji,role_id) VALUES($1::uuid,$2,$3,$4,$5) ON CONFLICT(bot_id,guild_id,message_id,emoji) DO UPDATE SET role_id=$5", self.bot.config.bot_id, interaction.guild_id, message.id, emoji, role_object.id)
        button = discord.ui.Button(label=f"Get {emoji}", custom_id=f"rr:{self.bot.config.bot_id}:{interaction.guild_id}:{message.id}:{emoji}", style=discord.ButtonStyle.secondary)
        await message.edit(view=panel("Reaction role", f"Toggle **{emoji}** to receive the configured role.", button=button))
        await interaction.response.send_message("Reaction-role panel saved.", ephemeral=True)

    def _panel_view(self, guild_id: int, message_id: int, emoji: str):
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label=f"Get {emoji}", custom_id=f"rr:{self.bot.config.bot_id}:{guild_id}:{message_id}:{emoji}", style=discord.ButtonStyle.secondary))
        return view


async def setup(bot):
    bot.add_dynamic_items(ReactionRoleButton)
    await bot.add_cog(ReactionRoles(bot))
