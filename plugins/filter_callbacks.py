"""Quality / language / season filter buttons (split out of pmfilter.py)."""
import math
import pytz
import logging
from info import *
from search_state import BUTTONS, FRESH
from Script import script
from datetime import datetime, timedelta
from utils import get_size, temp, get_settings, save_group_settings, get_cap, clean_filename, generate_season_variations, clean_search_text
from database.ia_filterdb import get_search_results
from pyrogram.errors import MessageIdInvalid, MessageNotModified
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.users_chats_db import db


logger = logging.getLogger(__name__)

@Client.on_callback_query(filters.regex(r"^qualities#"))
async def qualities_cb_handler(client: Client, query: CallbackQuery):
    try:
        if int(query.from_user.id) not in [query.message.reply_to_message.from_user.id, 0]:
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    except Exception as _ignored:
        logging.getLogger(__name__).debug("Ignored error: %r", _ignored)

    _, key = query.data.split("#")
    search = FRESH.get(key)
    if not search:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    search = search.replace(' ', '_')

    btn = []
    for i in range(0, len(QUALITIES), 2):
        q1 = QUALITIES[i]
        row = [InlineKeyboardButton(
            text=q1, callback_data=f"fq#{q1.lower()}#{key}")]
        if i + 1 < len(QUALITIES):
            q2 = QUALITIES[i + 1]
            row.append(InlineKeyboardButton(
                text=q2, callback_data=f"fq#{q2.lower()}#{key}"))
        btn.append(row)

    btn.insert(0, [InlineKeyboardButton(text="⇊ ꜱᴇʟᴇᴄᴛ ǫᴜᴀʟɪᴛʏ ⇊", callback_data="ident")])
    btn.append([InlineKeyboardButton(text="⋞ ʙᴀᴄᴋ ᴛᴏ ꜰɪʟᴇs", callback_data=f"fq#homepage#{key}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^fq#"))
async def filter_qualities_cb_handler(client: Client, query: CallbackQuery):
    _, qual, key = query.data.split("#")
    is_premium = await db.has_premium_access(query.from_user.id)
    if qual != "homepage":
        if QUALITY_LIMIT:
            if not is_premium and qual not in FREE_QUALITIES:
                return await query.answer("ᴛʜɪs ǫᴜᴀʟɪᴛʏ ɪs ꜰᴏʀ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ᴏɴʟʏ !", show_alert=True)
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    search = FRESH.get(key)
    if not search:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    search = search.replace("_", " ")
    baal = qual in search
    if baal:
        search = search.replace(qual, "")
    else:
        search = search
    req = query.from_user.id
    chat_id = query.message.chat.id
    message = query.message
    try:
        if int(query.from_user.id) not in [query.message.reply_to_message.from_user.id, 0]:
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    except Exception as _ignored:
        logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    if qual != "homepage":
        search = f"{search} {qual}"
    BUTTONS[key] = search
    files, offset, total_results = await get_search_results(chat_id, search, offset=0, filter=True)
    if not files:
        await query.answer("🚫 ɴᴏ ꜰɪʟᴇꜱ ᴡᴇʀᴇ ꜰᴏᴜɴᴅ 🚫", show_alert=True)
        return
    temp.GETALL[key] = files
    settings = await get_settings(message.chat.id)
    if settings.get('button'):
        btn = [
            [
                InlineKeyboardButton(text=f"{get_size(file.file_size)} ≽ " + clean_filename(file.file_name), callback_data=f'file#{file.file_id}')
            ]
            for file in files
        ]
        btn.insert(0,
                   [
                       InlineKeyboardButton(f'ǫᴜᴀʟɪᴛʏ', callback_data=f"qualities#{key}"),
                       InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}"),
                       InlineKeyboardButton("sᴇᴀsᴏɴ",  callback_data=f"seasons#{key}")
                   ]
                   )
        btn.insert(0,
                   [
                       InlineKeyboardButton("📥 sᴇɴᴅ ᴀʟʟ ꜰɪʟᴇs 📥", callback_data=f"sendfiles#{key}")
                   ])
    else:
        btn = []
        btn.insert(0,
                   [
                       InlineKeyboardButton(f'ǫᴜᴀʟɪᴛʏ', callback_data=f"qualities#{key}"),
                       InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}"),
                       InlineKeyboardButton("sᴇᴀsᴏɴ",  callback_data=f"seasons#{key}")
                   ]
                   )
        btn.insert(0,
                   [
                       InlineKeyboardButton("📥 sᴇɴᴅ ᴀʟʟ ꜰɪʟᴇs 📥", callback_data=f"sendfiles#{key}")
                   ])
    if offset != "":
        try:
            if settings['max_btn']:
                btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{offset}")])
            else:
                btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_BTNS))}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{offset}")])
        except KeyError:
            await save_group_settings(query.message.chat.id, 'max_btn', True)
            btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{offset}")])
    else:
        btn.append([InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="pages")])

    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - \
            timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(
                curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        title = clean_search_text(search)
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, title, offset=1)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        except (MessageNotModified, MessageIdInvalid) as _ignored:
            logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    else:
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except (MessageNotModified, MessageIdInvalid) as _ignored:
            logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    await query.answer()

@Client.on_callback_query(filters.regex(r"^languages#"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    try:
        if int(query.from_user.id) not in [query.message.reply_to_message.from_user.id, 0]:
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    except Exception as _ignored:
        logging.getLogger(__name__).debug("Ignored error: %r", _ignored)

    _, key = query.data.split("#")
    search = FRESH.get(key)
    if not search:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    search = search.replace(' ', '_')

    items = list(LANGUAGES.items())
    btn = []

    for i in range(0, len(items), 2):
        name1, code1 = items[i]
        row = [InlineKeyboardButton(
            text=name1, callback_data=f"fl#{code1}#{key}")]
        if i + 1 < len(items):
            name2, code2 = items[i + 1]
            row.append(InlineKeyboardButton(
                text=name2, callback_data=f"fl#{code2}#{key}"))
        btn.append(row)

    btn.insert(0, [InlineKeyboardButton(text="⇊ ꜱᴇʟᴇᴄᴛ ʟᴀɴɢᴜᴀɢᴇ ⇊", callback_data="ident")])
    btn.append([InlineKeyboardButton(text="⋞ ʙᴀᴄᴋ ᴛᴏ ꜰɪʟᴇs", callback_data=f"fl#homepage#{key}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^fl#"))
async def filter_languages_cb_handler(client: Client, query: CallbackQuery):
    _, lang, key = query.data.split("#")
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    search = FRESH.get(key)
    if not search:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    search = search.replace("_", " ")
    baal = lang in search
    if baal:
        search = search.replace(lang, "")
    else:
        search = search
    req = query.from_user.id
    chat_id = query.message.chat.id
    message = query.message
    try:
        if int(query.from_user.id) not in [query.message.reply_to_message.from_user.id, 0]:
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True,)
    except Exception as _ignored:
        logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    if lang != "homepage":
        search = f"{search} {lang}"
    BUTTONS[key] = search
    files, offset, total_results = await get_search_results(chat_id, search, offset=0, filter=True)
    if not files:
        await query.answer("🚫 ɴᴏ ꜰɪʟᴇꜱ ᴡᴇʀᴇ ꜰᴏᴜɴᴅ 🚫", show_alert=1)
        return
    temp.GETALL[key] = files
    settings = await get_settings(message.chat.id)
    if settings.get('button'):
        btn = [
            [
                InlineKeyboardButton(text=f"{get_size(file.file_size)} ≽ " + clean_filename(file.file_name), callback_data=f'file#{file.file_id}')
            ]
            for file in files
        ]
        btn.insert(0,
                   [
                       InlineKeyboardButton(f'ǫᴜᴀʟɪᴛʏ', callback_data=f"qualities#{key}"),
                       InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}"),
                       InlineKeyboardButton("sᴇᴀsᴏɴ",  callback_data=f"seasons#{key}")
                   ]
                   )
        btn.insert(0,
                   [
                       InlineKeyboardButton("📥 sᴇɴᴅ ᴀʟʟ ꜰɪʟᴇs 📥", callback_data=f"sendfiles#{key}")
                   ]
                   )
    else:
        btn = []
        btn.insert(0,
                   [
                       InlineKeyboardButton(f'ǫᴜᴀʟɪᴛʏ', callback_data=f"qualities#{key}"),
                       InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}"),
                       InlineKeyboardButton("sᴇᴀsᴏɴ",  callback_data=f"seasons#{key}")
                   ])
        btn.insert(0,
                   [
                       InlineKeyboardButton("📥 sᴇɴᴅ ᴀʟʟ ꜰɪʟᴇs 📥", callback_data=f"sendfiles#{key}")
                   ])
    if offset != "":
        try:
            if settings['max_btn']:
                btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{offset}")])
            else:
                btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_BTNS))}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{offset}")])
        except KeyError:
            await save_group_settings(query.message.chat.id, 'max_btn', True)
            btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{offset}")])
    else:
        btn.append([InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="pages")])
    if not settings["button"]:
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - \
            timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(
                curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        title = clean_search_text(search)
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, title, offset=1)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        except (MessageNotModified, MessageIdInvalid) as _ignored:
            logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    else:
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except (MessageNotModified, MessageIdInvalid) as _ignored:
            logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    await query.answer()

@Client.on_callback_query(filters.regex(r"^seasons#"))
async def seasons_cb_handler(client: Client, query: CallbackQuery):
    try:
        if int(query.from_user.id) not in [query.message.reply_to_message.from_user.id, 0]:
            return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    except Exception as _ignored:
        logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    _, key = query.data.split("#")
    search = FRESH.get(key)
    if not search:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    search = search.replace(" ", "_")
    req = query.from_user.id
    offset = 0
    btn: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(SEASONS) - 1, 2):
        btn.append([
            InlineKeyboardButton(f"sᴇᴀꜱᴏɴ {SEASONS[i][1:]}", callback_data=f"fs#{SEASONS[i].lower()}#{key}"),
            InlineKeyboardButton(f"sᴇᴀꜱᴏɴ {SEASONS[i+1][1:]}", callback_data=f"fs#{SEASONS[i+1].lower()}#{key}")
        ])

    btn.insert(
        0,
        [InlineKeyboardButton("⇊ ꜱᴇʟᴇᴄᴛ ꜱᴇᴀꜱᴏɴ ⇊", callback_data="ident")],
    )
    btn.append([InlineKeyboardButton(text="⋞ ʙᴀᴄᴋ ᴛᴏ ꜰɪʟᴇs", callback_data=f"next_{req}_{key}_{offset}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))
    await query.answer()

@Client.on_callback_query(filters.regex(r"^fs#"))
async def filter_seasons_cb_handler(client: Client, query: CallbackQuery):
    _, season_tag, key = query.data.split("#")
    search = FRESH.get(key)
    if not search:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    search = search.replace("_", " ")
    season_tag = season_tag.lower()
    if season_tag == "homepage":
        search_final = search
        query_input = search_final
    else:
        season_number = int(season_tag[1:])
        query_input = generate_season_variations(search, season_number)
        search_final = query_input[0] if query_input else search

    BUTTONS[key] = search_final
    try:
        if int(query.from_user.id) not in [query.message.reply_to_message.from_user.id, 0]:
            return await query.answer("⚠️ ɴᴏᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ", show_alert=True)
    except Exception as _ignored:
        logging.getLogger(__name__).debug("Ignored error: %r", _ignored)

    chat_id = query.message.chat.id
    req = query.from_user.id
    files, n_offset, total_results = await get_search_results(chat_id, query_input, offset=0, filter=True)
    if not files:
        BUTTONS[key] = None
        return await query.answer("🚫 ɴᴏ ꜰɪʟᴇꜱ ꜰᴏᴜɴᴅ 🚫", show_alert=True)

    temp.GETALL[key] = files
    settings = await get_settings(chat_id)
    btn: list[list[InlineKeyboardButton]] = []
    if settings.get("button"):
        btn.extend(
            [
                [
                    InlineKeyboardButton(text=f"{get_size(f.file_size)} ≽ " + clean_filename(f.file_name), callback_data=f"file#{f.file_id}")
                ]
                for f in files
            ]
        )
    btn.insert(
        0,
        [
            InlineKeyboardButton("ǫᴜᴀʟɪᴛʏ", callback_data=f"qualities#{key}"),
            InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}"),
            InlineKeyboardButton("sᴇᴀsᴏɴ", callback_data=f"seasons#{key}"),
        ],
    )
    btn.insert(
        0,
        [
            InlineKeyboardButton("📥 sᴇɴᴅ ᴀʟʟ ꜰɪʟᴇs 📥", callback_data=f"sendfiles#{key}"),
        ],
    )
    if n_offset != "":
        try:
            if settings['max_btn']:
                btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{n_offset}")])
            else:
                btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/int(MAX_BTNS))}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{n_offset}")])
        except KeyError:
            await save_group_settings(query.message.chat.id, 'max_btn', True)
            btn.append([InlineKeyboardButton(text=f"1/{math.ceil(int(total_results)/10)}", callback_data="pages"), InlineKeyboardButton(text="ɴᴇxᴛ ⋟", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        n_offset = 0
        btn.append([InlineKeyboardButton("🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="pages")])

    if not settings.get("button"):
        curr_time = datetime.now(pytz.timezone("Asia/Kolkata")).time()
        time_difference = timedelta(
            hours=curr_time.hour,
            minutes=curr_time.minute,
            seconds=curr_time.second + curr_time.microsecond / 1_000_000,
        )
        remaining_seconds = f"{time_difference.total_seconds():.2f}"
        title = clean_search_text(search_final)
        cap = await get_cap(settings, remaining_seconds, files, query, total_results, title, offset=1)
        try:
            await query.message.edit_text(
                text=cap,
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True,
            )
        except (MessageNotModified, MessageIdInvalid) as _ignored:
            logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    else:
        try:
            await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))
        except (MessageNotModified, MessageIdInvalid) as _ignored:
            logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
    await query.answer()

