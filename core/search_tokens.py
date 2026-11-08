"""Token based search: lets MongoDB use a multikey index instead of scanning with $regex."""
import re

_SPLIT = re.compile(r"[^0-9a-zÀ-￿]+")


def make_tokens(text):
    """'Avengers.Endgame.2019.1080p.WEB-DL' -> ['avengers','endgame','2019','1080p','web','dl']"""
    if not text:
        return []
    seen = []
    for t in _SPLIT.split(str(text).lower()):
        if t and t not in seen:
            seen.append(t)
    return seen[:64]


def build_token_filter(query):
    """Mongo filter for a user query, or None if the query has no usable words.

    one word   -> exact token   (same as the old whole-word regex)
    many words -> every word must be the *start* of some token (anchored regex, index friendly)
    """
    words = make_tokens(query)
    if not words:
        return None
    if len(words) == 1:
        return {"tokens": words[0]}
    return {"tokens": {"$all": [re.compile("^" + re.escape(w)) for w in words]}}
