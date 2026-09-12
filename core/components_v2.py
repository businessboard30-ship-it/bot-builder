import discord


def panel(title: str, body: str, *, button: discord.ui.Button | None = None) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container(accent_color=discord.Color.blurple())
    container.add_item(discord.ui.TextDisplay(f"## {title}\n{body}"))
    container.add_item(discord.ui.Separator())
    if button:
        section = discord.ui.Section(discord.ui.TextDisplay("Use the action below"), accessory=button)
        container.add_item(section)
    view.add_item(container)
    return view
