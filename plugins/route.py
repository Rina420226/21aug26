"""HTTP endpoints for browser streaming and direct file downloads."""
from aiohttp import web
import logging
import math
import mimetypes
import re
import secrets
from aiohttp.http_exceptions import BadStatusLine
from LucyBot.Bot import multi_clients, work_loads
from LucyBot.server.exceptions import FIleNotFound, InvalidHash
from LucyBot.util.custom_dl import ByteStreamer
from LucyBot.util.render_template import render_page
from LucyBot.util.ranges import parse_byte_range
from info import LOG_CHANNEL, MULTI_CLIENT

routes = web.RouteTableDef()


@routes.get("/", allow_head=True)
async def root_route_handler(request: web.Request):
    return web.json_response({"service": "Lucy_Bot", "status": "ok"})


def _parse_media_path(path: str, query_hash: str | None) -> tuple[int, str]:
    """Accept legacy hash+message-id paths and the normal id/filename form."""
    match = re.fullmatch(r"([A-Za-z0-9_-]{6})(\d+)", path)
    if match:
        return int(match.group(2)), match.group(1)

    match = re.fullmatch(r"(\d+)(?:/.*)?", path)
    if not match:
        raise web.HTTPBadRequest(text="Invalid file URL")
    if not query_hash:
        raise InvalidHash
    return int(match.group(1)), query_hash


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        file_id, secure_hash = _parse_media_path(
            request.match_info["path"], request.rel_url.query.get("hash")
        )
        return web.Response(
            text=await render_page(file_id, secure_hash),
            content_type="text/html",
            charset="utf-8",
        )
    except InvalidHash as exc:
        raise web.HTTPForbidden(text=exc.message)
    except FIleNotFound as exc:
        raise web.HTTPNotFound(text=exc.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        raise web.HTTPBadRequest(text="Invalid request")
    except web.HTTPException:
        raise
    except Exception as exc:
        logging.exception("Watch page request failed")
        raise web.HTTPInternalServerError(text="Unable to open this media") from exc


@routes.get(r"/dl/{path:\S+}", allow_head=True)
async def direct_download_handler(request: web.Request):
    """Explicit download endpoint; keeps the older root-level URL working too."""
    return await _handle_download_request(request)


@routes.get(r"/{path:\S+}", allow_head=True)
async def download_handler(request: web.Request):
    return await _handle_download_request(request)


async def _handle_download_request(request: web.Request):
    try:
        file_id, secure_hash = _parse_media_path(
            request.match_info["path"], request.rel_url.query.get("hash")
        )
        return await media_streamer(request, file_id, secure_hash)
    except InvalidHash as exc:
        raise web.HTTPForbidden(text=exc.message)
    except FIleNotFound as exc:
        raise web.HTTPNotFound(text=exc.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        raise web.HTTPBadRequest(text="Invalid request")
    except web.HTTPException:
        raise
    except Exception as exc:
        logging.exception("Media request failed")
        raise web.HTTPInternalServerError(text="Unable to stream this media") from exc


class_cache = {}


async def media_streamer(request: web.Request, id: int, secure_hash: str):
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if MULTI_CLIENT:
        logging.info("Client %s is serving %s", index, request.remote)

    tg_connect = class_cache.get(faster_client)
    if tg_connect is None:
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect

    file_id = await tg_connect.get_file_properties(id)
    if not secure_hash or file_id.unique_id[:6] != secure_hash:
        raise InvalidHash

    file_size = int(file_id.file_size or 0)
    range_header = request.headers.get("Range")
    parsed_range = parse_byte_range(range_header, file_size)
    if parsed_range is None:
        raise web.HTTPRequestRangeNotSatisfiable(
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    from_bytes, until_bytes, is_partial = parsed_range
    req_length = max(0, until_bytes - from_bytes + 1)
    chunk_size = 1024 * 1024
    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1
    part_count = (until_bytes // chunk_size) - (offset // chunk_size) + 1

    file_name = file_id.file_name or f"{secrets.token_hex(4)}.bin"
    file_name = re.sub(r'[\r\n"]', "_", file_name)
    mime_type = file_id.mime_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    disposition = "inline" if request.rel_url.query.get("inline") == "1" else "attachment"

    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(req_length),
        "Content-Disposition": f'{disposition}; filename="{file_name}"',
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, no-store",
    }
    if is_partial:
        headers["Content-Range"] = f"bytes {from_bytes}-{until_bytes}/{file_size}"

    status = 206 if is_partial else 200
    if request.method == "HEAD":
        return web.Response(status=status, headers=headers)

    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )
    return web.Response(status=status, body=body, headers=headers)
