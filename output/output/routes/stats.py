"""Stats page route — auth required. User-scoped."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import db

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _get_app():
    """Import app module. Deferred to avoid circular imports."""
    import app as app_module
    return app_module


@router.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    conn = await db.get_connection(a.DB_PATH)
    try:
        user = await db.get_user_by_id(conn, user_id)
        if not user:
            return a._deny()
        stats = await db.get_stats(conn, user_id=user_id)
        cycles = await db.get_cycle_history(conn, limit=20, user_id=user_id)
    finally:
        await conn.close()

    max_window_replies = max((w["count"] for w in stats.get("window_stats", [])), default=1) or 1

    return templates.TemplateResponse(
        request,
        "stats.html",
        {
            "stats": stats,
            "cycles": cycles,
            "max_window_replies": max_window_replies,
            "active_page": "stats",
            "user": user,
        },
    )
