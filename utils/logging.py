import logging
from telegram import Bot
from config import Config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("MovieBot")

async def log_to_telegram(bot: Bot, channel_id: int, message: str):
    if not channel_id:
        return
    try:
        await bot.send_message(chat_id=channel_id, text=message, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed sending log to channel {channel_id}: {e}")
      
