"""Fuzzy scoring: rapidfuzz (fast) -> fuzzywuzzy -> difflib fallback."""
try:  # pragma: no cover - depends on what is installed
    from rapidfuzz import fuzz as _fuzz
    BACKEND = "rapidfuzz"
except Exception:  # pragma: no cover
    try:
        from fuzzywuzzy import fuzz as _fuzz
        BACKEND = "fuzzywuzzy"
    except Exception:
        _fuzz = None
        BACKEND = "difflib"

import difflib


def ratio(a, b):
    if _fuzz is not None:
        return _fuzz.ratio(a, b)
    return round(100 * difflib.SequenceMatcher(None, a, b).ratio())


def token_sort_ratio(a, b):
    if _fuzz is not None:
        return _fuzz.token_sort_ratio(a, b)
    return ratio(" ".join(sorted(a.split())), " ".join(sorted(b.split())))
