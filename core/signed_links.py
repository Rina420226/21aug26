"""HMAC signed + expiring stream links (replaces the bare 6 char hash)."""
import base64
import hashlib
import hmac
import time


def derive_secret(explicit, fallback_seed):
    """Use STREAM_SECRET if given, else a stable secret derived from the bot token."""
    seed = explicit or f"stream-link::{fallback_seed}"
    return hashlib.sha256(seed.encode()).digest()


def _mac(secret, msg_id, file_hash, exp):
    msg = f"{int(msg_id)}|{file_hash}|{int(exp)}".encode()
    return base64.urlsafe_b64encode(hmac.new(secret, msg, hashlib.sha256).digest()[:16]).decode().rstrip("=")


def sign(secret, msg_id, file_hash, ttl, now=None):
    exp = int((now if now is not None else time.time()) + ttl)
    return exp, _mac(secret, msg_id, file_hash, exp)


def verify(secret, msg_id, file_hash, exp, sig, now=None):
    try:
        exp = int(exp)
    except (TypeError, ValueError):
        return False
    if not sig or exp < (now if now is not None else time.time()):
        return False
    return hmac.compare_digest(_mac(secret, msg_id, file_hash, exp), str(sig))
