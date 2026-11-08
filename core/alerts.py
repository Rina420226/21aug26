"""Send ERROR/CRITICAL logs (with traceback) to a Telegram chat, de-duplicated and rate limited."""
import asyncio
import hashlib
import html
import logging
import time


class TelegramErrorHandler(logging.Handler):
    def __init__(self, send, loop, level=logging.ERROR, dedupe_seconds=600, max_per_minute=10, max_len=3500):
        super().__init__(level)
        self._send = send            # async callable(text)
        self._loop = loop
        self._dedupe = dedupe_seconds
        self._max_pm = max_per_minute
        self._max_len = max_len
        self._seen = {}
        self._sent_times = []
        self._busy = False           # prevents alert -> error -> alert loops

    def emit(self, record):
        try:
            if self._busy or record.name.startswith(("pyrogram", "asyncio.alerts")):
                return
            text = self.format_text(record)
            key = hashlib.md5(f"{record.name}|{record.pathname}|{record.lineno}|{record.getMessage()[:80]}".encode()).hexdigest()
            now = time.time()
            if now - self._seen.get(key, 0) < self._dedupe:
                return
            self._seen[key] = now
            self._sent_times = [t for t in self._sent_times if now - t < 60]
            if len(self._sent_times) >= self._max_pm:
                return
            self._sent_times.append(now)
            self._loop.call_soon_threadsafe(lambda: self._loop.create_task(self._deliver(text)))
        except Exception:
            pass

    def format_text(self, record):
        body = self.format(record) if self.formatter else record.getMessage()
        if record.exc_info:
            body = f"{record.getMessage()}\n{logging.Formatter().formatException(record.exc_info)}"
        body = html.escape(body)[-self._max_len:]
        return f"<b>🚨 {record.levelname}</b> <code>{html.escape(record.name)}</code>\n<pre>{body}</pre>"

    async def _deliver(self, text):
        self._busy = True
        try:
            await self._send(text)
        except Exception:
            pass
        finally:
            self._busy = False


def install(send, loop, **kw):
    """Attach the handler to the root logger and to asyncio's unhandled-exception hook."""
    handler = TelegramErrorHandler(send, loop, **kw)
    logging.getLogger().addHandler(handler)

    def _loop_exc(lp, ctx):
        exc = ctx.get("exception")
        logging.getLogger("asyncio.unhandled").error(
            ctx.get("message", "Unhandled asyncio error"), exc_info=(type(exc), exc, exc.__traceback__) if exc else None)
    loop.set_exception_handler(_loop_exc)
    return handler
