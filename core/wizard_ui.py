from __future__ import annotations

import re
import discord


def _id_pattern(name: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(name)}:(?P<bot_id>[0-9a-f-]+):(?P<guild_id>[0-9]+):(?P<invoker_id>[0-9]+)$")


def _encode(name: str, bot_id: str, guild_id: int, invoker_id: int) -> str:
    return f"{name}:{bot_id}:{guild_id}:{invoker_id}"


def _decode(match: re.Match[str]) -> tuple[str, int, int]:
    return match.group("bot_id"), int(match.group("guild_id")), int(match.group("invoker_id"))


async def _check_access(interaction: discord.Interaction, invoker_id: int) -> bool:
    if interaction.user.id == invoker_id:
        return True
    if interaction.response.is_done():
        await interaction.followup.send("Only the admin who opened this setup can change it.", ephemeral=True)
    else:
        await interaction.response.send_message("Only the admin who opened this setup can change it.", ephemeral=True)
    return False


async def _rerender(interaction: discord.Interaction, *, content: str, view: discord.ui.View | None = None) -> None:
    if interaction.response.is_done():
        await interaction.edit_original_response(content=content, view=view)
    else:
        await interaction.response.edit_message(content=content, view=view)
