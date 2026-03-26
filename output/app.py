"""FastAPI application — config, auth, lifecycle, router wiring.
Routes live in routes/. Scheduled jobs live in jobs.py."""

import asyncio
import base64
import hmac as _hmac
import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, time, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional in production

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
    "CONSUMER_KEY", "CONSUMER_KEY_SECRET",
    "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET",
    "DASHBOARD_USERNAME", "DASHBOARD_PASSWORD",
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

# Global state
shutdown_event = asyncio.Event()


def _validate_env() -> None:
    """Fail fast if required env vars are missing."""
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        log.critical("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)


# --- Auth ---

def _get_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(os.environ["AUTH_SECRET_KEY"])


def check_auth(request: Request) -> bool:
    """Check signed cookie or Basic Auth. Fail closed: any error = denied."""
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        try:
            data = _get_signer().loads(cookie, max_age=COOKIE_MAX_AGE)
            if data == os.environ["DASHBOARD_USERNAME"]:
                return True
        except (BadSignature, KeyError, ValueError):
            pass

    auth = request.headers.get("authorization", "")
    if auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            username, password = decoded.split(":", 1)
            if (_hmac.compare_digest(username, os.environ["DASHBOARD_USERNAME"])
                    and _hmac.compare_digest(password, os.environ["DASHBOARD_PASSWORD"])):
                return True
        except (ValueError, UnicodeDecodeError, KeyError):
            pass
    return False


def _set_auth_cookie(response: Response) -> Response:
    token = _get_signer().dumps(os.environ["DASHBOARD_USERNAME"])
    response.set_cookie(
        COOKIE_NAME, token, max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="lax",
    )
    return response


def _deny() -> Response:
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
        '<p>Valid credentials required to access the dashboard.</p>'
        '</div></body></html>'
    )
    return HTMLResponse(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="gstack"'},
        content=body,
    )


# --- Send window logic ---

def _is_in_send_window(window_name: str) -> bool:
    """Check if current ET time is within the named send window."""
    if window_name not in SEND_WINDOWS:
        return False
    now_et = datetime.now(ET).time()
    start, end = SEND_WINDOWS[window_name]
    return start <= now_et <= end


def _next_send_time(window: str) -> str:
    """Compute next occurrence of send window start as ISO UTC string."""
    start, _ = SEND_WINDOWS.get(window, (time(9, 0), time(11, 0)))
    now_et = datetime.now(ET)
    candidate = now_et.replace(hour=start.hour, minute=0, second=0, microsecond=0)
    if candidate < now_et:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()


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
        jobs.send_approved_replies, "interval", minutes=1,
        id="sender", max_instances=1,
    )
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

app = FastAPI(lifespan=lifespan)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(stats_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), reload=False)
