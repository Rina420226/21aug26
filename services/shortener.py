import httpx
from config import Config
from utils.logging import logger

async def shorten_url(url: str) -> str:
    if not Config.SHORTENER_API_KEY or not Config.SHORTENER_API_URL:
        return url
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                Config.SHORTENER_API_URL,
                params={"api": Config.SHORTENER_API_KEY, "url": url}
            )
            data = resp.json()
            if data.get("status") == "success" and data.get("shortenedUrl"):
                return data["shortenedUrl"]
            return url
    except Exception as e:
        logger.error(f"Shortener error, fallback used: {e}")
        return url
      
