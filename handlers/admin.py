from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import Config
from services.database import get_settings, update_settings, movies_col, series_col, files_col

def is_admin(user_id: int) -> bool:
    return user_id in Config.OWNER_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    settings = get_settings()
    m_status = "🔴 OFF" if not settings.get("maintenance") else "🟢 ON"
    p_status = "🟢 ON" if settings.get("tmdb_poster") else "🔴 OFF"
    s_status = "🟢 ON" if settings.get("url_shortener") else "🔴 OFF"

    keyboard = [
        [InlineKeyboardButton(f"Maintenance: {m_status}", callback_data="adm_toggle_maintenance")],
        [InlineKeyboardButton(f"TMDB Poster: {p_status}", callback_data="adm_toggle_poster")],
        [InlineKeyboardButton(f"Shortener: {s_status}", callback_data="adm_toggle_shortener")],
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats")]
    ]
    await update.message.reply_text("⚙️ <b>Admin Control Center</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.answer("Unauthorized", show_alert=True)
        return

    data = query.data
    settings = get_settings()

    if data == "adm_toggle_maintenance":
        update_settings("maintenance", not settings.get("maintenance"))
    elif data == "adm_toggle_poster":
        update_settings("tmdb_poster", not settings.get("tmdb_poster"))
    elif data == "adm_toggle_shortener":
        update_settings("url_shortener", not settings.get("url_shortener"))
    elif data == "adm_stats":
        m_count = movies_col.count_documents({})
        s_count = series_col.count_documents({})
        f_count = files_col.count_documents({})
        await query.answer(f"Movies: {m_count}\nSeries: {s_count}\nFiles: {f_count}", show_alert=True)
        return

    await query.answer("Updated!")
  
