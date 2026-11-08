"""Copyright takedown tools.
User:   /dmca <file name / link / description>   -> report goes to LOG_CHANNEL
Admins: /takedown <words>   (preview + confirm: deletes matching files and blocks re-indexing)
        /takedown_list      /untakedown <id>
"""
import html
import secrets
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS, LOG_CHANNEL
from database.ia_filterdb import add_takedown, count_takedown_matches, list_takedowns, remove_takedown
from core.ttl_cache import TTLDict

_pending = TTLDict(ttl=600, maxsize=200)   # short token -> (query, admin id)


@Client.on_message(filters.command("dmca") & filters.private)
async def dmca_report(client, message):
    text = " ".join(message.command[1:]).strip()
    if len(text) < 3:
        return await message.reply("Usage: <code>/dmca file name, link or description of the content to remove</code>")
    user = message.from_user
    await client.send_message(
        LOG_CHANNEL,
        f"#DMCA_Report\n\n👤 {user.mention} (<code>{user.id}</code>)\n\n<code>{html.escape(text[:1000])}</code>\n\n"
        f"To remove: <code>/takedown {html.escape(text[:100])}</code>",
    )
    await message.reply("✅ Your report was sent to the admins. Thank you.")


@Client.on_message(filters.command("takedown") & filters.user(ADMINS))
async def takedown_cmd(client, message):
    query = " ".join(message.command[1:]).strip()
    if len(query) < 3:
        return await message.reply("Usage: <code>/takedown words from the file name</code>")
    n = await count_takedown_matches(query)
    token = secrets.token_hex(4)
    _pending[token] = (query, message.from_user.id)
    await message.reply(
        f"<b>Takedown</b> <code>{html.escape(query)}</code>\n\nMatching files in DB: <code>{n}</code>\n"
        "Confirm to delete them and block re-indexing of any file whose name contains all these words.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm", callback_data=f"tkd#ok#{token}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"tkd#no#{token}"),
        ]]),
    )


@Client.on_callback_query(filters.regex(r"^tkd#") & filters.user(ADMINS))
async def takedown_cb(client, query):
    _, action, token = query.data.split("#")
    item = _pending.pop(token, None)
    if not item:
        return await query.answer("Expired - run /takedown again.", show_alert=True)
    if action == "no":
        return await query.message.edit("Cancelled.")
    text, _admin = item
    entry_id, deleted = await add_takedown(text, query.from_user.id)
    await query.message.edit(f"✅ Takedown added (<code>{entry_id}</code>). Files deleted: <code>{deleted}</code>")
    await client.send_message(LOG_CHANNEL, f"#Takedown by {query.from_user.mention}\n<code>{html.escape(text)}</code>\nDeleted: {deleted}")


@Client.on_message(filters.command("takedown_list") & filters.user(ADMINS))
async def takedown_list_cmd(client, message):
    rows = await list_takedowns()
    if not rows:
        return await message.reply("Takedown list is empty.")
    await message.reply("<b>Takedown list</b>\n\n" + "\n".join(f"<code>{i}</code> - {html.escape(q)}" for i, q in rows))


@Client.on_message(filters.command("untakedown") & filters.user(ADMINS))
async def untakedown_cmd(client, message):
    if len(message.command) != 2:
        return await message.reply("Usage: <code>/untakedown id</code> (see /takedown_list)")
    ok = await remove_takedown(message.command[1])
    await message.reply("✅ Removed." if ok else "❌ Not found.")
