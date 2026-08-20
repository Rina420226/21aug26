import re
from typing import Optional, Tuple

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[\.\_\-\:\,\!\?\[\]\(\)]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_query_metadata(raw_query: str) -> Tuple[str, Optional[int], Optional[int], Optional[int]]:
    """
    Extracts: normalized_title, year, season, episode
    """
    norm = normalize_text(raw_query)
    
    # Check for S01E02 or s1 e2
    se_match = re.search(r'\bs(?:eason)?\s*(\d+)\s*e(?:pisode)?\s*(\d+)\b', norm)
    s_match = re.search(r'\bs(?:eason)?\s*(\d+)\b', norm)
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', norm)
    
    season, episode, year = None, None, None
    
    if se_match:
        season = int(se_match.group(1))
        episode = int(se_match.group(2))
        norm = re.sub(r'\bs(?:eason)?\s*\d+\s*e(?:pisode)?\s*\d+\b', '', norm).strip()
    elif s_match:
        season = int(s_match.group(1))
        norm = re.sub(r'\bs(?:eason)?\s*\d+\b', '', norm).strip()
        
    if year_match:
        year = int(year_match.group(1))
        norm = re.sub(r'\b(19\d{2}|20\d{2})\b', '', norm).strip()
        
    title = re.sub(r'\s+', ' ', norm).strip()
    return title, year, season, episode
  
