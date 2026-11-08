# Upgrades in this version

Everything is optional / backwards compatible. New environment variables (all have safe defaults):

| Variable | Default | What it does |
|---|---|---|
| `INDEXED_SEARCH` | `True` | Token-index search. On first start the bot backfills a `tokens` field for every file in the background (old regex search is used until it finishes). Set `False` to keep the old search. |
| `COUNT_CACHE_TTL` | `120` | Seconds to cache "total results" per query. |
| `STREAM_SIGNED` | `True` | Stream/download links carry an HMAC signature + expiry. Old plain links stop working - set `False` to keep them. |
| `STREAM_SECRET` | *(from BOT_TOKEN)* | Secret used to sign links. |
| `STREAM_LINK_TTL` | `21600` | Link lifetime in seconds (6 h). |
| `RATE_LIMIT`, `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW` | `True`, `8`, `10` | Max events per user per window. Admins are exempt. |
| `ERROR_ALERTS` | `True` | Send ERROR/CRITICAL logs with traceback to `LOG_CHANNEL` (de-duplicated, max 10/min). |
| `LOG_LEVEL` | `INFO` | Set `DEBUG` to also see the errors that used to be silently ignored. |
| `UI_PLAIN` | `False` | Replace small-caps/fancy letters in `Script.py` texts with normal letters. |
| `UI_LANG` | `en` | `hinglish` switches the most common messages to Hinglish. |
| `DEDUPE_ON_SAVE` | `True` | Skip files whose Telegram `file_unique_id` is already indexed. |
| `ADMIN_DASH_TOKEN` | *(empty = off)* | Enables the read-only dashboard at `/admin`. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | *(empty = off)* | Auto-premium via UPI/card. Webhook URL: `https://<your-domain>/webhook/razorpay` (event: `payment_link.paid`). |
| `RAZORPAY_PLANS` | `7:29,30:79,90:199` | `days:price_in_INR` pairs. |
| `SHORTENER_API*` | *(empty)* | The hardcoded key was removed - set these in the environment. |

New admin commands: `/resume_jobs`, `/dedupe` (dry run) / `/dedupe confirm`, `/takedown <words>`, `/takedown_list`, `/untakedown <id>`.
New user command: `/dmca <what to remove>`.

Development: `pip install -r requirements-dev.txt && ruff check . && pytest -q tests`.
