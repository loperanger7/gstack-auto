"""Admin routes — leaderboard and user management."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin")

BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _get_app():
    import app as app_module
    return app_module


async def _require_admin(request) -> tuple:
    """Check auth + admin. Returns (app, user_id) or raises redirect."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a, None

    conn = await db.get_connection(a.DB_PATH)
    try:
        user = await db.get_user_by_id(conn, user_id)
        if not user or not user.get("is_admin"):
            return a, None
    finally:
        await conn.close()
    return a, user_id


@router.get("", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Admin panel with engagement leaderboard."""
    a, user_id = await _require_admin(request)
    if not user_id:
        return HTMLResponse(
            '<html><body style="background:#0d1117;color:#f85149;display:flex;'
            'justify-content:center;align-items:center;height:100vh;font-family:sans-serif">'
            '<p>403 Forbidden — Admin access required.</p></body></html>',
            status_code=403,
        )

    conn = await db.get_connection(a.DB_PATH)
    try:
        leaderboard = await db.get_engagement_leaderboard(conn)
        all_users = await db.get_all_users(conn)
        health = await db.get_health(conn)
    finally:
        await conn.close()

    return templates.TemplateResponse(
        request, "admin.html", {
            "leaderboard": leaderboard,
            "users": all_users,
            "health": health,
            "active_page": "admin",
        }
    )


@router.post("/toggle-user/{target_user_id}")
async def toggle_user_active(request: Request, target_user_id: int):
    """Toggle a user's active status."""
    a, user_id = await _require_admin(request)
    if not user_id:
        return JSONResponse({"error": "forbidden"}, status_code=403)

    conn = await db.get_connection(a.DB_PATH)
    try:
        target = await db.get_user_by_id(conn, target_user_id)
        if not target:
            return JSONResponse({"error": "user not found"}, status_code=404)
        new_status = 0 if target["is_active"] else 1
        await db.update_user(conn, target_user_id, is_active=new_status)
    finally:
        await conn.close()

    return RedirectResponse("/admin", status_code=302)
