import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot Credentials
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Databases
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "MovieBotDB")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # External APIs
    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
    SHORTENER_API_KEY = os.getenv("SHORTENER_API_KEY", "")
    SHORTENER_API_URL = os.getenv("SHORTENER_API_URL", "")  # e.g., https://api.shortener.com/v1/shorten
    
    # Telegram Channels & Groups (IDs as integers)
    SEARCH_GROUP_ID = int(os.getenv("SEARCH_GROUP_ID", "0"))
    STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
    BIN_CHANNEL_ID = int(os.getenv("BIN_CHANNEL_ID", "0"))
    UPDATE_CHANNEL_ID = int(os.getenv("UPDATE_CHANNEL_ID", "0"))
    ERROR_CHANNEL_ID = int(os.getenv("ERROR_CHANNEL_ID", "0"))
    REQUEST_CHANNEL_ID = int(os.getenv("REQUEST_CHANNEL_ID", "0"))
    ADMIN_CONTROL_CHAT_ID = int(os.getenv("ADMIN_CONTROL_CHAT_ID", "0"))
    
    # Super Admins (Comma-separated Telegram user IDs)
    OWNER_IDS = [int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]
  
