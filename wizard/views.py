from __future__ import annotations

import importlib
import io
import json
import logging
import re
from typing import Any

log = logging.getLogger(__name__)

import discord
from discord.ui import Button, Modal, TextInput, View

from core.generator import generate_package, module_schema_hash
from core.token_encryption import decrypt_token, encrypt_token
from wizard.session_store import complete_session, get_active_session, update_session

MODULES = {
    "leveling": "XP and rank commands",
    "welcome": "Welcome messages for new members",
    "moderation": "Warnings and moderation tools",
    "economy": "Balances and daily rewards",
}
TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-.]{40,120}$")


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return cleaned.lower() or "discord-bot"


def answers(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("answers", {})
    return value if isinstance(value, dict) else json.loads(value)


class WizardView(View):
    def __init__(self, bot, user_id: int, step: int = 1):
        super().__init__(timeout=None)
        self.bot, self.user_id, self.step = bot, user_id, step
        if step == 1:
            self.add_item(ActionButton("Start", f"build:{user_id}:start", self.advance_start))
        elif step == 3:
            for key, label in MODULES.items():
                self.add_item(ActionButton(label, f"build:{user_id}:module:{key}", self.toggle_module))
            self.add_item(ActionButton("Continue", f"build:{user_id}:modules-done", self.modules_done, discord.ButtonStyle.green))
        elif step == 5:
            self.add_item(ActionButton("Enter currency name", f"build:{user_id}:currency", self.currency_modal))
        elif step == 6:
            self.add_item(ActionButton("I have the token", f"build:{user_id}:token", self.token_modal))
        elif step == 7:
            self.add_item(ActionButton("Enter the token", f"build:{user_id}:token", self.token_modal))
        elif step == 8:
            self.add_item(ActionButton("Railway", f"build:{user_id}:host:railway", self.host))
            self.add_item(ActionButton("Fly.io", f"build:{user_id}:host:fly", self.host))
        elif step == 9:
            self.add_item(ActionButton("Confirm & Generate", f"build:{user_id}:confirm", self.confirm, discord.ButtonStyle.green))

    async def row(self):
        return await get_active_session(self.bot.db, self.user_id)

    async def edit(self, interaction: discord.Interaction, content: str, step: int, answers_: dict[str, Any], view=None):
        await update_session(self.bot.db, self.user_id, step, answers_)
        await interaction.response.edit_message(content=content, view=view or WizardView(self.bot, self.user_id, step))

    async def advance_start(self, interaction):
        await interaction.response.send_modal(NameModal(self.bot, self.user_id))

    async def toggle_module(self, interaction, key: str):
        row = await self.row()
        if not row: return await interaction.response.send_message("This wizard session expired. Run /build again.", ephemeral=True)
        data = answers(row); selected = data.setdefault("modules", [])
        if key in selected: selected.remove(key)
        else: selected.append(key)
        label = ", ".join(selected) or "none yet"
        await interaction.response.edit_message(content=f"**Step 3 of 9 — Choose modules**\nSelected: {label}\nToggle modules, then press Continue.", view=WizardView(self.bot, self.user_id, 3))
        await update_session(self.bot.db, self.user_id, 3, data)

    async def modules_done(self, interaction):
        row = await self.row(); data = answers(row)
        if not data.get("modules"): return await interaction.response.send_message("Select at least one module.", ephemeral=True)
        if "leveling" in data["modules"] and "economy" in data["modules"]:
            await self.edit(interaction, "**Step 4 of 9 — Reward coordination**\nLeveling and Economy can both reward activity. Choose how to coordinate them.", 4, data, RewardView(self.bot, self.user_id))
        else: await interaction.response.send_modal(PrefixModal(self.bot, self.user_id))

    async def token_modal(self, interaction): await interaction.response.send_modal(TokenModal(self.bot, self.user_id))

    async def currency_modal(self, interaction): await interaction.response.send_modal(CurrencyModal(self.bot, self.user_id))

    async def host(self, interaction, host: str):
        row = await self.row(); data = answers(row); data["host"] = host
        await self.edit(interaction, "**Step 9 of 9 — Review**\n" + summary(data), 9, data)

    async def confirm(self, interaction):
        row = await self.row()
        if not row:
            return await interaction.response.send_message("This wizard session expired. Run /build again.", ephemeral=True)
        data = answers(row)
        encrypted_token = data.get("encrypted_token")
        encryption_key = getattr(self.bot.config, "encryption_key", None)
        if not encrypted_token or not encryption_key:
            return await interaction.response.send_message("I could not find the saved token encryption key. Please restart the build and try again.", ephemeral=True)
        try:
            decrypted_token = decrypt_token(encrypted_token, encryption_key)
            package_bytes = generate_package(data, decrypted_token)
            modules = data.get("modules", [])
            module_versions = {
                module: getattr(importlib.import_module(f"modules.{module}"), "MODULE_VERSION", "unknown")
                for module in modules
            }
            module_schema_hashes = {
                module: module_schema_hash(module)
                for module in modules
            }
            await self.bot.db.execute(
                """
                INSERT INTO user_bots(user_id, bot_name, modules_enabled, encrypted_token,
                                      currency_name, prefix, module_versions, module_schema_hashes)
                VALUES($1, $2, $3::jsonb, $4, $5, $6, $7::jsonb, $8::jsonb)
                """.strip(),
                self.user_id,
                data.get("bot_name", "discord-bot"),
                json.dumps(modules),
                encrypted_token,
                data.get("currency_name", "coins"),
                data.get("prefix", "!"),
                json.dumps(module_versions),
                json.dumps(module_schema_hashes),
            )
            await complete_session(self.bot.db, self.user_id)
            package = discord.File(io.BytesIO(package_bytes), filename=f"{safe_filename(data.get('bot_name', 'discord-bot'))}.zip")
            await interaction.response.edit_message(
                content="Your bot package is ready. Download the ZIP and follow the README for the next steps.",
                attachments=[package],
                view=None,
            )
        except Exception:
            log.exception("Bot package generation failed for user %s", self.user_id)
            if not interaction.response.is_done():
                await interaction.response.send_message("I could not generate your bot package. Please check your answers and try again.", ephemeral=True)
            else:
                await interaction.followup.send("I could not generate your bot package. Please try /build again.", ephemeral=True)


class ActionButton(Button):
    def __init__(self, label, custom_id, callback, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, custom_id=custom_id, style=style)
        self.handler = callback
    async def callback(self, interaction):
        if self.label in MODULES.values(): return await self.handler(interaction, next(k for k,v in MODULES.items() if v == self.label))
        if self.custom_id.endswith(":host:railway"): return await self.handler(interaction, "railway")
        if self.custom_id.endswith(":host:fly"): return await self.handler(interaction, "fly.io")
        return await self.handler(interaction)


class RewardView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        for key, label in (("separate", "Separate rewards"), ("xp_only", "XP only"), ("currency_only", "Currency only")):
            self.add_item(ActionButton(label, f"build:{user_id}:reward:{key}", self.choose))
        self.bot, self.user_id = bot, user_id
    async def choose(self, interaction):
        key = interaction.data["custom_id"].rsplit(":", 1)[-1]
        row = await get_active_session(self.bot.db, self.user_id); data = answers(row); data["reward_coordination"] = key
        await update_session(self.bot.db, self.user_id, 4, data)
        await interaction.response.send_modal(PrefixModal(self.bot, self.user_id))

class NameModal(Modal, title="Bot name"):
    name = TextInput(label="Bot name", min_length=1, max_length=80)
    def __init__(self, bot, user_id): super().__init__(); self.bot, self.user_id = bot, user_id
    async def on_submit(self, interaction):
        row = await get_active_session(self.bot.db, self.user_id); data = answers(row); data["bot_name"] = str(self.name.value)
        await update_session(self.bot.db, self.user_id, 3, data)
        await interaction.response.edit_message(content="**Step 3 of 9 — Choose modules**\nSelect modules, then press Continue.", view=WizardView(self.bot, self.user_id, 3))

class PrefixModal(Modal, title="Command prefix"):
    prefix = TextInput(label="Prefix", default="!", max_length=5)
    def __init__(self, bot, user_id): super().__init__(); self.bot, self.user_id = bot, user_id
    async def on_submit(self, interaction):
        row = await get_active_session(self.bot.db, self.user_id); data = answers(row); data["prefix"] = str(self.prefix.value)
        if "economy" in data.get("modules", []): return await update_and_modal(interaction, self.bot, self.user_id, 5, data, CurrencyModal)
        await update_and_modal(interaction, self.bot, self.user_id, 6, data, None)

class CurrencyModal(Modal, title="Currency name"):
    currency = TextInput(label="Currency", default="coins", max_length=30)
    def __init__(self, bot, user_id): super().__init__(); self.bot, self.user_id = bot, user_id
    async def on_submit(self, interaction):
        row = await get_active_session(self.bot.db, self.user_id); data = answers(row); data["currency_name"] = str(self.currency.value)
        await update_and_modal(interaction, self.bot, self.user_id, 6, data, None)

class TokenModal(Modal, title="Bot token"):
    token = TextInput(label="Paste token", min_length=40, max_length=120, style=discord.TextStyle.paragraph)
    def __init__(self, bot, user_id): super().__init__(); self.bot, self.user_id = bot, user_id
    async def on_submit(self, interaction):
        if not TOKEN_RE.fullmatch(str(self.token.value)): return await interaction.response.send_message("That does not look like a Discord token. Copy it from Developer Portal and try again.", ephemeral=True)
        key = self.bot.config.encryption_key
        if not key: return await interaction.response.send_message("ENCRYPTION_KEY is not configured; an administrator must set it before accepting tokens.", ephemeral=True)
        row = await get_active_session(self.bot.db, self.user_id); data = answers(row); data["encrypted_token"] = encrypt_token(str(self.token.value), key)
        await update_session(self.bot.db, self.user_id, 8, data)
        await interaction.response.edit_message(content="**Step 8 of 9 — Choose hosting**\nRailway is simple and GitHub-friendly. Fly.io offers more infrastructure control.", view=WizardView(self.bot, self.user_id, 8))

async def update_and_modal(interaction, bot, user_id, step, data, modal):
    await update_session(bot.db, user_id, step, data)
    if modal: return await interaction.response.send_modal(modal(bot, user_id))
    await interaction.response.edit_message(content="**Step 6 of 9 — Developer Portal walkthrough**\n1. Open the Discord Developer Portal.\n2. Click **New Application**, name it, and click Create.\n3. Open **Bot** in the left sidebar, then click **Add Bot**.\n4. Under Token, click **Reset Token**, then copy it. Never share it publicly.", view=WizardView(bot, user_id, 6))

def summary(data):
    return "\n".join((f"Bot: {data.get('bot_name','—')}", f"Modules: {', '.join(data.get('modules', []))}", f"Prefix: {data.get('prefix','!')}", f"Currency: {data.get('currency_name','—')}", f"Host: {data.get('host','—')}"))

async def render(bot, user_id: int, row: dict[str, Any]):
    step = int(row.get("current_step", 1))
    data = answers(row)
    if step == 1: return "**Step 1 of 9 — Welcome**\nBot Builder helps you create a configured Discord bot.", WizardView(bot, user_id, 1)
    if step == 3: return "**Step 3 of 9 — Choose modules**\nSelect modules, then press Continue.", WizardView(bot, user_id, 3)
    if step == 4: return "**Step 4 of 9 — Reward coordination**\nLeveling and Economy can both reward activity. Choose how to coordinate them.", RewardView(bot, user_id)
    if step == 5: return "**Step 5 of 9 — Currency name**\nChoose the name used for economy balances and rewards.", WizardView(bot, user_id, 5)
    if step == 6: return "**Step 6 of 9 — Developer Portal walkthrough**\nFollow the numbered instructions above, then provide the token.", WizardView(bot, user_id, 6)
    if step == 7: return "**Step 7 of 9 — Token input**\nPaste the bot token you copied from the Developer Portal. It will be encrypted before storage.", WizardView(bot, user_id, 7)
    if step == 8: return "**Step 8 of 9 — Choose hosting**\nRailway is simple and GitHub-friendly. Fly.io offers more infrastructure control.", WizardView(bot, user_id, 8)
    return f"**Step 9 of 9 — Review**\n{summary(data)}", WizardView(bot, user_id, 9)
