import logging
"""Per-user flood protection. Runs before every other handler (group -5)."""
from pyrogram import Client, filters, StopPropagation
from info import ADMINS, OWNER, RATE_LIMIT, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW
from core.ratelimit import RateLimiter
from core.ttl_cache import TTLDict

_EXEMPT = {int(a) for a in ADMINS if str(a).lstrip("-").isdigit()} | {int(OWNER)}
limiter = RateLimiter(RATE_LIMIT_MAX, RATE_LIMIT_WINDOW)
_notified = TTLDict(ttl=RATE_LIMIT_WINDOW, maxsize=10000)


def _blocked(user):
    if not RATE_LIMIT or user is None or user.is_bot or user.id in _EXEMPT:
        return False
    return not limiter.allow(user.id)


@Client.on_message(filters.incoming, group=-5)
async def throttle_messages(client, message):
    if _blocked(message.from_user):
        uid = message.from_user.id
        if uid not in _notified and message.chat.type.name == "PRIVATE":
            _notified[uid] = True
            try:
                await message.reply_text(f"⏳ Too many requests. Please wait {RATE_LIMIT_WINDOW} seconds and try again.", quote=True)
            except Exception as _ignored:
                logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
        raise StopPropagation


@Client.on_callback_query(group=-5)
async def throttle_callbacks(client, query):
    if _blocked(query.from_user):
        try:
            await query.answer("⏳ Slow down a little.", show_alert=False)
        except Exception as _ignored:
            logging.getLogger(__name__).debug("Ignored error: %r", _ignored)
        raise StopPropagation
