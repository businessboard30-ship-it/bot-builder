"""
Package generator: assembles completed wizard sessions into deployable bot zip files.
Returns bytes representing a complete, ready-to-deploy bot package.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from typing import Any

import importlib

MODULE_SQL_MAP = {
    "leveling": "sql/leveling.sql",
    "welcome": "sql/welcome.sql",
    "moderation": "sql/moderation.sql",
    "economy": "sql/economy.sql",
}


def load_sql_file(path: str) -> str:
    """Load SQL file content from disk."""
    try:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
        with open(full_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        raise RuntimeError(f"Failed to load {path}: {e}")


def build_selected_schema(modules: list[str]) -> str:
    """Build schema.sql containing only selected modules' tables + shared tables."""
    lines = [
        "-- Bot-specific schema for selected modules",
        "-- DO NOT EDIT BY HAND: regenerated with each bot build",
        "",
    ]
    
    # Extension required by shared tables
    lines.append("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    lines.append("")
    
    # Add selected module schemas
    for module in modules:
        if module in MODULE_SQL_MAP:
            sql = load_sql_file(MODULE_SQL_MAP[module])
            lines.append(f"-- === {module.upper()} ===")
            lines.append(sql)
            lines.append("")
    
    return "\n".join(lines)


def build_requirements(modules: list[str]) -> str:
    """Return only dependencies needed by the generated bot runtime."""
    requirements = [
        "discord.py==2.4.0",  # bot.py, core/base_cog.py, and selected modules import discord.py
        "asyncpg==0.29.0",  # core/database.py uses asyncpg
        "python-dotenv==1.0.1",  # bot.py imports dotenv.load_dotenv
    ]
    return "\n".join(requirements) + "\n"


def build_env_example(data: dict[str, Any]) -> str:
    """Generate .env.example with required variables for selected modules."""
    modules = data.get("modules", [])
    lines = [
        "# Bot Builder Generated Bot Configuration",
        "# Copy this file to .env and fill in your values",
        "",
        "# Core (required for all bots)",
        "DISCORD_BOT_TOKEN=your_bot_token_here",
        "# Get this from https://discord.com/developers/applications",
        "",
        "DATABASE_URL=postgresql://user:password@host:5432/dbname",
        "# Postgres connection string (Supabase or Neon)",
        "",
        "PREFIX=!",
        "# Command prefix (e.g., !, /, etc.)",
        "",
        "BOT_NAME=" + data.get("bot_name", "My Bot"),
        "# Display name for your bot",
        "",
    ]
    
    # Economy-specific
    if "economy" in modules:
        lines.extend([
            "# Economy module",
            "CURRENCY_NAME=" + data.get("currency_name", "coins"),
            "# Name of your currency (coins, gold, etc.)",
            "",
        ])
    
    return "\n".join(lines)


def build_readme(data: dict[str, Any]) -> str:
    """Generate plain-language README for the package."""
    bot_name = data.get("bot_name", "My Bot")
    prefix = data.get("prefix", "!")
    host = data.get("host", "Railway")
    modules = data.get("modules", [])
    currency = data.get("currency_name", "coins")
    
    module_features = {
        "leveling": "XP and rank commands",
        "welcome": "Welcome messages for new members",
        "moderation": "Warnings and moderation tools",
        "economy": "Balances and daily rewards",
    }
    
    features = "\n".join([f"- {module_features.get(m, m)}" for m in modules])
    
    host_friendly = "Railway" if host == "railway" else "Fly.io"
    db_friendly = "Supabase or Neon"
    
    economy_line = f"   - CURRENCY_NAME = {currency}\n" if "economy" in modules else ""
    return f"""{bot_name} — Discord Bot
==========================

What this is
============
This is {bot_name}, a Discord bot built with Bot Builder. It runs on {host_friendly} and keeps data in a Postgres database.

Features:
{features}

What you'll need
================
- A free GitHub account (github.com)
- A free {host_friendly} account ({host_friendly} site)
- A free Postgres database ({db_friendly})
- A Discord bot token from the Discord Developer Portal

Step 1: Get your code onto GitHub
==================================

On a computer:
1. Open a terminal in this package folder.
2. Run: git init
3. Run: git add .
4. Run: git commit -m "Add my Discord bot"
5. Create an empty repository on GitHub.
6. Run: git remote add origin YOUR_GITHUB_REPO_URL
7. Run: git push -u origin main
GitHub Desktop is an easier alternative if you do not want to use commands.

On a phone/tablet:
1. Go to GitHub.com and create a new repository.
2. Open the empty repository.
3. Choose Add file, then Upload files.
4. Drag the files from this package into the upload area.
5. Choose Commit changes.

Step 2: Set up your database
============================
1. Create a free database at Supabase or Neon.
2. Open its SQL editor.
3. Open schema.sql from this package and copy all of it.
4. Paste it into the SQL editor and click Run.
5. Copy the Postgres connection string for the next step.

Step 3: Deploy to {host_friendly}
=================================
1. Create a new {host_friendly} project from your GitHub repository.
2. Open the Environment Variables area.
3. Add these values:
   - DISCORD_BOT_TOKEN = your Discord bot token
   - DATABASE_URL = your Postgres connection string
   - PREFIX = {prefix}
   - BOT_NAME = {bot_name}
{economy_line}4. Start or deploy the project.
5. Check the deploy logs. Your bot should appear online in Discord.

Environment variables reference
================================
| Variable | What it is for | Where to get it |
| --- | --- | --- |
| DISCORD_BOT_TOKEN | Connects the bot to Discord | Discord Developer Portal |
| DATABASE_URL | Connects the bot to Postgres | Supabase or Neon |
| PREFIX | Starts text commands | Your choice |
| BOT_NAME | Names the bot in logs | Your choice |
{('| CURRENCY_NAME | Names economy money | Your choice |' if 'economy' in modules else '')}

Troubleshooting
===============
- Missing environment variable: read the first error in the {host_friendly} logs and add the named variable.
- Wrong Postgres connection string: copy the complete DATABASE_URL again, including its postgresql:// prefix.
- Bot is not online: check the token, confirm the bot was invited to your server, and inspect the logs for LoginFailure.
- Commands are missing: wait for Discord command sync, then restart the deployment and check permissions.

Still stuck?
=============
Paste the exact error from the logs into Claude or ChatGPT for help debugging. Support Discord: https://discord.gg/jSfXzVVUtC
"""


def module_schema_hash(module: str) -> str:
    """Return a stable hash of a module's current SQL schema source."""
    return hashlib.sha256(load_sql_file(MODULE_SQL_MAP[module]).encode("utf-8")).hexdigest()


def generate_update_package(changed_modules: list[str], schema_changed_modules: list[str] | None = None) -> bytes:
    """Create an update archive, including migration SQL only for changed schemas."""
    schema_changed_modules = schema_changed_modules or []
    root = os.path.dirname(os.path.dirname(__file__))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for module in changed_modules:
            module_path = os.path.join(root, "modules", f"{module}.py")
            if os.path.exists(module_path):
                with open(module_path, "rb") as handle:
                    zf.writestr(f"modules/{module}.py", handle.read())
        if schema_changed_modules:
            migration = "-- Review before running. Statements are idempotent CREATE TABLE IF NOT EXISTS definitions.\n\n"
            migration += "\n\n".join(load_sql_file(MODULE_SQL_MAP[module]) for module in schema_changed_modules if module in MODULE_SQL_MAP)
            zf.writestr("migration.sql", migration)
    return buffer.getvalue()


def generate_package(data: dict[str, Any], decrypted_token: str) -> bytes:
    """
    Assemble a deployable bot package from completed wizard answers.
    
    Returns bytes representing a ready-to-deploy zip file.
    Does NOT include the decrypted token in the archive (user adds it to .env on their machine).
    """
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Add all core/ files (always included)
        core_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core")
        for filename in os.listdir(core_dir):
            if filename.endswith(".py"):
                filepath = os.path.join(core_dir, filename)
                with open(filepath, 'r') as f:
                    zf.writestr(f"core/{filename}", f.read())
        
        # 2. Add bot.py (entrypoint)
        bot_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.py")
        with open(bot_path, 'r') as f:
            zf.writestr("bot.py", f.read())
        
        # 3. Add selected modules only
        modules = data.get("modules", [])
        modules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules")
        for module in modules:
            module_file = os.path.join(modules_dir, f"{module}.py")
            if os.path.exists(module_file):
                with open(module_file, 'r') as f:
                    zf.writestr(f"modules/{module}.py", f.read())
        
        # 4. Bundle the selected modules so bot.py never falls back to unbundled defaults.
        zf.writestr("modules_enabled.json", json.dumps({"modules": modules}, indent=2) + "\n")

        # 5. Bundle only dependencies used by the generated bot runtime.
        zf.writestr("requirements.txt", build_requirements(modules))

        # 6. Add selected schema only + shared tables (never include wizard_sessions.sql or user_bots.sql)
        schema = build_selected_schema(modules)
        zf.writestr("schema.sql", schema)
        
        # 5. Add .env.example (placeholder only, NO decrypted token)
        env_example = build_env_example(data)
        zf.writestr(".env.example", env_example)
        
        # 6. Add deployment template based on host choice
        host = data.get("host", "railway")
        if host == "railway":
            procfile = """worker: python bot.py"""
            zf.writestr("Procfile", procfile)
        elif host == "fly.io":
            fly_toml = f"""app = "{data.get('bot_name', 'my-bot').lower().replace(' ', '-')}"
primary_region = "ord"

[build]
  builder = "paketobuildpacks/builder:base"

[processes]
  app = "python bot.py"
"""
            zf.writestr("fly.toml", fly_toml)
        
        # 7. Add README
        readme = build_readme(data)
        zf.writestr("README.md", readme)
        
        # 8. Add .gitignore
        gitignore = """.env
__pycache__/
*.pyc
.env.local
.DS_Store
"""
        zf.writestr(".gitignore", gitignore)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
