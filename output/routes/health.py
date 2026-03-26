"""Health and index routes — no auth required."""

import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import db

log = logging.getLogger(__name__)
router = APIRouter()


def _db_path():
    """Get DB_PATH from app module — tests patch app.DB_PATH."""
    import app as app_module
    return app_module.DB_PATH


@router.get("/health", response_class=JSONResponse)
async def health():
    """Health endpoint — no auth required. Always returns JSON, never crashes."""
    conn = None
    try:
        conn = await db.get_connection(_db_path())
        data = await db.get_health(conn)
        return data
    except Exception as e:
        log.error("Health check failed: %s", e)
        return JSONResponse({"status": "error", "detail": str(e)[:100]}, status_code=503)
    finally:
        if conn:
            try:
                await conn.close()
            except Exception:
                pass  # Connection close should never crash the health endpoint


@router.get("/", response_class=HTMLResponse)
async def index():
    return RedirectResponse("/dashboard")
