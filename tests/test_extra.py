import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.alerts import TelegramErrorHandler
from core.hinglish import HINGLISH
from Script import script


def test_hinglish_keeps_placeholders():
    for name, text in HINGLISH.items():
        original = getattr(script, name)
        assert text.count("{}") == original.count("{}"), name
        text.format(*["x"] * text.count("{}"))   # must not raise


def test_plain_and_hinglish_modes_load_and_format():
    code = ("from Script import script; "
            "print(script.START_TXT.format('a','b','c','d')); "
            "print(script.I_CUDNT.format('x'))")
    for env in ({"UI_PLAIN": "true"}, {"UI_LANG": "hinglish"}, {"UI_LANG": "hinglish", "UI_PLAIN": "1"}):
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**os.environ, **env, "PYTHONPATH": str(ROOT)},
                             capture_output=True, text=True, check=True).stdout
        assert "a, b" in out
        if env.get("UI_PLAIN"):
            assert not any(0x1D5A0 <= ord(c) <= 0x1D7FF or c in "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘʀꜱᴛᴜᴠᴡʏᴢ" for c in out), out


def test_alert_handler_sends_once_and_escapes():
    async def main():
        sent = []

        async def send(text):
            sent.append(text)
        h = TelegramErrorHandler(send, asyncio.get_running_loop())
        lg = logging.getLogger("tests.alerts"); lg.propagate = False; lg.addHandler(h)
        try:
            1 / 0
        except ZeroDivisionError:
            lg.exception("boom <b>")
        for _ in range(3):
            lg.error("same error")                  # identical call site -> de-duplicated
        lg.warning("below threshold")               # WARNING is below ERROR
        await asyncio.sleep(0.05)
        return sent
    sent = asyncio.run(main())
    assert len(sent) == 2
    assert "ZeroDivisionError" in sent[0] and "&lt;b&gt;" in sent[0] and "<b>boom" not in sent[0]


def test_alert_handler_is_rate_limited():
    async def main():
        sent = []

        async def send(text):
            sent.append(text)
        h = TelegramErrorHandler(send, asyncio.get_running_loop(), max_per_minute=3)
        lg = logging.getLogger("tests.alerts2"); lg.propagate = False; lg.addHandler(h)
        for i in range(10):
            lg.error("distinct %s", i)              # same line but different message -> not deduped
        await asyncio.sleep(0.05)
        return sent
    assert len(asyncio.run(main())) == 3
