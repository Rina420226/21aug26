import httpx
from config import Config
from typing import Optional, Dict

async def fetch_metadata(title: str, year: Optional[int], media_type: str = "movie") -> Optional[Dict]:
    if not Config.TMDB_API_KEY:
        return None
    endpoint = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {
        "api_key": Config.TMDB_API_KEY,
        "query": title
    }
    if year and media_type == "movie":
        params["year"] = year
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(endpoint, params=params)
            data = res.json()
            results = data.get("results", [])
            if results:
                top = results[0]
                poster_path = top.get("poster_path")
                return {
                    "tmdb_id": top.get("id"),
                    "title": top.get("title") or top.get("name"),
                    "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
                    "overview": top.get("overview")
                }
    except Exception:
        return None
    return None
              
