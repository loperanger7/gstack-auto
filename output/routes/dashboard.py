"""Dashboard routes — approval queue with Twitter intent URLs. Auth required. User-scoped."""

import asyncio
import logging
import re
import urllib.parse
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import db

log = logging.getLogger(__name__)
router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Input validation — fail closed: reject anything unexpected
_TWEET_ID_RE = re.compile(r'^[\w-]{1,64}$')
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def _get_app():
    """Import app module. Deferred to avoid circular imports."""
    import app as app_module
    return app_module


def _intent_url(tweet_id: str, text: str) -> str:
    """Build Twitter intent URL for replying to a tweet."""
    return (
        "https://x.com/intent/post?"
        + urllib.parse.urlencode({"in_reply_to": tweet_id, "text": text})
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    conn = await db.get_connection(a.DB_PATH)
    try:
        user = await db.get_user_by_id(conn, user_id)
        if not user:
            return a._deny()

        if user.get("onboard_step", 0) < 3:
            return RedirectResponse("/onboard", status_code=302)

        tweets = await db.get_pending_tweets(conn, user_id=user_id)
        recently_posted = await db.get_recently_posted(conn, user_id)
        health_data = await db.get_health(conn)

        user_cycles = await db.get_cycle_history(conn, limit=1, user_id=user_id)
        if not user_cycles:
            import jobs
            asyncio.create_task(jobs.trigger_first_monitor(user_id))
    finally:
        await conn.close()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "tweets": tweets,
            "recently_posted": recently_posted,
            "last_cycle": health_data.get("last_cycle"),
            "error_count_24h": health_data.get("error_count_24h", 0),
            "active_page": "dashboard",
            "user": user,
        },
    )


@router.post("/approve")
async def approve(
    request: Request,
    tweet_id: str = Form(...),
    variant_id: int = Form(...),
    reply_text: str = Form(""),
):
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny_api()

    if not _TWEET_ID_RE.match(tweet_id):
        return JSONResponse({"error": "Invalid request"}, status_code=400)
    if variant_id < 1:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    text = _CONTROL_CHARS_RE.sub('', reply_text).strip()
    if not text:
        return JSONResponse({"error": "Reply text cannot be empty"}, status_code=400)
    if len(text) > 280:
        return JSONResponse({"error": f"Reply exceeds 280 chars ({len(text)})"}, status_code=400)

    conn = await db.get_connection(a.DB_PATH)
    try:
        cursor = await conn.execute(
            "SELECT user_id FROM tweets WHERE id = ?", (tweet_id,)
        )
        row = await cursor.fetchone()
        if not row or row["user_id"] != user_id:
            return JSONResponse({"error": "Not authorized for this tweet"}, status_code=403)

        reply_id = await db.approve_variant(conn, tweet_id, variant_id, text)

        # Set cooldown for this author
        cursor = await conn.execute(
            "SELECT author_id FROM tweets WHERE id = ?", (tweet_id,)
        )
        author_row = await cursor.fetchone()
        if author_row:
            await db.update_cooldown(conn, author_row["author_id"], user_id=user_id)
    finally:
        await conn.close()

    if reply_id is None:
        return JSONResponse({"error": "Tweet not pending or variant not found"}, status_code=409)

    intent = _intent_url(tweet_id, text)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"ok": True, "intent_url": intent, "reply_id": reply_id})
    return RedirectResponse(intent, status_code=303)


@router.post("/undo")
async def undo(request: Request, reply_id: int = Form(...)):
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny_api()

    if reply_id < 1:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    conn = await db.get_connection(a.DB_PATH)
    try:
        ok = await db.undo_posted(conn, reply_id, user_id)
    finally:
        await conn.close()

    if not ok:
        return JSONResponse({"error": "Cannot undo — reply not found or not yours"}, status_code=409)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"ok": True, "action": "undone"})
    return RedirectResponse("/dashboard?action=undone", status_code=303)


@router.post("/save-reply-url")
async def save_reply_url_endpoint(
    request: Request,
    reply_id: int = Form(...),
    twitter_reply_id: str = Form(...),
):
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny_api()

    if reply_id < 1:
        return JSONResponse({"error": "Invalid request"}, status_code=400)
    # Accept a tweet ID or a full URL — extract the ID
    tid = twitter_reply_id.strip().rstrip("/").split("/")[-1]
    if not _TWEET_ID_RE.match(tid):
        return JSONResponse({"error": "Invalid tweet ID or URL"}, status_code=400)

    conn = await db.get_connection(a.DB_PATH)
    try:
        ok = await db.save_reply_url(conn, reply_id, tid, user_id)
    finally:
        await conn.close()

    if not ok:
        return JSONResponse({"error": "Reply not found or not yours"}, status_code=409)
    return JSONResponse({"ok": True})


@router.post("/skip")
async def skip(request: Request, tweet_id: str = Form(...)):
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny_api()

    if not _TWEET_ID_RE.match(tweet_id):
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    conn = await db.get_connection(a.DB_PATH)
    try:
        cursor = await conn.execute(
            "SELECT user_id FROM tweets WHERE id = ?", (tweet_id,)
        )
        row = await cursor.fetchone()
        if not row or row["user_id"] != user_id:
            return JSONResponse({"error": "Not authorized for this tweet"}, status_code=403)

        ok = await db.skip_tweet(conn, tweet_id)
    finally:
        await conn.close()

    if not ok:
        return JSONResponse({"error": "Tweet not found or already handled"}, status_code=409)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"ok": True, "action": "skipped"})
    return RedirectResponse("/dashboard?action=skipped", status_code=303)
