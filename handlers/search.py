import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import Config
from services.database import (
    get_settings, movies_col, series_col, files_col, search_requests_col
)
from services.cache import is_rate_limited
from services.scheduler import schedule_deletion
from services.search_engine import search_content
from utils.normalization import parse_query_metadata
from utils.logging import log_to_telegram

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    raw_query = update.message.text.strip()
    settings = get_settings()
    
    # 1. Maintenance Check
    if settings.get("maintenance", False):
        if user.id not in Config.OWNER_IDS:
            msg = await update.message.reply_text(settings.get("maintenance_message"))
            schedule_deletion(chat.id, msg.message_id, 10)
            return

    # 2. Rate Limiting
    if is_rate_limited(user.id, settings.get("rate_limit_count", 10), settings.get("rate_limit_window", 60)):
        msg = await update.message.reply_text("⚠️ Rate limit exceeded. Please wait a bit before searching again.")
        schedule_deletion(chat.id, msg.message_id, 5)
        return

    # 3. Normalization & Query Parsing
    title, year, season, episode = parse_query_metadata(raw_query)
    if not title:
        return
    
    is_series_query = season is not None or episode is not None
    
    # 4. Search Execution
    res = search_content(title, year, is_series=is_series_query)
    
    # If not found in primary guessed category, toggle and search once more
    if res["status"] == "none":
        res = search_content(title, year, is_series=not is_series_query)
        if res["status"] != "none":
            is_series_query = not is_series_query

    # 5. Handle Not Found
    if res["status"] == "none":
        msg = await update.message.reply_text("❌ File not found")
        schedule_deletion(chat.id, msg.message_id, 5)
        
        # Log search request to DB & Request Channel
        search_requests_col.insert_one({
            "query": raw_query,
            "user_id": user.id,
            "username": user.username,
            "date": datetime.datetime.utcnow()
        })
        await log_to_telegram(
            context.bot,
            Config.REQUEST_CHANNEL_ID,
            f"🔎 <b>New Request Not Found</b>\nQuery: <code>{raw_query}</code>\nUser: @{user.username or user.id}"
        )
        return

    # 6. Build Display (Exact / Corrected / Fuzzy Suggestions)
    if res["status"] in ["exact", "corrected"]:
        item = res["results"][0]
        await send_item_view(context.bot, chat.id, item, is_series=is_series_query, season=season, episode=episode)
    else:
        # Fuzzy Suggestions (Up to 3)
        buttons = []
        for s in res["results"]:
            label = f"🎬 {s['title']} ({s.get('year', 'N/A')})"
            item_type = "s" if is_series_query else "m"
            buttons.append([InlineKeyboardButton(label, callback_data=f"view_{item_type}_{s['_id']}")])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        msg = await update.message.reply_text("🔎 <b>Search Results:</b>", reply_markup=reply_markup, parse_mode="HTML")
        if settings.get("auto_delete", True):
            schedule_deletion(chat.id, msg.message_id, settings.get("delete_time", 300))

async def send_item_view(bot, chat_id: int, item: dict, is_series: bool, season=None, episode=None):
    settings = get_settings()
    caption = f"🎬 <b>{item['title']}</b>"
    if item.get("year"):
        caption += f" ({item['year']})"
        
    buttons = []
    
    if is_series:
        # Hierarchical lookup for Series
        seasons = item.get("seasons", [])
        if season is None:
            # Show available seasons
            row = []
            for s_num in seasons:
                row.append(InlineKeyboardButton(f"Season {s_num}", callback_data=f"ser_{item['_id']}_s{s_num}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
        else:
            # Show available episodes in that season
            episodes = files_col.distinct("episode", {"item_id": str(item["_id"]), "season": season})
            row = []
            for ep_num in sorted(episodes):
                row.append(InlineKeyboardButton(f"Ep {ep_num}", callback_data=f"ser_{item['_id']}_s{season}_e{ep_num}"))
                if len(row) == 3:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
    else:
        # Show verified available languages for Movie
        available_files = list(files_col.find({"item_id": str(item["_id"])}))
        row = []
        for f in available_files:
            lang = f.get("language", "Default")
            quality = f.get("quality", "")
            btn_label = f"{lang} [{quality}]" if quality else lang
            row.append(InlineKeyboardButton(btn_label, callback_data=f"file_{f['_id']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
            
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    
    # Poster sending
    if settings.get("tmdb_poster", True) and item.get("poster_url"):
        msg = await bot.send_photo(chat_id=chat_id, photo=item["poster_url"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
    else:
        msg = await bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
        
    if settings.get("auto_delete", True):
        schedule_deletion(chat_id, msg.message_id, settings.get("delete_time", 300))
  
