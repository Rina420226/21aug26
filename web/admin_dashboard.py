"""Read-only admin dashboard: /admin (HTML) and /admin/api/stats (JSON). Disabled unless ADMIN_DASH_TOKEN is set."""
import hashlib
import hmac
import html
import time
from aiohttp import web
from info import ADMIN_DASH_TOKEN, BOT_TOKEN, MULTIPLE_DB, HAS_SSL
from database.users_chats_db import db
from database.ia_filterdb import Media, Media2
from database import jobs_db
from utils import temp, get_readable_time
from core.ratelimit import RateLimiter

_login_limiter = RateLimiter(5, 60)


def _session_value():
    return hmac.new(BOT_TOKEN.encode(), b"admin-dash:" + ADMIN_DASH_TOKEN.encode(), hashlib.sha256).hexdigest()


def _authed(request):
    if not ADMIN_DASH_TOKEN:
        return False
    cookie = request.cookies.get("adm", "")
    if cookie and hmac.compare_digest(cookie, _session_value()):
        return True
    auth = request.headers.get("Authorization", "")
    return auth.startswith("Bearer ") and hmac.compare_digest(auth[7:], ADMIN_DASH_TOKEN)


async def collect_stats():
    files = await Media.count_documents({})
    if MULTIPLE_DB:
        files += await Media2.count_documents({})
    jobs = await jobs_db.list_unfinished()
    return {
        "users": await db.total_users_count(),
        "groups": await db.total_chat_count(),
        "premium_users": await db.all_premium_users(),
        "files": files,
        "banned_users": len(temp.BANNED_USERS),
        "banned_chats": len(temp.BANNED_CHATS),
        "uptime": get_readable_time(time.time() - temp.START_TIME),
        "indexed_search": bool(temp.SEARCH_INDEX_READY),
        "unfinished_jobs": [{"id": j["_id"], "kind": j.get("kind"), "status": j.get("status"), "current": j.get("current", j.get("done"))} for j in jobs],
    }


_LOGIN = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Admin</title>
<style>body{font:16px system-ui;margin:0;display:grid;place-items:center;min-height:100vh;background:#0f1115;color:#e8eaed}
form{display:flex;gap:8px;flex-direction:column;width:min(320px,90vw)}input,button{padding:12px;border-radius:8px;border:1px solid #333;font:inherit}
input{background:#1a1d24;color:inherit}button{background:#3b82f6;color:#fff;border:0;cursor:pointer}</style>
<form method=post action=/admin/login><b>Admin dashboard</b><input type=password name=key placeholder="Access key" autofocus required><button>Sign in</button>%s</form>"""

_PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><meta http-equiv=refresh content=30><title>Bot dashboard</title>
<style>:root{color-scheme:light dark}body{font:16px system-ui;margin:0;padding:16px;max-width:900px;margin:auto}
h1{font-size:20px}.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.c{padding:14px;border-radius:12px;border:1px solid #8883}.c b{display:block;font-size:26px}.c span{opacity:.7;font-size:13px}
table{width:100%%;border-collapse:collapse;margin-top:8px}td,th{padding:6px;border-bottom:1px solid #8883;text-align:left;font-size:14px}</style>
<h1>Bot dashboard</h1><div class=g>%s</div><h1>Unfinished jobs</h1>%s<p><small>Auto-refreshes every 30 s.</small></p>"""


async def dashboard_stats(request):
    if not _authed(request):
        raise web.HTTPNotFound()
    return web.json_response(await collect_stats())


async def dashboard_page(request):
    if not ADMIN_DASH_TOKEN:
        raise web.HTTPNotFound()
    if not _authed(request):
        return web.Response(text=_LOGIN % "", content_type="text/html")
    s = await collect_stats()
    cards = "".join(f"<div class=c><b>{html.escape(str(v))}</b><span>{k.replace('_', ' ')}</span></div>"
                    for k, v in s.items() if k != "unfinished_jobs")
    if s["unfinished_jobs"]:
        rows = "".join(f"<tr><td>{html.escape(str(j['kind']))}</td><td>{html.escape(str(j['id']))}</td><td>{html.escape(str(j['status']))}</td><td>{html.escape(str(j['current']))}</td></tr>" for j in s["unfinished_jobs"])
        jobs = f"<table><tr><th>Kind<th>Job<th>Status<th>Progress</tr>{rows}</table><p><small>Resume from Telegram with /resume_jobs.</small></p>"
    else:
        jobs = "<p>None.</p>"
    return web.Response(text=_PAGE % (cards, jobs), content_type="text/html")


async def dashboard_login(request):
    if not ADMIN_DASH_TOKEN:
        raise web.HTTPNotFound()
    if not _login_limiter.allow(request.remote or "?"):
        return web.Response(status=429, text="Too many attempts. Wait a minute.")
    form = await request.post()
    if not hmac.compare_digest(str(form.get("key", "")), ADMIN_DASH_TOKEN):
        return web.Response(text=_LOGIN % "<small style='color:#f87171'>Wrong key</small>", content_type="text/html", status=401)
    resp = web.HTTPFound("/admin")
    resp.set_cookie("adm", _session_value(), httponly=True, secure=bool(HAS_SSL), samesite="Strict", max_age=86400, path="/")
    raise resp
