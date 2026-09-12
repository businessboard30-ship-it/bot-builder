from __future__ import annotations

import json
import logging
import re
from typing import Any

import discord
from discord.ui import Button, Modal, Select, TextInput, View

from core.token_encryption import encrypt_token, decrypt_token
from wizard.session_store import complete_session, get_active_session, update_session

log = logging.getLogger(__name__)
MODULES = {"leveling": "Leveling", "welcome": "Welcome", "moderation": "Moderation", "economy": "Economy", "reaction_roles": "Reaction roles", "starboard": "Starboard", "ticket": "Tickets", "giveaways": "Giveaways", "schedule": "Schedule", "analytics": "Analytics", "voice_xp": "Voice XP", "autopost": "Autopost", "automod": "Automod"}
THEMES = ("Minimal", "Neon", "Corporate", "Pastel")
TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]{40,120}$")


def data(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("answers", {})
    return value if isinstance(value, dict) else json.loads(value)


async def session_or_error(interaction: discord.Interaction, bot):
    row = await get_active_session(bot.db, interaction.user.id)
    if not row:
        await interaction.response.send_message("This build session expired. Run /build again.", ephemeral=True)
        return None, None
    return row, data(row)


class ModuleView(View):
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=None); self.bot, self.user_id = bot, user_id
        for key, label in MODULES.items(): self.add_item(ModuleButton(bot, user_id, key, label))
        self.add_item(ContinueButton(bot, user_id))


class ModuleButton(Button):
    def __init__(self, bot, user_id, key, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"build:{user_id}:module:{key}")
        self.bot, self.user_id, self.key = bot, user_id, key
    async def callback(self, interaction):
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        selected = values.setdefault("modules", [])
        if self.key in selected: selected.remove(self.key)
        else: selected.append(self.key)
        await update_session(self.bot.db, self.user_id, 2, values)
        await interaction.response.edit_message(content=f"**Step 2 — Modules**\nSelected: {', '.join(selected) or 'none'}", view=ModuleView(self.bot, self.user_id))


class ContinueButton(Button):
    def __init__(self, bot, user_id):
        super().__init__(label="Continue", style=discord.ButtonStyle.green, custom_id=f"build:{user_id}:modules-done")
        self.bot, self.user_id = bot, user_id
    async def callback(self, interaction):
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        if not values.get("modules"): return await interaction.response.send_message("Select at least one module.", ephemeral=True)
        await update_session(self.bot.db, self.user_id, 3, values)
        await interaction.response.send_modal(BotDetailsModal(self.bot, self.user_id))


class BotDetailsModal(Modal, title="Bot details"):
    bot_name = TextInput(label="Bot name", min_length=1, max_length=80)
    currency = TextInput(label="Currency name (Economy only)", default="coins", max_length=30, required=False)
    def __init__(self, bot, user_id): super().__init__(); self.bot, self.user_id = bot, user_id
    async def on_submit(self, interaction):
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        values.update(bot_name=str(self.bot_name.value), currency_name=str(self.currency.value or "coins"))
        await update_session(self.bot.db, self.user_id, 4, values)
        await interaction.response.edit_message(content="**Step 4 — Choose a theme**\nThe preview updates in this message.", embed=theme_embed(values), view=ThemeView(self.bot, self.user_id))


def theme_embed(values):
    theme = values.get("theme", "Minimal")
    return discord.Embed(title=values.get("bot_name", "Your bot"), description=f"Theme preset: **{theme}**\nModules: {', '.join(values.get('modules', []))}", color=discord.Color.blurple())


class ThemeView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None); self.bot, self.user_id = bot, user_id
        for theme in THEMES: self.add_item(ThemeButton(bot, user_id, theme))
        self.add_item(ThemeContinue(bot, user_id))


class ThemeButton(Button):
    def __init__(self, bot, user_id, theme):
        super().__init__(label=theme, custom_id=f"build:{user_id}:theme:{theme.lower()}")
        self.bot, self.user_id, self.theme = bot, user_id, theme
    async def callback(self, interaction):
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        values["theme"] = self.theme; await update_session(self.bot.db, self.user_id, 4, values)
        await interaction.response.edit_message(embed=theme_embed(values), view=ThemeView(self.bot, self.user_id))


class ThemeContinue(Button):
    def __init__(self, bot, user_id): super().__init__(label="Continue", style=discord.ButtonStyle.green, custom_id=f"build:{user_id}:theme-done"); self.bot, self.user_id = bot, user_id
    async def callback(self, interaction): await interaction.response.send_modal(SupportServerModal(self.bot, self.user_id))


class SupportServerModal(Modal, title="Support server"):
    support_url = TextInput(label="Your support server invite URL (optional)", required=False, max_length=200, placeholder="https://discord.gg/your-server")
    def __init__(self, bot, user_id): super().__init__(); self.bot, self.user_id = bot, user_id
    async def on_submit(self, interaction):
        value = str(self.support_url.value or "").strip()
        if value and not re.fullmatch(r"https://(discord\.gg|discord\.com/invite)/[A-Za-z0-9-]+", value):
            return await interaction.response.send_message("Use a Discord invite URL or leave it blank.", ephemeral=True)
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        values["support_server_url"] = value or None
        await update_session(self.bot.db, self.user_id, 5, values)
        await interaction.response.edit_message(content="**Step 6 — Token setup**\nEnable Privileged Gateway Intents in your own Developer Portal first, then enter the token here.", view=TokenView(self.bot, self.user_id))


class TokenView(View):
    def __init__(self, bot, user_id): super().__init__(timeout=None); self.add_item(TokenButton(bot, user_id))
class TokenButton(Button):
    def __init__(self, bot, user_id): super().__init__(label="Enter token", style=discord.ButtonStyle.primary, custom_id=f"build:{user_id}:token"); self.bot, self.user_id = bot, user_id
    async def callback(self, interaction): await interaction.response.send_modal(TokenModal(self.bot, self.user_id))
class TokenModal(Modal, title="Discord bot token"):
    token = TextInput(label="Token", style=discord.TextStyle.paragraph, min_length=40, max_length=120)
    def __init__(self, bot, user_id): super().__init__(); self.bot, self.user_id = bot, user_id
    async def on_submit(self, interaction):
        if not TOKEN_RE.fullmatch(str(self.token.value)): return await interaction.response.send_message("That does not look like a Discord token.", ephemeral=True)
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        values["encrypted_token"] = encrypt_token(str(self.token.value), self.bot.config.encryption_key)
        await update_session(self.bot.db, self.user_id, 6, values)
        await interaction.response.edit_message(content="**Step 6 — Permissions**\nChoose the invite permission preset.", view=PermissionView(self.bot, self.user_id))


class PermissionView(View):
    def __init__(self, bot, user_id): super().__init__(timeout=None); self.add_item(PermissionButton(bot, user_id, "8", "Administrator")); self.add_item(PermissionButton(bot, user_id, "0", "Advanced permissions"))
class PermissionButton(Button):
    def __init__(self, bot, user_id, permissions, label): super().__init__(label=label, custom_id=f"build:{user_id}:permissions:{permissions}"); self.bot, self.user_id, self.permissions = bot, user_id, permissions
    async def callback(self, interaction):
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        values["permissions"] = self.permissions
        token = decrypt_token(values["encrypted_token"], self.bot.config.encryption_key)
        application_id = token.split(".", 1)[0]
        values["bot_invite_url"] = f"https://discord.com/oauth2/authorize?client_id={application_id}&scope=bot%20applications.commands&permissions={self.permissions}"
        await update_session(self.bot.db, self.user_id, 7, values)
        invite = values["bot_invite_url"]
        support = values.get("support_server_url") or "Not configured"
        await interaction.response.edit_message(content=f"**Bot invite link** (adds this bot to a server):\n{invite}\n\n**Support server** (where your users get help):\n{support}\n\nReview your setup, then launch.", view=LaunchView(self.bot, self.user_id))


class LaunchView(View):
    def __init__(self, bot, user_id): super().__init__(timeout=None); self.add_item(LaunchButton(bot, user_id))
class LaunchButton(Button):
    def __init__(self, bot, user_id): super().__init__(label="Launch", style=discord.ButtonStyle.green, custom_id=f"build:{user_id}:launch"); self.bot, self.user_id = bot, user_id
    async def callback(self, interaction):
        row, values = await session_or_error(interaction, self.bot)
        if values is None: return
        await self.bot.db.execute("INSERT INTO user_bots(user_id, bot_name, modules_enabled, encrypted_token, currency_name, prefix, support_server_url, status) VALUES($1,$2,$3::jsonb,$4,$5,$6,$7,'active')", str(self.user_id), values.get("bot_name", "Discord bot"), json.dumps(values.get("modules", [])), values["encrypted_token"], values.get("currency_name", "coins"), "!", values.get("support_server_url"))
        await complete_session(self.bot.db, self.user_id)
        await interaction.response.edit_message(content="Connecting...\n\nLaunch accepted. This message will update to Online after the supervisor heartbeat is received.", view=None)


async def render(bot, user_id, row): return "**Step 1 — Bot Builder**\nChoose your modules and configure a bot entirely inside Discord.", ModuleView(bot, user_id)
