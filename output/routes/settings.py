"""Settings routes — card-based settings page."""

import logging
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import db

log = logging.getLogger(__name__)
router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

VALID_TONES = {"professional", "casual", "witty", "technical", "custom"}


def _get_app():
    import app as app_module
    return app_module


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Card-based settings page."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    conn = await db.get_connection(a.DB_PATH)
    try:
        user = await db.get_user_by_id(conn, user_id)
        if not user:
            return a._deny()
        queries = await db.get_user_queries(conn, user_id)
    finally:
        await conn.close()

    twitter_status = request.query_params.get("twitter", "")
    error = request.query_params.get("error", "")

    return templates.TemplateResponse(
        request, "settings.html", {
            "user": user,
            "queries": queries,
            "tones": ["professional", "casual", "witty", "technical", "custom"],
            "twitter_status": twitter_status,
            "error": error,
            "active_page": "settings",
        }
    )


@router.post("/settings/queries")
async def update_queries(request: Request):
    """Update search queries."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    form = await request.form()
    raw = str(form.get("queries", "")).strip()
    query_list = [q.strip() for q in raw.split("\n") if q.strip()]
    validated = [q[:200] for q in query_list[:20] if q]

    conn = await db.get_connection(a.DB_PATH)
    try:
        await db.save_user_queries(conn, user_id, validated)
    finally:
        await conn.close()

    return RedirectResponse("/settings?saved=queries", status_code=302)


@router.post("/settings/tone")
async def update_tone(request: Request):
    """Update tone preference."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    form = await request.form()
    tone = str(form.get("tone", "")).strip().lower()
    custom_link = str(form.get("custom_link", "")).strip()[:500]

    if tone not in VALID_TONES:
        tone = "professional"
    if custom_link and not custom_link.startswith(("http://", "https://")):
        custom_link = ""

    conn = await db.get_connection(a.DB_PATH)
    try:
        updates = {"tone": tone}
        if custom_link:
            updates["custom_link"] = custom_link
        await db.update_user(conn, user_id, **updates)
    finally:
        await conn.close()

    return RedirectResponse("/settings?saved=tone", status_code=302)
