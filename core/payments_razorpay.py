"""Razorpay Payment Links (UPI/cards/netbanking) -> auto premium. No SDK; plain REST + HMAC webhook."""
import hashlib
import hmac
import json

API = "https://api.razorpay.com/v1/payment_links"


def verify_webhook(secret, raw_body, signature):
    """Razorpay signs the *raw* body with HMAC-SHA256(webhook_secret)."""
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def build_link_payload(user_id, plan_key, amount_inr, days_label, callback_url=None):
    payload = {
        "amount": int(amount_inr) * 100,   # paise
        "currency": "INR",
        "accept_partial": False,
        "description": f"Premium {days_label}",
        "reference_id": f"u{user_id}-{plan_key}-{int(__import__('time').time())}",
        "notes": {"user_id": str(user_id), "plan": plan_key},
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
    }
    if callback_url:
        payload["callback_url"] = callback_url
        payload["callback_method"] = "get"
    return payload


def parse_paid_event(raw_body):
    """Return (payment_id, user_id, plan_key, amount_paise) for a paid payment-link event, else None."""
    try:
        data = json.loads(raw_body)
    except Exception:
        return None
    if data.get("event") != "payment_link.paid":
        return None
    try:
        pl = data["payload"]["payment_link"]["entity"]
        pay = data["payload"]["payment"]["entity"]
        notes = pl.get("notes") or {}
        return pay["id"], int(notes["user_id"]), str(notes["plan"]), int(pl.get("amount_paid") or pay.get("amount") or 0)
    except (KeyError, TypeError, ValueError):
        return None
