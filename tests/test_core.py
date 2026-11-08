import hashlib
import hmac
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config_check import find_problems
from core.payments_razorpay import build_link_payload, parse_paid_event, verify_webhook
from core.ratelimit import RateLimiter
from core.search_tokens import build_token_filter, make_tokens
from core.signed_links import derive_secret, sign, verify
from core.text_style import apply_to_class, plainify
from core.ttl_cache import TTLDict
from core import fuzzy


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t


def test_ttl_expiry_and_cap():
    c = Clock(); d = TTLDict(ttl=10, maxsize=3, clock=c)
    d["a"] = 1; assert d["a"] == 1 and "a" in d
    c.t = 11
    assert "a" not in d and d.get("a") is None and len(d) == 0
    for i in range(5): d[i] = i
    assert len(d) == 3 and 0 not in d and 4 in d       # oldest evicted


def test_ttl_dict_api_used_by_bot():
    d = TTLDict(ttl=100, maxsize=10)
    d.update({1: {"x": 1}}); assert d.get(1) == {"x": 1}
    assert d.pop(1) == {"x": 1} and d.get(1, 0) == 0


def test_tokens():
    assert make_tokens("Avengers.Endgame.2019.1080p.WEB-DL") == ["avengers", "endgame", "2019", "1080p", "web", "dl"]
    assert make_tokens("") == [] and make_tokens(None) == []
    assert make_tokens("a a A") == ["a"]


def test_token_filter():
    assert build_token_filter("Avengers") == {"tokens": "avengers"}
    f = build_token_filter("avengers end game")["tokens"]["$all"]
    assert [p.pattern for p in f] == ["^avengers", "^end", "^game"]
    assert f[0].match("avengers") and f[1].match("endgame") and not f[1].match("blend")
    assert build_token_filter("   !!! ") is None
    assert build_token_filter("a.b")["tokens"]["$all"][0].pattern == "^a"   # separators split words


def test_signed_links():
    s = derive_secret("", "bot-token")
    exp, sig = sign(s, 123, "abc123", 60, now=1000)
    assert verify(s, 123, "abc123", exp, sig, now=1030)
    assert not verify(s, 123, "abc123", exp, sig, now=1100)         # expired
    assert not verify(s, 124, "abc123", exp, sig, now=1030)         # other message
    assert not verify(s, 123, "zzz999", exp, sig, now=1030)         # other hash
    assert not verify(s, 123, "abc123", exp + 1, sig, now=1030)     # tampered expiry
    assert not verify(s, 123, "abc123", "x", sig) and not verify(s, 123, "abc123", exp, None)
    assert not verify(derive_secret("other", "t"), 123, "abc123", exp, sig, now=1030)


def test_rate_limiter():
    c = Clock(); r = RateLimiter(3, 10, clock=c)
    assert [r.allow(1) for _ in range(4)] == [True, True, True, False]
    assert r.allow(2)                                   # other user unaffected
    c.t = 5; assert not r.allow(1)                      # still blocked
    c.t = 11; assert r.allow(1)                         # block expired


def test_config_check():
    env = {"API_ID": "abc", "BOT_TOKEN": "", "DATABASE_URI": "x"}
    p = find_problems(env, ["API_ID", "BOT_TOKEN", "DATABASE_URI", "LOG_CHANNEL"], ["API_ID"])
    assert "BOT_TOKEN is missing" in p and "LOG_CHANNEL is missing" in p
    assert any("API_ID must be a number" in x for x in p)
    assert find_problems({"A": "1"}, ["A"], ["A"]) == []


def test_razorpay_webhook():
    body = json.dumps({"event": "payment_link.paid", "payload": {
        "payment_link": {"entity": {"notes": {"user_id": "42", "plan": "30"}, "amount_paid": 4900}},
        "payment": {"entity": {"id": "pay_1", "amount": 4900}}}}).encode()
    sig = hmac.new(b"sec", body, hashlib.sha256).hexdigest()
    assert verify_webhook("sec", body, sig)
    assert not verify_webhook("sec", body + b" ", sig) and not verify_webhook("", body, sig) and not verify_webhook("sec", body, None)
    assert parse_paid_event(body) == ("pay_1", 42, "30", 4900)
    assert parse_paid_event(b"{bad") is None
    assert parse_paid_event(json.dumps({"event": "payment.failed"}).encode()) is None
    pl = build_link_payload(42, "30", 49, "30 days")
    assert pl["amount"] == 4900 and pl["notes"] == {"user_id": "42", "plan": "30"}


def test_plainify_and_overrides():
    assert plainify("ɪ ᴀᴍ ꜱᴇᴀʀᴄʜ 𝖲𝗁𝖺𝗋𝖾 𝟹 <b>{0}</b>") == "i am search Share 3 <b>{0}</b>"
    class S: A = "ᴀʙᴄ {x}"; B = "keep"; _c = "ᴀ"
    apply_to_class(S, overrides={"B": "ᴅᴇ"}, plain=True)
    assert (S.A, S.B, S._c) == ("abc {x}", "de", "ᴀ")


def test_fuzzy_fallback_scores():
    assert fuzzy.ratio("avengers", "avengers") == 100
    assert fuzzy.token_sort_ratio("end game", "game end") == 100
    assert fuzzy.ratio("avngers", "avengers") > 80 > fuzzy.ratio("avngers", "titanic")
