from __future__ import annotations

from collections.abc import Iterable

COMMANDS: dict[str, list[tuple[str, str, str, str]]] = {
    "leveling": [("/rank", "/rank [member]", "Show a member's level card and XP.", "Everyone")],
    "welcome": [("/setwelcome", "/setwelcome <channel> <message>", "Configure join messages and cards.", "Manage Server")],
    "moderation": [("/warn", "/warn <member> [reason]", "Warn a member.", "Moderate Members"), ("/warnings", "/warnings <member>", "Review a member's warnings.", "Moderate Members")],
    "economy": [("/balance", "/balance [member]", "Show a member's balance.", "Everyone"), ("/daily", "/daily", "Claim daily currency.", "Everyone"), ("/pay", "/pay <member> <amount>", "Pay another member.", "Everyone")],
    "analytics": [("/analytics", "/analytics", "Show bot analytics.", "Manage Server")],
    "reaction_roles": [("/reactionroles", "/reactionroles", "Configure reaction roles.", "Manage Roles")],
    "starboard": [("/starboard", "/starboard", "Configure the starboard.", "Manage Server")],
    "ticket": [("/ticket", "/ticket", "Create or configure support tickets.", "Manage Channels")],
    "giveaways": [("/giveaway", "/giveaway <prize>", "Create a giveaway.", "Manage Server")],
    "schedule": [("/schedule", "/schedule <channel> <message>", "Schedule a message.", "Manage Messages")],
    "voice_xp": [("/voicexp", "/voicexp", "Show voice XP.", "Everyone")],
    "autopost": [("/autopost", "/autopost <feed_url> <channel>", "Configure an autopost feed.", "Manage Server")],
    "automod": [("/automod", "/automod <enabled>", "Enable or disable automod.", "Manage Server")],
}


def entries_for(enabled_modules: Iterable[str]) -> list[tuple[str, str, str, str]]:
    entries = []
    for module in enabled_modules:
        entries.extend(COMMANDS.get(module, []))
    return entries


def render_help(enabled_modules: Iterable[str]) -> str:
    grouped: dict[str, list[tuple[str, str, str, str]]] = {}
    for command, usage, description, permission in entries_for(enabled_modules):
        category = next((name for name, items in COMMANDS.items() if any(item[0] == command for item in items)), "General")
        grouped.setdefault(category.replace("_", " ").title(), []).append((command, usage, description, permission))
    lines = ["**Command manual**", "Commands are shown for this bot's enabled modules."]
    for category, entries in grouped.items():
        lines.append(f"\n**{category}**")
        lines.extend(f"`{usage}` — {description} *(requires: {permission})*" for _, usage, description, permission in entries)
    return "\n".join(lines)
