"""Shared, bounded caches for search results / pagination.

Lives outside plugins/ on purpose: plugin modules can be loaded twice by the bot's plugin loader,
which would give each copy its own (separate) dicts. A plain module is imported exactly once."""
from core.ttl_cache import TTLDict


def _cache():
    # entries expire after 2h; the oldest are dropped once 3000 are stored
    return TTLDict(ttl=7200, maxsize=3000)


BUTTON = _cache()
BUTTONS = _cache()
FRESH = _cache()
BUTTONS0 = _cache()
BUTTONS1 = _cache()
BUTTONS2 = _cache()
SPELL_CHECK = _cache()
DYM = _cache()  # "{chat_id}-{msg_id}" -> list of suggested titles
