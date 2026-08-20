from bson import ObjectId
from telegram import Update
from telegram.ext import ContextTypes
from services.database import files_col, movies_col, series_col, get_settings
from services.shortener import shorten_url
from services.scheduler import schedule_deletion

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    settings = get_settings()

    if data.startswith("file_"):
        file_id = data.split("_")[1]
        file_doc = files_col.find_one({"_id": ObjectId(file_id)})
        if not file_doc:
            await query.edit_message_text("❌ Link unavailable.")
            return

        dest_url = file_doc["file_link"]
        if settings.get("url_shortener", False):
            dest_url = await shorten_url(dest_url)

        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ <b>Access Link:</b>\n{dest_url}",
            parse_mode="HTML"
        )
        if settings.get("auto_delete", True):
            schedule_deletion(chat_id, msg.message_id, settings.get("delete_time", 300))
  
