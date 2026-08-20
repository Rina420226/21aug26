from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from config import Config
from services.database import setup_indexes
from services.scheduler import process_deletion_jobs
from handlers.search import handle_search
from handlers.callback import handle_callback
from handlers.admin import admin_panel, handle_admin_callback
from utils.logging import logger

async def auto_delete_task(context):
    await process_deletion_jobs(context.bot)

def main():
    logger.info("Setting up database indexes...")
    setup_indexes()

    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    # Job Queue for reliable persistent auto-deletions (runs every 10s)
    app.job_queue.run_repeating(auto_delete_task, interval=10, first=5)

    # Command Handlers
    app.add_handler(CommandHandler("admin", admin_panel))

    # Search Handler (Group searches)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_search))

    # Callback Query Handlers
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^adm_"))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Movie Search Bot is operational.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
  
