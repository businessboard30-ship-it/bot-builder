from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

MODULES = {
    "leveling": "Leveling", "welcome": "Welcome", "moderation": "Moderation", "economy": "Economy",
    "reaction_roles": "Reaction roles", "starboard": "Starboard", "ticket": "Tickets", "giveaways": "Giveaways",
    "schedule": "Schedule", "analytics": "Analytics", "voice_xp": "Voice XP", "autopost": "Autopost", "automod": "Automod",
}


class ManageBotButton(discord.ui.DynamicItem[discord.ui.Button], template=r"manage:([0-9a-f-]{36}):([0-9]+)"):
    def __init__(self, item: discord.ui.Button):
        super().__init__(item)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, custom_id: str):
        return cls(discord.ui.Button(label="Manage", style=discord.ButtonStyle.primary, custom_id=custom_id))

    async def callback(self, interaction: discord.Interaction):
        bot_id, user_id = self.match.groups()
        if str(interaction.user.id) != user_id:
            return await interaction.response.send_message("Only the bot owner can manage this bot.", ephemeral=True)
        row = await interaction.client.db.fetchrow(
            "SELECT bot_name, modules_enabled FROM user_bots WHERE bot_id=$1::uuid AND user_id=$2",
            bot_id, user_id,
        )
        if not row:
            return await interaction.response.send_message("That bot is no longer available.", ephemeral=True)
        await interaction.response.edit_message(
            content=f"Manage **{row['bot_name']}**. Toggle modules below; changes apply on the supervisor's next poll.",
            embed=None,
            view=ModuleManagementView(interaction.client, bot_id, int(user_id), set(row["modules_enabled"] or [])),
        )


class ModuleToggle(discord.ui.DynamicItem[discord.ui.Button], template=r"toggle:([0-9a-f-]{36}):([0-9]+):([a-z_]+)"):
    def __init__(self, item: discord.ui.Button):
        super().__init__(item)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, custom_id: str):
        return cls(discord.ui.Button(label="Toggle", style=discord.ButtonStyle.secondary, custom_id=custom_id))

    async def callback(self, interaction: discord.Interaction):
        bot_id, user_id, module = self.match.groups()
        if str(interaction.user.id) != user_id:
            return await interaction.response.send_message("Only the bot owner can manage this bot.", ephemeral=True)
        row = await interaction.client.db.fetchrow(
            "SELECT modules_enabled FROM user_bots WHERE bot_id=$1::uuid AND user_id=$2",
            bot_id, user_id,
        )
        if not row:
            return await interaction.response.send_message("That bot is no longer available.", ephemeral=True)
        enabled = set(row["modules_enabled"] or [])
        enabled.symmetric_difference_update({module})
        await interaction.client.db.execute(
            "UPDATE user_bots SET modules_enabled=$1::jsonb, last_regenerated_at=NOW() WHERE bot_id=$2::uuid AND user_id=$3",
            list(enabled), bot_id, user_id,
        )
        await interaction.response.edit_message(
            content=f"Manage bot. Updated **{MODULES[module]}**. The supervisor will restart it with the new module set.",
            view=ModuleManagementView(interaction.client, bot_id, int(user_id), enabled),
        )


class ModuleManagementView(discord.ui.View):
    def __init__(self, bot, bot_id: str, user_id: int, enabled: set[str]):
        super().__init__(timeout=None)
        for key, label in MODULES.items():
            style = discord.ButtonStyle.success if key in enabled else discord.ButtonStyle.secondary
            self.add_item(discord.ui.Button(label=("On: " if key in enabled else "Off: ") + label, style=style, custom_id=f"toggle:{bot_id}:{user_id}:{key}"))


class MyBots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mybots", description="List and manage your Bot Builder bots")
    async def mybots(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch(
            "SELECT bot_id::text, bot_name, modules_enabled, created_at, last_regenerated_at FROM user_bots WHERE user_id=$1 ORDER BY created_at",
            str(interaction.user.id),
        )
        if not rows:
            return await interaction.response.send_message("You have no bots yet. Run /build to create one.", ephemeral=True)
        embed = discord.Embed(title="Your bots", color=discord.Color.blurple())
        view = discord.ui.View(timeout=None)
        for row in rows:
            created = row["created_at"].strftime("%Y-%m-%d")
            regenerated = row["last_regenerated_at"].strftime("%Y-%m-%d") if row["last_regenerated_at"] else "Never"
            embed.add_field(name=row["bot_name"], value=f"Modules: {', '.join(row['modules_enabled'] or [])}\nCreated: {created}\nLast regenerated: {regenerated}", inline=False)
            view.add_item(discord.ui.Button(label=f"Manage {row['bot_name']}", style=discord.ButtonStyle.primary, custom_id=f"manage:{row['bot_id']}:{interaction.user.id}"))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    bot.add_dynamic_items(ManageBotButton, ModuleToggle)
    await bot.add_cog(MyBots(bot))


MODULE_REGISTRY = tuple(MODULES)
