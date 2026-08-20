import redis
from config import Config

redis_client = redis.Redis.from_url(Config.REDIS_URL, decode_responses=True)

def is_rate_limited(user_id: int, limit: int = 10, window: int = 60) -> bool:
    key = f"rate:{user_id}"
    current = redis_client.get(key)
    if current is not None and int(current) >= limit:
        return True
    
    pipe = redis_client.pipeline()
    pipe.incr(key, 1)
    if current is None:
        pipe.expire(key, window)
    pipe.execute()
    return False
  
