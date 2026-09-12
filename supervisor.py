from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import asyncpg

from core.migrate import run_migrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot-supervisor")
LOCK_PATH = Path(os.getenv("SUPERVISOR_LOCK_PATH", "/tmp/prime-bot-supervisor.lock"))
STATE_PATH = Path(os.getenv("SUPERVISOR_STATE_PATH", "/tmp/prime-bot-supervisor.children"))
HEARTBEAT_TIMEOUT = 30
BASE_BACKOFF = 15
MAX_BACKOFF = 300


@dataclass
class ManagedBot:
    bot_id: str
    process: asyncio.subprocess.Process
    next_restart_at: float = 0
    backoff: int = BASE_BACKOFF
    stable_since: float | None = None


def cleanup_orphans() -> None:
    """Kill generated bot children left by a crashed supervisor, not unrelated processes."""
    seen: set[int] = set()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
            if "generated_bot.py" in command and pid != os.getpid():
                seen.add(pid)
                os.kill(pid, signal.SIGTERM)
                log.warning("Cleaned orphaned generated bot process %s", pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    if STATE_PATH.exists():
        STATE_PATH.unlink(missing_ok=True)


async def run() -> None:
    lock_file = LOCK_PATH.open("w+")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.error("Another supervisor is already running")
        return

    cleanup_orphans()
    database_url = os.environ["DATABASE_URL"]
    await run_migrations(database_url)
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    managed: dict[str, ManagedBot] = {}
    retry_at: dict[str, float] = {}
    backoff_by_bot: dict[str, int] = {}
    stopping = False

    def persist_children() -> None:
        STATE_PATH.write_text("\n".join(str(item.process.pid) for item in managed.values()), encoding="utf-8")

    async def stop_all() -> None:
        nonlocal stopping
        stopping = True
        for item in managed.values():
            if item.process.returncode is None:
                item.process.terminate()
        await asyncio.gather(*(item.process.wait() for item in managed.values()), return_exceptions=True)
        STATE_PATH.unlink(missing_ok=True)
        await pool.close()
        lock_file.close()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(stop_all()))

    async def reap(bot_id: str, item: ManagedBot) -> None:
        code = await item.process.wait()
        managed.pop(bot_id, None)
        delay = backoff_by_bot.get(bot_id, BASE_BACKOFF)
        retry_at[bot_id] = time.monotonic() + delay
        backoff_by_bot[bot_id] = min(delay * 2, MAX_BACKOFF)
        log.warning("Bot %s exited with code %s; retry scheduled in %ss", bot_id, code, delay)
        persist_children()

    try:
        while not stopping:
            rows = await pool.fetch(
                "SELECT bot_id::text, encrypted_token, bot_name, prefix, currency_name, support_server_url, modules_enabled "
                "FROM user_bots WHERE status = 'active'"
            )
            active = {row["bot_id"]: row for row in rows}

            for bot_id, item in list(managed.items()):
                if bot_id not in active:
                    if item.process.returncode is None:
                        item.process.terminate()
                    await item.process.wait()
                    managed.pop(bot_id, None)
                elif item.process.returncode is not None:
                    await reap(bot_id, item)

            for bot_id, row in active.items():
                if stopping or bot_id in managed:
                    continue
                now = time.monotonic()
                retry_after = retry_at.get(bot_id, 0)
                if retry_after and now < retry_after:
                    continue
                env = os.environ.copy()
                env.update({
                    "BOT_ID": bot_id,
                    "DISCORD_BOT_TOKEN_ENCRYPTED": row["encrypted_token"],
                    "BOT_NAME": row["bot_name"],
                    "PREFIX": row["prefix"],
                    "CURRENCY_NAME": row["currency_name"],
                    "SUPPORT_SERVER_URL": row["support_server_url"] or "",
                    "MODULES_ENABLED": ",".join(row["modules_enabled"] or []),
                })
                await pool.execute("UPDATE user_bots SET last_heartbeat=NULL WHERE bot_id=$1::uuid", bot_id)
                process = await asyncio.create_subprocess_exec(sys.executable, "generated_bot.py", env=env)
                managed[bot_id] = ManagedBot(bot_id, process, backoff=backoff_by_bot.get(bot_id, BASE_BACKOFF), stable_since=now)
                retry_at.pop(bot_id, None)
                persist_children()
                log.info("Started bot %s; waiting for heartbeat", bot_id)
                deadline = time.monotonic() + HEARTBEAT_TIMEOUT
                while time.monotonic() < deadline and not stopping:
                    heartbeat = await pool.fetchval("SELECT last_heartbeat FROM user_bots WHERE bot_id=$1::uuid", bot_id)
                    if heartbeat is not None:
                        managed[bot_id].stable_since = time.monotonic()
                        backoff_by_bot[bot_id] = BASE_BACKOFF
                        break
                    await asyncio.sleep(1)
                else:
                    log.warning("Bot %s did not heartbeat within %ss; terminating before next spawn", bot_id, HEARTBEAT_TIMEOUT)
                    process.terminate()
                    await process.wait()
                    managed.pop(bot_id, None)
                    delay = backoff_by_bot.get(bot_id, BASE_BACKOFF)
                    retry_at[bot_id] = time.monotonic() + delay
                    backoff_by_bot[bot_id] = min(delay * 2, MAX_BACKOFF)
                    persist_children()

            for bot_id, item in list(managed.items()):
                if item.stable_since and time.monotonic() - item.stable_since >= 60:
                    backoff_by_bot[bot_id] = BASE_BACKOFF
            await asyncio.sleep(5)
    finally:
        await stop_all()


if __name__ == "__main__":
    asyncio.run(run())
