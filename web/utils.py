import jinja2
from info import *
import urllib.parse
import logging
import aiohttp
from pyrogram import Client
from typing import Any, Optional
from pyrogram.types import Message
from pyrogram.file_id import FileId
from pyrogram.raw.types.messages import Messages
from .exceptions import FIleNotFound, InvalidHash
from core import signed_links
from . import techifybots

async def parse_file_id(message: "Message") -> Optional[FileId]:
    media = get_media_from_message(message)
    if media:
        return FileId.decode(media.file_id)

async def parse_file_unique_id(message: "Messages") -> Optional[str]:
    media = get_media_from_message(message)
    if media:
        return media.file_unique_id

async def get_file_ids(client: Client, chat_id: int, id: int) -> Optional[FileId]:
    message = await client.get_messages(chat_id, id)
    if message.empty:
        raise FIleNotFound
    media = get_media_from_message(message)
    file_unique_id = await parse_file_unique_id(message)
    file_id = await parse_file_id(message)
    setattr(file_id, "file_size", getattr(media, "file_size", 0))
    setattr(file_id, "mime_type", getattr(media, "mime_type", ""))
    setattr(file_id, "file_name", getattr(media, "file_name", ""))
    setattr(file_id, "unique_id", file_unique_id)
    return file_id

def get_media_from_message(message: "Message") -> Any:
    media_types = (
        "audio",
        "document",
        "photo",
        "sticker",
        "animation",
        "video",
        "voice",
        "video_note",
    )
    for attr in media_types:
        media = getattr(message, attr, None)
        if media:
            return media

def get_hash(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return getattr(media, "file_unique_id", "")[:6]

_SIGN_SECRET = signed_links.derive_secret(STREAM_SECRET, BOT_TOKEN)

def make_query(msg_id, file_hash: str) -> str:
    """Query string for a stream/download link: hash (+ expiry + HMAC signature when STREAM_SIGNED)."""
    if not STREAM_SIGNED:
        return f"hash={file_hash}"
    exp, sig = signed_links.sign(_SIGN_SECRET, msg_id, file_hash, STREAM_LINK_TTL)
    return f"hash={file_hash}&exp={exp}&sig={sig}"

def link_query(media_msg: Message) -> str:
    return make_query(media_msg.id, get_hash(media_msg))

def check_signature(msg_id, file_hash, exp, sig):
    """Reject forged / expired links *before* any Telegram request is made."""
    if STREAM_SIGNED and not signed_links.verify(_SIGN_SECRET, msg_id, file_hash, exp, sig):
        raise InvalidHash

def get_name(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return getattr(media, 'file_name', "")

def get_media_file_size(m):
    media = get_media_from_message(m)
    return getattr(media, "file_size", 0)

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

async def render_page(id, secure_hash, exp=None, sig=None, src=None):
    check_signature(id, secure_hash, exp, sig)
    file = await techifybots.get_messages(int(BIN_CHANNEL), int(id))
    file_data = await get_file_ids(techifybots, int(BIN_CHANNEL), int(id))
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    src = urllib.parse.urljoin(
        URL,
        f"{id}/{urllib.parse.quote_plus(file_data.file_name)}?{make_query(id, secure_hash)}",
    )
    tag = file_data.mime_type.split("/")[0].strip()
    file_size = humanbytes(file_data.file_size)
    template_file = "web/techifybots.html"
    if tag not in ["video", "audio"]:
        async with aiohttp.ClientSession() as s:
            async with s.get(src) as u:
                file_size = humanbytes(int(u.headers.get("Content-Length")))

    with open(template_file) as f:
        template = jinja2.Template(f.read())
    file_name = file_data.file_name.replace("_", " ")
    return template.render(
        file_name=file_name,
        file_url=src,
        file_size=file_size,
        file_unique_id=file_data.unique_id,
    )
