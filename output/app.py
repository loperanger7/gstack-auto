"""FastAPI application — routes, auth, scheduler, email alerts.
Single entry point. Every external dependency is fail-safe."""

import asyncio
import base64
import hmac as _hmac
import json
import logging
import os
import signal
import smtplib
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, time, timezone
from email.mime.text import MIMEText
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import anthropic
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeTimedSerializer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional in production

import db
import drafter
import twitter

log = logging.getLogger(__name__)
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
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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
        except (BadSignature, Exception):
            pass

    auth = request.headers.get("authorization", "")
    if auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            username, password = decoded.split(":", 1)
            if (_hmac.compare_digest(username, os.environ["DASHBOARD_USERNAME"])
                    and _hmac.compare_digest(password, os.environ["DASHBOARD_PASSWORD"])):
                return True
        except Exception:
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
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="gstack"'},
        content="Unauthorized",
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


# --- Email (fire-and-forget) ---

def _send_email(subject: str, body: str) -> None:
    """Send email via Gmail SMTP. Catches all errors internally."""
    addr = os.environ.get("GMAIL_ADDRESS", "")
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT_EMAIL", addr)
    if not addr or not pwd:
        log.info("Email not configured, skipping: %s", subject)
        return
    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = addr
        msg["To"] = recipient
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
            s.starttls()
            s.login(addr, pwd)
            s.send_message(msg)
        log.info("Email sent: %s", subject)
    except Exception as e:
        log.error("Email send failed: %s", e)


# --- Scheduled jobs ---

async def monitor_cycle() -> None:
    """Search Twitter, classify, draft variants, store pending."""
    if shutdown_event.is_set():
        return

    log.info("Starting monitor cycle")
    conn = await db.get_connection(DB_PATH)
    cycle_id = None
    tweets_found = 0
    drafts_created = 0
    errors_list = []

    try:
        cycle_id = await db.start_cycle(conn)

        async with httpx.AsyncClient() as http_client:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                log.warning("ANTHROPIC_API_KEY not set, skipping drafting")
                return
            claude_client = anthropic.AsyncAnthropic(api_key=api_key)

            mentions = await twitter.search_mentions(http_client)
            tweets_found = len(mentions)

            for mention in mentions:
                if shutdown_event.is_set():
                    break

                inserted = await db.upsert_tweet(
                    conn,
                    tweet_id=mention["id"],
                    author_id=mention["author_id"],
                    author_name=mention.get("author_name", ""),
                    follower_count=mention.get("follower_count", 0),
                    text=mention["text"],
                )
                if not inserted:
                    continue

                if await db.check_cooldown(conn, mention["author_id"], COOLDOWN_DAYS):
                    log.info("Skipping %s — author on cooldown", mention["id"])
                    continue

                thread = []
                conv_id = mention.get("conversation_id", mention["id"])
                if conv_id:
                    thread = await twitter.fetch_thread(http_client, conv_id)

                thread_json = json.dumps(
                    [{"text": t.get("text", "")} for t in thread] if thread else []
                )
                await conn.execute(
                    "UPDATE tweets SET thread_json = ? WHERE id = ?",
                    (thread_json, mention["id"]),
                )
                await conn.commit()

                sentiment = await drafter.classify_sentiment(claude_client, mention["text"])
                await conn.execute(
                    "UPDATE tweets SET sentiment = ? WHERE id = ?",
                    (sentiment, mention["id"]),
                )
                await conn.commit()

                variants = await drafter.draft_variants(
                    claude_client,
                    tweet_text=mention["text"],
                    author_name=mention.get("author_name", ""),
                    author_username=mention.get("author_username", ""),
                    sentiment=sentiment,
                    thread=thread,
                )
                if variants:
                    count = await db.save_variants(conn, mention["id"], variants)
                    drafts_created += count
                    log.info("Drafted %d variants for tweet %s", count, mention["id"])

                    follower_count = mention.get("follower_count", 0)
                    if isinstance(follower_count, int) and follower_count >= HOT_TWEET_THRESHOLD:
                        _send_email(
                            f"HOT TWEET: {mention.get('author_name', '?')} ({follower_count:,} followers)",
                            f"Tweet: {mention['text']}\n\nAuthor: {mention.get('author_name', '')}\n"
                            f"Followers: {follower_count:,}\nID: {mention['id']}",
                        )
                else:
                    log.warning("No variants for tweet %s", mention["id"])

    except twitter.RateLimitError:
        errors_list.append("Rate limit hit")
        log.warning("Rate limit — skipping rest of cycle")
    except twitter.TwitterAuthError:
        errors_list.append("Auth failed")
        log.critical("Twitter auth failed — check credentials")
        _send_email("CRITICAL: Twitter Auth Failed", "Twitter 401. Check API credentials.")
    except Exception as e:
        errors_list.append(str(e)[:200])
        log.error("Monitor cycle error: %s", e, exc_info=True)
    finally:
        if cycle_id is not None:
            await db.end_cycle(
                conn, cycle_id, tweets_found, drafts_created,
                "; ".join(errors_list),
            )
        await conn.close()

    log.info("Monitor cycle done: %d found, %d drafted", tweets_found, drafts_created)


async def send_approved_replies() -> None:
    """Post approved replies whose send window is active."""
    if shutdown_event.is_set():
        return

    conn = await db.get_connection(DB_PATH)
    try:
        queue = await db.get_send_queue(conn)
        if not queue:
            return

        async with httpx.AsyncClient() as http_client:
            for item in queue:
                if shutdown_event.is_set():
                    break

                # Send if ANY window is active. scheduled_for already
                # gates first-eligible time; after that, don't require
                # exact window match or stale replies never send.
                if not any(_is_in_send_window(w) for w in VALID_SEND_WINDOWS):
                    continue

                try:
                    reply_id = await twitter.post_reply(
                        http_client, item["tweet_id"], item["reply_text"]
                    )
                    await db.mark_sent(conn, item["reply_id"], reply_id)
                    await db.update_cooldown(conn, item["author_id"])
                    log.info("Sent reply %s to tweet %s", reply_id, item["tweet_id"])
                    await asyncio.sleep(10)
                except twitter.TweetDeletedError:
                    await db.mark_stale(conn, item["tweet_id"])
                    log.warning("Tweet %s deleted, marked stale", item["tweet_id"])
                except twitter.RateLimitError:
                    log.warning("Rate limited during send — will retry next cycle")
                    break
                except Exception as e:
                    log.error("Send failed for tweet %s: %s", item["tweet_id"], e)
    finally:
        await conn.close()


async def check_engagement() -> None:
    """Check engagement on replies sent ~24h and ~72h ago."""
    if shutdown_event.is_set():
        return

    conn = await db.get_connection(DB_PATH)
    try:
        async with httpx.AsyncClient() as http_client:
            for hours in (24, 72):
                replies = await db.get_replies_needing_engagement_check(conn, hours)
                for r in replies:
                    if not r.get("twitter_reply_id"):
                        continue
                    try:
                        eng = await twitter.get_tweet_engagement(
                            http_client, r["twitter_reply_id"]
                        )
                        if not eng.get("deleted") and not eng.get("error"):
                            await db.upsert_engagement(
                                conn, r["reply_id"], eng["likes"], eng["retweets"]
                            )
                    except Exception as e:
                        log.warning("Engagement check failed for reply %s: %s", r["reply_id"], e)
    finally:
        await conn.close()


async def weekly_digest() -> None:
    """Send weekly digest email every Monday."""
    if shutdown_event.is_set():
        return

    conn = await db.get_connection(DB_PATH)
    try:
        data = await db.get_weekly_digest(conn)
        body = (
            f"gstack Twitter Auto-Reply — Weekly Digest\n"
            f"{'=' * 45}\n\n"
            f"Tweets found: {data['tweets_found']}\n"
            f"Replies sent: {data['replies_sent']}\n"
            f"Total likes: {data['total_likes']}\n"
            f"Total retweets: {data['total_retweets']}\n"
            f"Error cycles: {data['error_cycles']}\n\n"
        )
        if data["top_replies"]:
            body += "Top Replies:\n"
            for r in data["top_replies"]:
                body += (
                    f"  - To @{r['author_name']} ({r['follower_count']:,} followers): "
                    f"{r['draft_text'][:80]}... "
                    f"[{r['likes']}L {r['retweets']}RT]\n"
                )
        else:
            body += "No replies sent this week.\n"

        _send_email("gstack Weekly Digest", body)
    except Exception as e:
        log.error("Weekly digest failed: %s", e)
    finally:
        await conn.close()


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_env()

    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = await db.get_connection(DB_PATH)
    await db.init_db(conn)
    await conn.close()
    log.info("Database initialized at %s", DB_PATH)

    scheduler = AsyncIOScheduler()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        scheduler.add_job(
            monitor_cycle, "interval", minutes=15,
            id="monitor", max_instances=1,
        )
    else:
        log.warning("ANTHROPIC_API_KEY not set — monitor cycle disabled")

    scheduler.add_job(
        send_approved_replies, "interval", minutes=1,
        id="sender", max_instances=1,
    )
    scheduler.add_job(
        check_engagement, "interval", hours=6,
        id="engagement", max_instances=1,
    )
    scheduler.add_job(
        weekly_digest, "cron", day_of_week="mon", hour=9, minute=0,
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


# --- FastAPI app ---

app = FastAPI(lifespan=lifespan)


@app.get("/health", response_class=JSONResponse)
async def health():
    """Health endpoint — no auth required."""
    conn = None
    try:
        conn = await db.get_connection(DB_PATH)
        data = await db.get_health(conn)
        return data
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)[:200]}, status_code=500)
    finally:
        if conn:
            await conn.close()


@app.get("/", response_class=HTMLResponse)
async def index():
    return RedirectResponse("/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not check_auth(request):
        return _deny()

    conn = await db.get_connection(DB_PATH)
    try:
        tweets = await db.get_pending_tweets(conn)
    finally:
        await conn.close()

    response = templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "tweets": tweets, "send_windows": VALID_SEND_WINDOWS},
    )
    return _set_auth_cookie(response)


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    if not check_auth(request):
        return _deny()

    conn = await db.get_connection(DB_PATH)
    try:
        stats = await db.get_stats(conn)
        cycles = await db.get_cycle_history(conn, limit=20)
    finally:
        await conn.close()

    response = templates.TemplateResponse(
        "stats.html",
        {"request": request, "stats": stats, "cycles": cycles},
    )
    return _set_auth_cookie(response)


@app.post("/approve")
async def approve(
    request: Request,
    tweet_id: str = Form(...),
    variant_id: int = Form(...),
    reply_text: str = Form(...),
    send_window: str = Form(...),
):
    if not check_auth(request):
        return _deny()

    text = reply_text.strip()
    if not text:
        return JSONResponse({"error": "Reply text cannot be empty"}, status_code=400)
    if len(text) > 280:
        return JSONResponse({"error": f"Reply exceeds 280 chars ({len(text)})"}, status_code=400)
    if send_window not in VALID_SEND_WINDOWS:
        return JSONResponse({"error": "Invalid send window"}, status_code=400)

    conn = await db.get_connection(DB_PATH)
    try:
        scheduled = _next_send_time(send_window)
        ok = await db.approve_variant(conn, tweet_id, variant_id, text, scheduled, send_window)
    finally:
        await conn.close()

    if not ok:
        return JSONResponse({"error": "Tweet not pending or variant not found"}, status_code=409)

    return RedirectResponse("/dashboard", status_code=303)


@app.post("/skip")
async def skip(request: Request, tweet_id: str = Form(...)):
    if not check_auth(request):
        return _deny()

    conn = await db.get_connection(DB_PATH)
    try:
        ok = await db.skip_tweet(conn, tweet_id)
    finally:
        await conn.close()

    if not ok:
        return JSONResponse({"error": "Tweet not found or already handled"}, status_code=409)

    return RedirectResponse("/dashboard", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=False)
