"""Health and index routes — no auth required."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import db

router = APIRouter()


def _db_path():
    """Get DB_PATH from app module — tests patch app.DB_PATH."""
    import app as app_module
    return app_module.DB_PATH


@router.get("/health", response_class=JSONResponse)
async def health():
    """Health endpoint — no auth required."""
    conn = None
    try:
        conn = await db.get_connection(_db_path())
        data = await db.get_health(conn)
        return data
    except Exception:
        return JSONResponse({"status": "error"}, status_code=503)
    finally:
        if conn:
            await conn.close()


@router.get("/", response_class=HTMLResponse)
async def index():
    return RedirectResponse("/dashboard")
