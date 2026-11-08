"""Broadcast runner with checkpoints. A plain module (not in plugins/) so the lock is shared by
the /broadcast command and /resume_jobs - plugin files can be loaded twice and would get separate locks."""
import asyncio
import logging
import time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.users_chats_db import db
from database import jobs_db
from utils import temp, get_readable_time, users_broadcast

lock = asyncio.Lock()


async def resume_users_broadcast(bot, status_msg, job):
    """Continue a broadcast that was interrupted by a restart / cancel (see /resume_jobs)."""
    try:
        b_msg = await bot.get_messages(job["chat_id"], job["msg_id"])
    except Exception:
        b_msg = None
    if not b_msg or b_msg.empty:
        await jobs_db.finish_job(job["_id"])
        return await status_msg.edit("❌ The original broadcast message was deleted - cannot resume.")
    await run_users_broadcast(bot, b_msg, job.get("is_pin", False), status_msg, start=int(job.get("done", 0)), stats=job)


async def run_users_broadcast(bot, b_msg, is_pin, techifybots_status_msg, start=0, stats=None):
    users = [user async for user in await db.get_all_users()]
    total_users = len(users)
    st = stats or {}
    success, blocked, deleted, failed = (int(st.get(k, 0)) for k in ("success", "blocked", "deleted", "failed"))
    job_id = "broadcast:users"
    start_time = time.time()
    cancelled = False
    await jobs_db.save_job(job_id, kind="bcast_users", chat_id=b_msg.chat.id, msg_id=b_msg.id, is_pin=is_pin,
                           total=total_users, done=start, success=success, blocked=blocked, deleted=deleted,
                           failed=failed, status="running")

    async def send(user):
        try:
            _, result = await users_broadcast(int(user["id"]), b_msg, is_pin)
            return result
        except Exception as e:
            logging.exception(f"Error sending broadcast to {user['id']}")
            return "Error"
    async with lock:
        for i in range(start, total_users, 100):
            if temp.B_USERS_CANCEL:
                temp.B_USERS_CANCEL = False
                cancelled = True
                break
            batch = users[i:i + 100]
            results = await asyncio.gather(*[send(user) for user in batch])
            for res in results:
                if res == "Success":
                    success += 1
                elif res == "Blocked":
                    blocked += 1
                elif res == "Deleted":
                    deleted += 1
                elif res == "Error":
                    failed += 1
            done = i + len(batch)
            await jobs_db.save_job(job_id, done=done, success=success, blocked=blocked, deleted=deleted, failed=failed, status="running")
            elapsed = get_readable_time(time.time() - start_time)
            await techifybots_status_msg.edit(
                f"📣 <b>Broadcast Progress....:</b>\n\n"
                f"👥 Total: <code>{total_users}</code>\n"
                f"✅ Done: <code>{done}</code>\n"
                f"📬 Success: <code>{success}</code>\n"
                f"⛔ Blocked: <code>{blocked}</code>\n"
                f"🗑️ Deleted: <code>{deleted}</code>\n"
                f"⏱️ Time: {elapsed}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data="broadcast_cancel#users")]]))
            await asyncio.sleep(0.1)
    if cancelled:
        await jobs_db.save_job(job_id, status="paused")
    else:
        await jobs_db.finish_job(job_id)
    elapsed = get_readable_time(time.time() - start_time)
    final_status = (
        f"{'⏸ <b>Broadcast Paused (resume with /resume_jobs).</b>' if cancelled else '✅ <b>Broadcast Completed.</b>'}\n\n"
        f"🕒 Time: {elapsed}\n"
        f"👥 Total: <code>{total_users}</code>\n"
        f"📬 Success: <code>{success}</code>\n"
        f"⛔ Blocked: <code>{blocked}</code>\n"
        f"🗑️ Deleted: <code>{deleted}</code>\n"
        f"❌ Failed: <code>{failed}</code>"
    )
    await techifybots_status_msg.edit(final_status)
