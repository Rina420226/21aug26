"""UPI / card / netbanking premium purchase via Razorpay Payment Links (auto-activates through the webhook)."""
import logging
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import RAZORPAY_ENABLED, RAZORPAY_PLANS, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
from core.payments_razorpay import API, build_link_payload

logger = logging.getLogger(__name__)


async def _show(query, text, buttons):
    markup = InlineKeyboardMarkup(buttons)
    try:
        await query.message.edit_caption(text, reply_markup=markup)
    except Exception:
        await query.message.edit_text(text, reply_markup=markup)


@Client.on_callback_query(filters.regex(r"^rzp_menu$"))
async def rzp_menu(client, query):
    if not RAZORPAY_ENABLED:
        return await query.answer("Online payment is not available right now.", show_alert=True)
    rows = [[InlineKeyboardButton(f"{days} days - ₹{price}", callback_data=f"rzp_{days}")] for days, price in sorted(RAZORPAY_PLANS.items())]
    rows.append([InlineKeyboardButton("⋞ Back", callback_data="buy_info")])
    await _show(query, "<b>💳 Pay with UPI / Card / Netbanking</b>\n\nPremium activates automatically within a minute of payment.\n\nChoose a plan:", rows)


@Client.on_callback_query(filters.regex(r"^rzp_(\d+)$"))
async def rzp_create(client, query):
    if not RAZORPAY_ENABLED:
        return await query.answer("Online payment is not available right now.", show_alert=True)
    days = int(query.matches[0].group(1))
    price = RAZORPAY_PLANS.get(days)
    if not price:
        return await query.answer("Invalid plan.", show_alert=True)
    payload = build_link_payload(query.from_user.id, str(days), price, f"{days} days")
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.post(API, json=payload, auth=aiohttp.BasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) as r:
                data = await r.json()
                if r.status >= 400:
                    logger.error("Razorpay payment link failed: %s %s", r.status, data)
                    return await query.answer("Could not create the payment link. Try again later.", show_alert=True)
    except Exception:
        logger.exception("Razorpay request failed")
        return await query.answer("Payment service is unreachable. Try again later.", show_alert=True)
    await query.answer()
    await client.send_message(
        query.from_user.id,
        f"<b>💳 {days} days premium - ₹{price}</b>\n\nTap Pay, complete the payment, and premium turns on automatically.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Pay now", url=data["short_url"])]]),
    )
