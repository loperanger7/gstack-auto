"""FastAPI application — config, auth, lifecycle, router wiring.
Multi-tenant with Google OAuth. Routes live in routes/. Scheduled jobs live in jobs.py."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime, time, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.sessions import SessionMiddleware

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db

log = logging.getLogger(__name__)
_log_format = os.environ.get("LOG_FORMAT", "text")
if _log_format == "json":
    class _JsonFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps({
                "ts": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            })

    _handler = logging.StreamHandler()
    _handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[_handler])
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

# --- Configuration ---

REQUIRED_ENV = [
    "AUTH_SECRET_KEY",
]

ET = ZoneInfo("America/New_York")
COOKIE_NAME = "gstack_session"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days
SEND_WINDOWS = {
    "morning": (time(9, 0), time(11, 0)),
    "lunch": (time(12, 0), time(14, 0)),
    "evening": (time(17, 0), time(19, 0)),
}
VALID_SEND_WINDOWS = set(SEND_WINDOWS.keys())
DB_PATH = os.environ.get("DB_PATH", "data/gstack_replies.db")
HOT_TWEET_THRESHOLD = int(os.environ.get("HOT_TWEET_THRESHOLD", "50000"))
COOLDOWN_DAYS = int(os.environ.get("COOLDOWN_DAYS", "7"))

# Google OAuth config
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Admin emails (comma-separated)
ADMIN_EMAILS = set(
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
)

# Global state
shutdown_event = asyncio.Event()


def _validate_env() -> None:
    """Fail fast if required env vars are missing."""
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        log.critical("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)


# --- Auth (Session-based with Google OAuth) ---

def _get_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(os.environ["AUTH_SECRET_KEY"])


def get_current_user_id(request: Request) -> int | None:
    """Get current user ID from session. Returns None if not authenticated."""
    user_id = request.session.get("user_id")
    if user_id and isinstance(user_id, int) and user_id > 0:
        return user_id
    return None


def check_auth(request: Request) -> bool:
    """Check if request has a valid session. Fail closed."""
    return get_current_user_id(request) is not None


def _deny() -> Response:
    """Redirect to login page instead of showing 401."""
    return RedirectResponse("/auth/login", status_code=302)


def _deny_api() -> Response:
    """Return 401 for API endpoints."""
    body = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>gstack - Unauthorized</title>'
        '<style>body{font-family:-apple-system,system-ui,sans-serif;background:#0d1117;'
        'color:#c9d1d9;display:flex;justify-content:center;align-items:center;'
        'min-height:100vh;margin:0;text-align:center}'
        '.box{padding:2rem}'
        'h1{font-size:1.3rem;color:#f85149;margin-bottom:.5rem}'
        'p{color:#8b949e;font-size:.95rem}'
        '</style></head><body><div class="box">'
        '<h1>Unauthorized</h1>'
        '<p>Please <a href="/auth/login" style="color:#58a6ff">log in</a> to continue.</p>'
        '</div></body></html>'
    )
    return HTMLResponse(status_code=401, content=body)


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_env()

    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = await db.get_connection(DB_PATH)
    await db.init_db(conn)
    await conn.close()
    log.info("Database initialized at %s", DB_PATH)

    import jobs
    scheduler = AsyncIOScheduler()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        scheduler.add_job(
            jobs.monitor_cycle, "interval", minutes=15,
            id="monitor", max_instances=1,
        )
    else:
        log.warning("ANTHROPIC_API_KEY not set — monitor cycle disabled")

    scheduler.add_job(
        jobs.check_engagement, "interval", hours=6,
        id="engagement", max_instances=1,
    )
    scheduler.add_job(
        jobs.weekly_digest, "cron", day_of_week="mon", hour=9, minute=0,
        id="digest", max_instances=1,
    )
    scheduler.start()
    log.info("Scheduler started")

    def handle_sigterm(*_):
        log.info("SIGTERM received — graceful shutdown")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_sigterm)

    yield

    shutdown_event.set()
    scheduler.shutdown(wait=True)
    log.info("Shutdown complete")


# --- FastAPI app with route modules ---

from routes.health import router as health_router
from routes.dashboard import router as dashboard_router
from routes.stats import router as stats_router
from routes.auth import router as auth_router
from routes.onboarding import router as onboarding_router
from routes.settings import router as settings_router
from routes.admin import router as admin_router

app = FastAPI(lifespan=lifespan)

# Session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("AUTH_SECRET_KEY", "INSECURE-DEV-ONLY"),
    max_age=COOKIE_MAX_AGE,
    same_site="lax",
    https_only=os.environ.get("ENVIRONMENT", "development") == "production",
)

@app.get("/")
async def root():
    """Redirect root to login page."""
    return RedirectResponse("/auth/login", status_code=302)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(dashboard_router)
app.include_router(stats_router)
app.include_router(settings_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), reload=False)
