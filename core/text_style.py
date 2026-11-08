"""UI text helpers: optional plain-text mode (small-caps / math-sans -> normal letters) + Hinglish overrides."""

_SMALL_CAPS = {
    "ᴀ": "a", "ʙ": "b", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ꜰ": "f", "ɢ": "g", "ʜ": "h", "ɪ": "i", "ᴊ": "j",
    "ᴋ": "k", "ʟ": "l", "ᴍ": "m", "ɴ": "n", "ᴏ": "o", "ᴘ": "p", "ǫ": "q", "ʀ": "r", "ꜱ": "s", "ᴛ": "t",
    "ᴜ": "u", "ᴠ": "v", "ᴡ": "w", "ʏ": "y", "ᴢ": "z", "ꜱ": "s",
}


def _build_map():
    m = dict(_SMALL_CAPS)
    # Mathematical sans-serif / bold / double-struck digits and letters -> ASCII
    for base, start in (
        (0x1D5A0, "A"), (0x1D5BA, "a"),      # sans upper / lower
        (0x1D5D4, "A"), (0x1D5EE, "a"),      # sans bold
        (0x1D7E2, "0"), (0x1D7EC, "0"),      # sans digits / bold digits
        (0x1D7D8, "0"), (0x1D7F6, "0"),      # double-struck / monospace digits
        (0x1D670, "A"), (0x1D68A, "a"),      # monospace letters
    ):
        n = 10 if start == "0" else 26
        for i in range(n):
            m[chr(base + i)] = chr(ord(start) + i)
    return {ord(k): v for k, v in m.items()}


_MAP = _build_map()


def plainify(text):
    """Convert fancy unicode letters to plain ASCII. Leaves HTML tags and {placeholders} untouched."""
    return text.translate(_MAP) if isinstance(text, str) else text


def apply_to_class(cls, overrides=None, plain=False):
    """Mutate a Script-style class in place: apply overrides, then optionally plainify every str attr."""
    for name, value in list(vars(cls).items()):
        if name.startswith("_") or not isinstance(value, str):
            continue
        if overrides and name in overrides:
            value = overrides[name]
        if plain:
            value = plainify(value)
        setattr(cls, name, value)
