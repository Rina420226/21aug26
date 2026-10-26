"""Shared inline buttons for file delivery: direct download and online watch are separate buttons."""
from pyrogram.types import InlineKeyboardButton
from database.ia_filterdb import unpack_new_file_id


def compact_file_id(file_id: str) -> str:
    # Raw Bot API file_ids are longer than Telegram's 64-byte callback_data limit.
    # The compact (legacy) id is short and send_cached_media accepts it.
    if len(file_id) > 40:
        return unpack_new_file_id(file_id)[0]
    return file_id


def web_delivery_rows(file_id: str) -> list:
    fid = compact_file_id(file_id)
    return [[
        InlineKeyboardButton("🚀 Direct Download", callback_data=f"gdl:{fid}"),
        InlineKeyboardButton("🖥️ Watch Online", callback_data=f"gwt:{fid}"),
    ]]
