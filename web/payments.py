"""Razorpay webhook: verifies the signature, then grants premium exactly once per payment."""
import datetime
import logging
from aiohttp import web
from info import RAZORPAY_ENABLED, RAZORPAY_PLANS, RAZORPAY_WEBHOOK_SECRET, PREMIUM_LOGS
from core.payments_razorpay import verify_webhook, parse_paid_event
from database.users_chats_db import db
from . import techifybots

logger = logging.getLogger(__name__)


async def grant_premium(user_id: int, days: int):
    """Extend (stack) premium by `days`. Returns the new expiry."""
    now = datetime.datetime.now()
    data = await db.get_user(user_id)
    cur = data.get("expiry_time") if data else None
    if isinstance(cur, datetime.datetime) and cur.tzinfo is not None:
        cur = cur.replace(tzinfo=None)
    base = cur if isinstance(cur, datetime.datetime) and cur > now else now
    expiry = base + datetime.timedelta(days=days)
    await db.update_user({"id": user_id, "expiry_time": expiry})
    return expiry


async def razorpay_webhook(request: web.Request):
    if not RAZORPAY_ENABLED:
        raise web.HTTPNotFound()
    raw = await request.read()
    if not verify_webhook(RAZORPAY_WEBHOOK_SECRET, raw, request.headers.get("X-Razorpay-Signature")):
        logger.warning("Razorpay webhook with a bad signature from %s", request.remote)
        return web.Response(status=400, text="bad signature")
    event = parse_paid_event(raw)
    if not event:
        return web.Response(text="ignored")          # other event types are fine, just acknowledge
    payment_id, user_id, plan, paid = event
    days = int(plan) if plan.isdigit() else 0
    price = RAZORPAY_PLANS.get(days)
    if not price or paid < price * 100:
        logger.error("Razorpay payment %s: plan/amount mismatch (plan=%s paid=%s)", payment_id, plan, paid)
        return web.Response(text="mismatch")          # 200 so Razorpay does not retry; admins see the log alert
    if not await db.claim_payment(payment_id, user_id, days, paid):
        return web.Response(text="duplicate")         # already processed (Razorpay retries webhooks)
    try:
        expiry = await grant_premium(user_id, days)
    except Exception:
        logger.exception("Could not grant premium for payment %s", payment_id)
        await db.release_payment(payment_id)
        return web.Response(status=500, text="retry")  # Razorpay will retry later
    try:
        await techifybots.send_message(user_id, f"✅ Payment received. Premium active for {days} days.\nExpires: {expiry:%d-%m-%Y %I:%M %p}")
        await techifybots.send_message(PREMIUM_LOGS, f"#Purchase_Razorpay\n\nUser: <code>{user_id}</code>\nPlan: {days} days\nPaid: ₹{paid / 100:.2f}\nPayment: <code>{payment_id}</code>")
    except Exception:
        logger.warning("Premium granted to %s but notification failed", user_id, exc_info=True)
    return web.Response(text="ok")
