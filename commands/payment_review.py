from __future__ import annotations

import asyncio
import json
import discord
from discord.ext import commands


class PaymentReviewButton(discord.ui.DynamicItem[discord.ui.Button], template=r"payment:(approve|reject):(\d+)"):
    def __init__(self, item: discord.ui.Button):
        super().__init__(item)

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, custom_id: str):
        action, payment_id = custom_id.split(":")[1:]
        label = "Approve" if action == "approve" else "Reject"
        style = discord.ButtonStyle.success if action == "approve" else discord.ButtonStyle.danger
        return cls(discord.ui.Button(label=label, style=style, custom_id=custom_id))

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("PaymentReview")
        if cog is None or not cog.is_admin(interaction.user.id):
            return await interaction.response.send_message("You are not authorized to review payments.", ephemeral=True)
        action, payment_id = self.match.groups()
        if action == "approve":
            result = await cog.approve(int(payment_id), str(interaction.user.id))
            message = "Approved. The bot unlock is now active." if result else "This payment is expired or already finalized."
        else:
            result = await cog.reject(int(payment_id), str(interaction.user.id))
            message = "Rejected. No bot settings were changed." if result else "This payment is expired or already finalized."
        await interaction.response.edit_message(content=message, view=None)


class PaymentReview(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.poll_task = bot.loop.create_task(self.poll())

    def is_admin(self, user_id: int) -> bool:
        return not self.bot.config.admin_user_ids or user_id in self.bot.config.admin_user_ids

    async def poll(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                if self.bot.config.admin_review_channel_id:
                    rows = await self.bot.db.fetch(
                        "SELECT id, reference, buyer_email, buyer_name, bot_id::text FROM unlock_payments "
                        "WHERE submitted_at IS NOT NULL AND status='pending' AND review_message_id IS NULL "
                        "AND (expires_at IS NULL OR expires_at > NOW()) ORDER BY submitted_at LIMIT 20"
                    )
                    channel = self.bot.get_channel(self.bot.config.admin_review_channel_id)
                    if channel:
                        for row in rows:
                            view = discord.ui.View(timeout=None)
                            view.add_item(discord.ui.Button(label="Approve", style=discord.ButtonStyle.success, custom_id=f"payment:approve:{row['id']}"))
                            view.add_item(discord.ui.Button(label="Reject", style=discord.ButtonStyle.danger, custom_id=f"payment:reject:{row['id']}"))
                            message = await channel.send(
                                f"Payment review #{row['id']}\nReference: `{row['reference']}`\nBuyer: {row['buyer_name'] or 'Unknown'} / {row['buyer_email'] or 'Unknown'}\nTarget bot: `{row['bot_id']}`\nAmount: $5.00 USD",
                                view=view,
                            )
                            await self.bot.db.execute("UPDATE unlock_payments SET review_message_id=$1, updated_at=NOW() WHERE id=$2 AND review_message_id IS NULL", str(message.id), row["id"])
            except Exception:
                pass
            await asyncio.sleep(5)

    async def approve(self, payment_id: int, reviewer: str) -> bool:
        async with self.bot.db.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("SELECT id, bot_id::text, status, expires_at FROM unlock_payments WHERE id=$1 FOR UPDATE", payment_id)
                if not row or row["status"] != "pending" or (row["expires_at"] and row["expires_at"] <= await conn.fetchval("SELECT NOW()")):
                    return False
                await conn.execute("UPDATE unlock_payments SET status='verified', verified_at=NOW(), approved_by=$2, updated_at=NOW() WHERE id=$1", payment_id, reviewer)
                updated = await conn.execute(
                    "UPDATE user_bots SET unlocked=TRUE, unlocked_at=NOW(), modules_enabled=$2::jsonb, "
                    "status='active', last_regenerated_at=NOW() WHERE bot_id=$1::uuid",
                    row["bot_id"], json.dumps([
                        "leveling", "welcome", "moderation", "economy", "reaction_roles", "starboard",
                        "ticket", "giveaways", "schedule", "analytics", "voice_xp", "autopost", "automod", "help",
                    ]),
                )
                if updated != "UPDATE 1":
                    raise RuntimeError("Payment target bot was not found; approval transaction rolled back")
                return True

    async def reject(self, payment_id: int, reviewer: str) -> bool:
        result = await self.bot.db.execute("UPDATE unlock_payments SET status='rejected', approved_by=$2, updated_at=NOW() WHERE id=$1 AND status='pending' AND (expires_at IS NULL OR expires_at > NOW())", payment_id, reviewer)
        return result.endswith("1")

    def cog_unload(self):
        self.poll_task.cancel()


async def setup(bot):
    await bot.add_cog(PaymentReview(bot))
