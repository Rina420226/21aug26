import time
from telegram import Bot
from services.database import deletion_jobs_col
from utils.logging import logger

def schedule_deletion(chat_id: int, message_id: int, delay_seconds: int):
    delete_at = int(time.time()) + delay_seconds
    deletion_jobs_col.insert_one({
        "chat_id": chat_id,
        "message_id": message_id,
        "delete_at": delete_at
    })

async def process_deletion_jobs(bot: Bot):
    now = int(time.time())
    jobs = list(deletion_jobs_col.find({"delete_at": {"$lte": now}}))
    for job in jobs:
        try:
            await bot.delete_message(chat_id=job["chat_id"], message_id=job["message_id"])
        except Exception:
            pass
        finally:
            deletion_jobs_col.delete_one({"_id": job["_id"]})
          
