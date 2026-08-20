from typing import List, Dict, Any, Optional
from rapidfuzz import process, fuzz
from services.database import movies_col, series_col
from utils.normalization import normalize_text

def search_content(title: str, year: Optional[int], is_series: bool = False) -> Dict[str, Any]:
    col = series_col if is_series else movies_col
    norm_title = normalize_text(title)
    
    # 1. Exact Match
    query = {"normalized_title": norm_title}
    if year and not is_series:
        query["year"] = year
    exact = col.find_one(query)
    if exact:
        return {"status": "exact", "results": [exact]}
        
    # 2. Alias / Text Lookup
    alias_match = col.find_one({"aliases": norm_title})
    if alias_match:
        return {"status": "exact", "results": [alias_match]}
        
    # 3. Fuzzy Lookup across registered titles
    all_titles = list(col.find({}, {"normalized_title": 1, "title": 1, "year": 1}))
    if not all_titles:
        return {"status": "none", "results": []}
        
    title_map = {item["normalized_title"]: item for item in all_titles}
    choices = list(title_map.keys())
    
    matches = process.extract(norm_title, choices, scorer=fuzz.token_set_ratio, limit=5)
    
    # Auto-correction if confidence is extremely high (>= 92)
    if matches and matches[0][1] >= 92:
        best_doc = title_map[matches[0][0]]
        return {"status": "corrected", "results": [best_doc]}
        
    # Suggestions (Top 3 with score >= 60)
    suggestions = []
    for match_title, score, _ in matches:
        if score >= 60:
            suggestions.append(title_map[match_title])
        if len(suggestions) == 3:
            break
            
    if suggestions:
        return {"status": "fuzzy", "results": suggestions}
        
    return {"status": "none", "results": []}
      
