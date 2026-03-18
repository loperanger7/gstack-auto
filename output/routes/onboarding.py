"""Onboarding routes — 3-step wizard (queries, tone, Twitter connect)."""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/onboard")

BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

VALID_TONES = {"professional", "casual", "witty", "technical", "custom"}
_QUERY_RE = re.compile(r'^[\w\s@#"\'-]{1,200}$')


def _get_app():
    import app as app_module
    return app_module


@router.get("", response_class=HTMLResponse)
async def onboard_page(request: Request):
    """Show onboarding wizard at current step."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    conn = await db.get_connection(a.DB_PATH)
    try:
        user = await db.get_user_by_id(conn, user_id)
        if not user:
            return a._deny()

        step = user.get("onboard_step", 0) + 1
        if step > 3:
            return RedirectResponse("/dashboard", status_code=302)

        queries = await db.get_user_queries(conn, user_id)
    finally:
        await conn.close()

    return templates.TemplateResponse(
        request, "onboard.html", {
            "user": user,
            "step": min(step, 3),
            "queries": queries,
            "tones": ["professional", "casual", "witty", "technical", "custom"],
            "active_page": "onboard",
        }
    )


@router.post("/step1")
async def step1_queries(request: Request):
    """Save search queries."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    form = await request.form()
    raw_queries = str(form.get("queries", "")).strip()
    query_list = [q.strip() for q in raw_queries.split("\n") if q.strip()]

    # Validate each query
    validated = []
    for q in query_list[:20]:
        q = q[:200]
        if q:
            validated.append(q)

    if not validated:
        return RedirectResponse("/onboard?error=no_queries", status_code=302)

    conn = await db.get_connection(a.DB_PATH)
    try:
        await db.save_user_queries(conn, user_id, validated)
        user = await db.get_user_by_id(conn, user_id)
        if user and user.get("onboard_step", 0) < 1:
            await db.update_user(conn, user_id, onboard_step=1)
    finally:
        await conn.close()

    return RedirectResponse("/onboard", status_code=302)


@router.post("/step2")
async def step2_tone(request: Request):
    """Save tone preference."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    form = await request.form()
    tone = str(form.get("tone", "professional")).strip().lower()
    custom_link = str(form.get("custom_link", "")).strip()[:500]

    if tone not in VALID_TONES:
        tone = "professional"

    # Validate custom link if provided
    if custom_link and not custom_link.startswith(("http://", "https://")):
        custom_link = ""

    conn = await db.get_connection(a.DB_PATH)
    try:
        updates = {"tone": tone, "onboard_step": 2}
        if custom_link:
            updates["custom_link"] = custom_link
        await db.update_user(conn, user_id, **updates)
    finally:
        await conn.close()

    return RedirectResponse("/onboard", status_code=302)
