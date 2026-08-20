from pymongo import MongoClient, ASCENDING, TEXT
from config import Config
from typing import Dict, Any, Optional

client = MongoClient(Config.MONGODB_URI)
db = client[Config.DATABASE_NAME]

# Collections
movies_col = db["movies"]
series_col = db["series"]
files_col = db["files"]
users_col = db["users"]
settings_col = db["settings"]
search_requests_col = db["search_requests"]
deletion_jobs_col = db["deletion_jobs"]

def setup_indexes():
    movies_col.create_index([("normalized_title", ASCENDING)])
    movies_col.create_index([("year", ASCENDING)])
    movies_col.create_index([("aliases", ASCENDING)])
    
    series_col.create_index([("normalized_title", ASCENDING)])
    files_col.create_index([("item_id", ASCENDING), ("language", ASCENDING), ("quality", ASCENDING)], unique=True)
    deletion_jobs_col.create_index([("delete_at", ASCENDING)])

def get_settings() -> Dict[str, Any]:
    defaults = {
        "_id": "global_settings",
        "maintenance": False,
        "maintenance_message": "🛠️ Bot is under maintenance. Please try again later.",
        "tmdb_poster": True,
        "auto_filter": True,
        "url_shortener": False,
        "result_mode": "buttons",  # 'buttons' or 'text'
        "auto_delete": True,
        "delete_time": 300,        # 5 minutes in seconds
        "rate_limit_count": 10,
        "rate_limit_window": 60
    }
    settings = settings_col.find_one({"_id": "global_settings"})
    if not settings:
        settings_col.insert_one(defaults)
        return defaults
    return settings

def update_settings(key: str, value: Any):
    settings_col.update_one({"_id": "global_settings"}, {"$set": {key: value}}, upsert=True)
  
