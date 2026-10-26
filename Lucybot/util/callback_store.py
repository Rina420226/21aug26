"""Keep callback_data under Telegram's 64-byte limit when it carries user text (filter keywords)."""
import hashlib

_STORE = {}


def fit_keyword(keyword: str, prefix: str) -> str:
    """Return the keyword itself when prefix+keyword fits, else a short stored reference."""
    if len((prefix + keyword).encode("utf-8")) <= 64 and ":" not in keyword and "#" not in keyword:
        return keyword
    ref = "ref" + hashlib.sha1(keyword.encode("utf-8")).hexdigest()[:16]
    _STORE[ref] = keyword
    return ref


def resolve_keyword(value: str) -> str:
    return _STORE.get(value, value)
