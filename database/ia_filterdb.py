import logging
from struct import pack
import re
import base64
import asyncio
from pyrogram.file_id import FileId
from typing import Dict, List
from collections import defaultdict
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from info import *
from utils import get_settings, save_group_settings
from datetime import datetime, timedelta
from functools import lru_cache
from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# ---------------------------------------------------------

# Global cache for DB size
_db_stats_cache = {"timestamp": None, "primary_size": 0.0}

@lru_cache(maxsize=4096)
def compile_regex(pattern):
    return re.compile(pattern, re.IGNORECASE)

# Primary DB
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

# secondary db
client2 = AsyncIOMotorClient(DATABASE_URI2)
db2 = client2[DATABASE_NAME]
instance2 = Instance.from_db(db2)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute="_id")
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    cover = fields.StrField(allow_none=True)

    class Meta:
        indexes = ("$file_name",)
        collection_name = COLLECTION_NAME


@instance2.register
class Media2(Document):
    file_id = fields.StrField(attribute="_id")
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    cover = fields.StrField(allow_none=True)

    class Meta:
        indexes = ("$file_name",)
        collection_name = COLLECTION_NAME

async def check_db_size(db):
    try:
        now = datetime.utcnow()
        cache_stale_by_time = _db_stats_cache["timestamp"] is None or (
            now - _db_stats_cache["timestamp"] > timedelta(minutes=10)
        )
        refresh_if_size_threshold = _db_stats_cache["primary_size"] >= 10.0
        if not cache_stale_by_time and not refresh_if_size_threshold:
            return _db_stats_cache["primary_size"]
        stats = await db.command("dbstats")
        db_logical_size = stats["dataSize"]
        db_index_size = stats["indexSize"]
        db_logical_size_mb = db_logical_size / (1024 * 1024)
        db_index_size_mb = db_index_size / (1024 * 1024)
        db_size_mb = db_logical_size_mb + db_index_size_mb
        _db_stats_cache["primary_size"] = db_size_mb
        _db_stats_cache["timestamp"] = now
        return db_size_mb
    except Exception:
        logger.exception("Error checking database size")
        return 0

async def save_file(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(
        r"[_\-\.#+$%^&*()!~`,;:\"'?/<>\[\]{}=|\\]", " ", str(media.file_name)
    )
    file_name = re.sub(r"\s+", " ", file_name).strip()
    saveMedia = Media
    target_db = "Primary"
    if MULTIPLE_DB:
        try:
            exists = await Media.find_one({"file_id": file_id})
            if exists:
                logger.info(f"[SKIP] '{file_name}' already in Primary DB.")
                return False, 0
            primary_db_size = await check_db_size(db)
            if primary_db_size >= 407:
                saveMedia = Media2
                target_db = "Secondary"
                logger.warning("Switching to Secondary DB due to size threshold.")
        except Exception as e:
            logger.error(
                "Error during MULTIPLE_DB check; defaulting to primary DB.", exc_info=e
            )
    try:
        cover_to_use = getattr(getattr(media, "cover", None), "file_id", None)
        record = saveMedia(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=(media.caption.html if media.caption and INDEX_CAPTION else None),
            cover=cover_to_use if COVER else None,
        )
    except Exception as e:
        logger.exception(f"[ERROR] '{file_name}' → {e}")
        return False, 2
    try:
        await record.commit()
    except DuplicateKeyError:
        logger.info(
            f"[SKIP] DuplicateKey: '{file_name}' already exists in {target_db} DB."
        )
        return False, 0
    except Exception as e:
        logger.exception(
            f"[ERROR] Failed commit of '{file_name}' to {target_db} DB.", exc_info=e
        )
        return False, 3
    #logger.info(f"[SUCCESS] '{file_name}' saved to {target_db} DB.")
    return True, 1

async def get_search_results(chat_id, query, file_type=None, max_results=None, offset=0, filter=False):
    if chat_id is not None and max_results is None:
        settings = await get_settings(int(chat_id))
        if "max_btn" not in settings:
            await save_group_settings(int(chat_id), "max_btn", True)
            settings["max_btn"] = True
        max_results = 10 if settings["max_btn"] else int(MAX_BTNS)
    if isinstance(query, list):
        raw_pattern = "|".join(re.escape(q.strip()) for q in query if q and q.strip())
        if not raw_pattern:
            return [], None, 0
        regex = compile_regex(raw_pattern)
        if USE_CAPTION_FILTER:
            filter_mongo = {"$or": [{"file_name": regex},{"caption": regex},]}
        else:
            filter_mongo = {"file_name": regex}
    else:
        query = query.strip()
        if not query:
            return [], None, 0
        if " " in query:
            words = [re.escape(w) for w in query.split() if w]
            raw_pattern = (r".*[\s\.\+\-_]".join(words) if words else r".")
        else:
            raw_pattern = (r"(\b|[\.\+\-_])" + re.escape(query) + r"(\b|[\.\+\-_])" )
        try:
            regex = compile_regex(raw_pattern)
        except re.error:
            return [], None, 0
        if USE_CAPTION_FILTER:
            filter_mongo = { "$or": [{"file_name": regex}, {"caption": regex},]}
        else:
            filter_mongo = {"file_name": regex}

    if file_type:
        filter_mongo["file_type"] = file_type

    if FAST_MODE:
        limit = max_results + 1
        find_tasks = [Media.find(filter_mongo).sort("$natural", -1).skip(offset).limit(limit).to_list(length=limit)]
        if MULTIPLE_DB:
            find_tasks.append(Media2.find(filter_mongo).sort("$natural", -1).skip(offset).limit(limit).to_list(length=limit))
        results = await asyncio.gather(*find_tasks)
        files = results[0]
        if MULTIPLE_DB and len(results) > 1:
            files.extend(results[1])
        files = files[:limit]
        has_next_page = len(files) > max_results
        if has_next_page:
            files = files[:-1]
        next_offset = offset + len(files) if has_next_page else ""
        total_results = offset + len(files) + (1 if has_next_page else 0)
    else:
        count_tasks = [Media.count_documents(filter_mongo)]
        find_tasks = [Media.find(filter_mongo).sort("$natural", -1).skip(offset).limit(max_results).to_list(length=max_results)]

        if MULTIPLE_DB:
            count_tasks.append(Media2.count_documents(filter_mongo))
            find_tasks.append(Media2.find(filter_mongo).sort("$natural", -1).skip(offset).limit(max_results).to_list(length=max_results))
        count_results, find_results = await asyncio.gather(
            asyncio.gather(*count_tasks),
            asyncio.gather(*find_tasks)
        )
        total_results = sum(count_results)
        files = find_results[0]
        if MULTIPLE_DB and len(find_results) > 1:
            files.extend(find_results[1])
        files = files[:max_results]

        next_offset = offset + len(files)
        if next_offset >= total_results:
            next_offset = ""
    return files, next_offset, total_results

async def get_bad_files(query, file_type=None):
    query = query.strip()
    if not query:
        return [], 0
    if " " not in query:
        raw_pattern = r"(\b|[\.\+\-_])" + re.escape(query) + r"(\b|[\.\+\-_])"
    else:
        raw_pattern = r".*[\s\.\+\-_]".join(map(re.escape, query.split()))
    try:
        regex = compile_regex(raw_pattern)
    except re.error:
        return [], 0
    if USE_CAPTION_FILTER:
        filter_mongo = {
            "$or": [
                {"file_name": regex},
                {"caption": regex}
            ]
        }
    else:
        filter_mongo = {"file_name": regex}
    if file_type:
        filter_mongo["file_type"] = file_type
    tasks = [
        Media.find(filter_mongo)
        .sort("$natural", -1)
        .to_list(300)
    ]
    if MULTIPLE_DB:
        tasks.append(
            Media2.find(filter_mongo)
            .sort("$natural", -1)
            .to_list(300)
        )
    results = await asyncio.gather(*tasks)
    files = results[0]
    if MULTIPLE_DB and len(results) > 1:
        files.extend(results[1])
    files = files[:300]
    return files, len(files)

async def get_file_details(query):
    filter = {"file_id": query}
    tasks = [Media.find(filter).to_list(length=1)]
    if MULTIPLE_DB:
        tasks.append(Media2.find(filter).to_list(length=1))  
    results = await asyncio.gather(*tasks)
    for filedetails in results:
        if filedetails:
            return filedetails       
    return []

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash,
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref

async def techifybots_fetch_media(limit: int) -> List[dict]:
    try:
        if MULTIPLE_DB:
            db_size = await check_db_size(db)
            if db_size > 407:
                cursor = Media2.find().sort("$natural", -1).limit(limit)
                files = await cursor.to_list(length=limit)
                return files
        cursor = Media.find().sort("$natural", -1).limit(limit)
        files = await cursor.to_list(length=limit)
        return files
    except Exception as e:
        logger.error(f"Error in techifybots_fetch_media: {e}")
        return []

async def techifybots_clean_title(filename: str, is_series: bool = False) -> str:
    try:
        year_match = re.search(r"^(.*?(\d{4}|\(\d{4}\)))", filename, re.IGNORECASE)
        if year_match:
            title = year_match.group(1).replace("(", "").replace(")", "")
            return (
                re.sub(
                    r"(?:@[^ \n\r\t.,:;!?()\[\]{}<>\\\/\"'=_%]+|[._\-\[\]@()]+)",
                    " ",
                    title,
                )
                .strip()
                .title()
            )
        if is_series:
            season_match = re.search(
                r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?",
                filename,
                re.IGNORECASE,
            )
            if season_match:
                title = season_match.group(1).strip()
                season = (
                    season_match.group(2)
                    or season_match.group(3)
                    or season_match.group(4)
                )
                title = (
                    re.sub(
                        r"(?:@[^ \n\r\t.,:;!?()\[\]{}<>\\\/\"'=_%]+|[._\-\[\]@()]+)",
                        " ",
                        title,
                    )
                    .strip()
                    .title()
                )
                return f"{title} S{int(season):02}"
        title = filename
        return (
            re.sub(
                r"(?:@[^ \n\r\t.,:;!?()\[\]{}<>\\\/\"'=_%]+|[._\-\[\]@()]+)", " ", title
            )
            .strip()
            .title()
        )
    except Exception as e:
        logger.error(f"Error in truncate_title: {e}")
        return filename

async def techifybots_get_movies(limit: int = 20) -> List[str]:
    try:
        cursor = await techifybots_fetch_media(limit * 2)
        results = set()
        pattern = r"(?:s\d{1,2}|season\s*\d+|season\d+)(?:\s*combined)?(?:e\d{1,2}|episode\s*\d+)?\b"
        for file in cursor:
            file_name = getattr(file, "file_name", "")
            if not re.search(pattern, file_name, re.IGNORECASE):
                title = await techifybots_clean_title(file_name)
                results.add(title)
            if len(results) >= limit:
                break
        return sorted(list(results))[:limit]
    except Exception as e:
        logger.error(f"Error in techifybots_get_movies: {e}")
        return []

async def techifybots_get_series(limit: int = 30) -> Dict[str, List[int]]:
    try:
        cursor = await techifybots_fetch_media(limit * 5)
        grouped = defaultdict(list)
        pattern = r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?(?:E(\d{1,2})|Episode\s*(\d+))?\b"
        for file in cursor:
            file_name = getattr(file, "file_name", "")
            match = re.search(pattern, file_name, re.IGNORECASE)
            if match:
                title = await techifybots_clean_title(match.group(1), is_series=True)
                season = int(match.group(2) or match.group(3) or match.group(4))
                grouped[title].append(season)
        return {
            title: sorted(set(seasons))[:10]
            for title, seasons in grouped.items()
            if seasons
        }
    except Exception as e:
        logger.error(f"Error in techifybots_get_series: {e}")
        return []


# ---------------------------------------------------------
# Fuzzy "Did you mean" suggestions (built from titles already in the DB,
# so every suggestion is guaranteed to return files when tapped)
# ---------------------------------------------------------
_TITLE_CUT = re.compile(
    r"\b(?:s\d{1,2}(?:e\d{1,3})?|season\s*\d+|480p|576p|720p|1080p|1440p|2160p|4k|"
    r"hdrip|hdtv|webrip|web\s?dl|bluray|brrip|dvdrip|hdcam|camrip|predvd|hevc|x26[45]|10bit)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_FUZZY_STOP = {"the", "and", "movie", "movies", "film", "full", "hindi", "dubbed", "new", "latest"}


def fuzzy_clean_title(file_name: str) -> str:
    """'Avengers.Endgame.2019.1080p.WEB-DL' -> 'Avengers Endgame'"""
    name = re.sub(r"@\w+", " ", str(file_name or ""))
    name = re.sub(r"[_\.\-\[\]\(\)\{\}\+]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    cut = len(name)
    for rx in (_TITLE_CUT, _YEAR):
        for m in rx.finditer(name):
            if m.start() > 0:  # ignore markers at position 0 (e.g. movie "1917")
                cut = min(cut, m.start())
                break
    title = name[:cut].strip()
    return title if len(title) >= 2 else ""


def _score_titles(query: str, items, min_score: int):
    scored = []
    for key, title in items:
        score = max(fuzz.token_sort_ratio(query, key), fuzz.ratio(query, key))
        if score >= min_score:
            scored.append((score, title))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return scored


async def get_fuzzy_suggestions(query: str, limit: int = None, min_score: int = None, file_type=None) -> List[str]:
    """Return up to `limit` close title matches (from the DB) for a misspelled query."""
    limit = limit or FUZZY_LIMIT
    min_score = min_score or FUZZY_MIN_SCORE
    q = re.sub(r"[^\w\s]", " ", str(query or "").lower())
    q = re.sub(r"\s+", " ", q).strip()
    if len(q) < 3:
        return []
    tokens = [t for t in q.split() if len(t) >= 3 and t not in _FUZZY_STOP] or [q]
    frags = set()
    for t in tokens:
        frags.add(t[:3])
        if len(t) >= 5:
            frags.add(t[-3:])
    regex = compile_regex("|".join(re.escape(f) for f in frags))
    filter_mongo = {"file_name": regex}
    if file_type:
        filter_mongo["file_type"] = file_type
    n = FUZZY_CANDIDATES
    tasks = [Media.find(filter_mongo).sort("$natural", -1).limit(n).to_list(length=n)]
    if MULTIPLE_DB:
        tasks.append(Media2.find(filter_mongo).sort("$natural", -1).limit(n).to_list(length=n))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    titles = {}
    for res in results:
        if isinstance(res, Exception):
            logger.error(f"Fuzzy candidate fetch failed: {res}")
            continue
        for f in res:
            t = fuzzy_clean_title(f.file_name)
            if t:
                titles.setdefault(t.lower(), t.title())
    if not titles:
        return []
    scored = await asyncio.to_thread(_score_titles, q, list(titles.items()), min_score)
    return [title for _, title in scored[:limit]]
