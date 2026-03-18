"""Dashboard routes — approval queue, approve, skip. Auth required."""

import logging
import re
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import db

log = logging.getLogger(__name__)
router = APIRouter()

VALID_SEND_WINDOWS = {"morning", "lunch", "evening"}
ET = ZoneInfo("America/New_York")
BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Input validation — fail closed: reject anything unexpected
_TWEET_ID_RE = re.compile(r'^[\w-]{1,64}$')
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def _get_app():
    """Import app module. Deferred to avoid circular imports."""
    import app as app_module
    return app_module


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    a = _get_app()
    if not a.check_auth(request):
        return a._deny()

    conn = await db.get_connection(a.DB_PATH)
    try:
        tweets = await db.get_pending_tweets(conn)
        health_data = await db.get_health(conn)
    finally:
        await conn.close()

    # Auto-select nearest upcoming send window
    et_hour = datetime.now(ET).hour
    if et_hour < 11:
        default_window = "morning"
    elif et_hour < 14:
        default_window = "lunch"
    else:
        default_window = "evening"

    response = templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "tweets": tweets,
            "send_windows": VALID_SEND_WINDOWS,
            "last_cycle": health_data.get("last_cycle"),
            "current_et_hour": et_hour,
            "default_window": default_window,
        },
    )
    return a._set_auth_cookie(response)


@router.post("/approve")
async def approve(
    request: Request,
    tweet_id: str = Form(...),
    variant_id: int = Form(...),
    reply_text: str = Form(""),
    send_window: str = Form(...),
):
    a = _get_app()
    if not a.check_auth(request):
        return a._deny()

    # Validate inputs before touching the database
    if not _TWEET_ID_RE.match(tweet_id):
        return JSONResponse({"error": "Invalid request"}, status_code=400)
    if variant_id < 1:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    text = _CONTROL_CHARS_RE.sub('', reply_text).strip()
    if not text:
        return JSONResponse({"error": "Reply text cannot be empty"}, status_code=400)
    if len(text) > 280:
        return JSONResponse({"error": f"Reply exceeds 280 chars ({len(text)})"}, status_code=400)
    if send_window not in VALID_SEND_WINDOWS:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    conn = await db.get_connection(a.DB_PATH)
    try:
        scheduled = a._next_send_time(send_window)
        ok = await db.approve_variant(conn, tweet_id, variant_id, text, scheduled, send_window)
    finally:
        await conn.close()

    if not ok:
        return JSONResponse({"error": "Tweet not pending or variant not found"}, status_code=409)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"ok": True, "action": "approved"})
    return RedirectResponse("/dashboard?action=approved", status_code=303)


@router.post("/skip")
async def skip(request: Request, tweet_id: str = Form(...)):
    a = _get_app()
    if not a.check_auth(request):
        return a._deny()

    if not _TWEET_ID_RE.match(tweet_id):
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    conn = await db.get_connection(a.DB_PATH)
    try:
        ok = await db.skip_tweet(conn, tweet_id)
    finally:
        await conn.close()

    if not ok:
        return JSONResponse({"error": "Tweet not found or already handled"}, status_code=409)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"ok": True, "action": "skipped"})
    return RedirectResponse("/dashboard?action=skipped", status_code=303)
