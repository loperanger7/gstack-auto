"""Database layer — every SQL statement in the system lives here.
SQLite WAL mode enforced on every connection. All queries are named functions.
Multi-tenant: all tenant tables have user_id FK to users table."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import aiosqlite

log = logging.getLogger(__name__)

DB_PATH = "data/gstack_replies.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    picture TEXT NOT NULL DEFAULT '',
    google_sub TEXT NOT NULL DEFAULT '',
    twitter_access_token TEXT NOT NULL DEFAULT '',
    twitter_access_secret TEXT NOT NULL DEFAULT '',
    twitter_username TEXT NOT NULL DEFAULT '',
    tone TEXT NOT NULL DEFAULT 'professional',
    custom_link TEXT NOT NULL DEFAULT 'https://github.com/loperanger7/gstack-auto',
    is_admin INTEGER NOT NULL DEFAULT 0,
    onboard_step INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    query_text TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tweets (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 0 REFERENCES users(id),
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL DEFAULT '',
    follower_count INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL,
    thread_json TEXT NOT NULL DEFAULT '[]',
    sentiment TEXT NOT NULL DEFAULT 'neutral',
    found_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL REFERENCES tweets(id),
    draft_text TEXT NOT NULL,
    variant_label TEXT NOT NULL,
    chosen INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL REFERENCES tweets(id),
    variant_id INTEGER NOT NULL REFERENCES variants(id),
    reply_text TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    send_window TEXT NOT NULL,
    sent_at TEXT,
    twitter_reply_id TEXT,
    send_attempts INTEGER NOT NULL DEFAULT 0,
    claimed_at TEXT
);

CREATE TABLE IF NOT EXISTS cooldowns (
    author_id TEXT NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 0 REFERENCES users(id),
    last_replied_at TEXT NOT NULL,
    PRIMARY KEY (author_id, user_id)
);

CREATE TABLE IF NOT EXISTS engagement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reply_id INTEGER NOT NULL UNIQUE REFERENCES replies(id),
    likes INTEGER NOT NULL DEFAULT 0,
    retweets INTEGER NOT NULL DEFAULT 0,
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0 REFERENCES users(id),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    tweets_found INTEGER NOT NULL DEFAULT 0,
    drafts_created INTEGER NOT NULL DEFAULT 0,
    errors TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_tweets_status ON tweets(status);
CREATE INDEX IF NOT EXISTS idx_tweets_follower ON tweets(follower_count DESC);
CREATE INDEX IF NOT EXISTS idx_tweets_user ON tweets(user_id);
CREATE INDEX IF NOT EXISTS idx_variants_tweet ON variants(tweet_id);
CREATE INDEX IF NOT EXISTS idx_replies_scheduled ON replies(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_replies_sent ON replies(sent_at);
CREATE INDEX IF NOT EXISTS idx_queries_user ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_cycles_user ON cycles(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

INSERT OR IGNORE INTO schema_version (version) VALUES (2);
"""


async def get_connection(db_path: str = DB_PATH) -> aiosqlite.Connection:
    """Open a connection with WAL mode and foreign keys enforced."""
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def init_db(conn: aiosqlite.Connection) -> None:
    """Create all tables. Safe to call repeatedly."""
    await conn.executescript(SCHEMA)
    await conn.commit()


# ---- User CRUD ----

async def get_or_create_user(
    conn: aiosqlite.Connection,
    email: str,
    name: str = "",
    picture: str = "",
    google_sub: str = "",
) -> dict:
    """Find user by email or create new. Returns user dict."""
    email = str(email).strip().lower()
    if not email:
        raise ValueError("Email is required")

    cursor = await conn.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = await cursor.fetchone()
    if row:
        return dict(row)

    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        """INSERT INTO users (email, name, picture, google_sub, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (email, str(name)[:200], str(picture)[:500], str(google_sub)[:200], now, now),
    )
    await conn.commit()
    cursor = await conn.execute("SELECT * FROM users WHERE email = ?", (email,))
    return dict(await cursor.fetchone())


async def get_user_by_id(conn: aiosqlite.Connection, user_id: int) -> dict | None:
    """Get user by ID. Returns None if not found."""
    if not isinstance(user_id, int) or user_id < 1:
        return None
    cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_user(conn: aiosqlite.Connection, user_id: int, **fields) -> bool:
    """Update user fields. Only allows known columns."""
    allowed = {
        "name", "picture", "twitter_access_token", "twitter_access_secret",
        "twitter_username", "tone", "custom_link", "is_admin",
        "onboard_step", "is_active",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    await conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    await conn.commit()
    return True


async def get_all_active_users(conn: aiosqlite.Connection) -> list[dict]:
    """Get all active users with Twitter credentials configured."""
    cursor = await conn.execute(
        """SELECT * FROM users
           WHERE is_active = 1 AND twitter_access_token != ''
           ORDER BY id"""
    )
    return [dict(r) for r in await cursor.fetchall()]


async def get_all_users(conn: aiosqlite.Connection) -> list[dict]:
    """Get all users for admin panel."""
    cursor = await conn.execute("SELECT * FROM users ORDER BY created_at DESC")
    return [dict(r) for r in await cursor.fetchall()]


# ---- Query CRUD ----

async def get_user_queries(conn: aiosqlite.Connection, user_id: int) -> list[dict]:
    """Get active queries for a user."""
    cursor = await conn.execute(
        "SELECT * FROM queries WHERE user_id = ? AND is_active = 1 ORDER BY id",
        (user_id,),
    )
    return [dict(r) for r in await cursor.fetchall()]


async def save_user_queries(conn: aiosqlite.Connection, user_id: int, query_texts: list[str]) -> int:
    """Replace user's queries. Deactivates old, inserts new. Returns count saved."""
    await conn.execute("UPDATE queries SET is_active = 0 WHERE user_id = ?", (user_id,))
    count = 0
    now = datetime.now(timezone.utc).isoformat()
    for qt in query_texts[:20]:  # max 20 queries per user
        qt = str(qt).strip()[:200]
        if not qt:
            continue
        await conn.execute(
            "INSERT INTO queries (user_id, query_text, created_at) VALUES (?, ?, ?)",
            (user_id, qt, now),
        )
        count += 1
    await conn.commit()
    return count


# ---- Tweet CRUD (user-scoped) ----

async def upsert_tweet(
    conn: aiosqlite.Connection,
    tweet_id: str,
    author_id: str,
    author_name: str,
    follower_count: int,
    text: str,
    thread_json: str = "[]",
    sentiment: str = "neutral",
    user_id: int = 0,
) -> bool:
    """Insert a tweet if not already seen. Returns True if newly inserted."""
    tweet_id = str(tweet_id).strip() if tweet_id else ""
    author_id = str(author_id).strip() if author_id else ""
    if not tweet_id or not author_id:
        log.warning("Refusing to insert tweet with empty id or author_id")
        return False
    allowed_sentiments = {"praise", "question", "criticism", "neutral"}
    if sentiment not in allowed_sentiments:
        sentiment = "neutral"
    try:
        cursor = await conn.execute("SELECT 1 FROM tweets WHERE id = ?", (tweet_id,))
        if await cursor.fetchone():
            return False
        await conn.execute(
            """INSERT OR IGNORE INTO tweets
               (id, user_id, author_id, author_name, follower_count, text,
                thread_json, sentiment, found_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                tweet_id,
                user_id,
                author_id,
                str(author_name)[:200],
                max(0, int(follower_count)),
                str(text)[:10000],
                (thread_json or "[]")[:50000],
                sentiment,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await conn.commit()
        return True
    except aiosqlite.Error as e:
        log.error("upsert_tweet failed for %s: %s", tweet_id, e)
        return False


async def get_pending_tweets(conn: aiosqlite.Connection, user_id: int = 0) -> list[dict]:
    """Return pending tweets with variants, ordered by follower count DESC.
    If user_id is 0, return all (legacy/admin mode)."""
    if user_id:
        cursor = await conn.execute(
            """SELECT id, author_id, author_name, follower_count, text,
                      thread_json, sentiment, found_at
               FROM tweets WHERE status = 'pending' AND user_id = ?
               ORDER BY follower_count DESC""",
            (user_id,),
        )
    else:
        cursor = await conn.execute(
            """SELECT id, author_id, author_name, follower_count, text,
                      thread_json, sentiment, found_at
               FROM tweets WHERE status = 'pending'
               ORDER BY follower_count DESC"""
        )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        tweet = dict(row)
        try:
            tweet["thread"] = json.loads(tweet.pop("thread_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            tweet["thread"] = []
        vcursor = await conn.execute(
            "SELECT id, draft_text, variant_label FROM variants WHERE tweet_id = ?",
            (tweet["id"],),
        )
        tweet["variants"] = [dict(v) for v in await vcursor.fetchall()]
        result.append(tweet)
    return result


async def save_variants(
    conn: aiosqlite.Connection,
    tweet_id: str,
    variants: list[dict],
) -> int:
    """Save draft variants for a tweet. Returns count saved."""
    count = 0
    for v in variants[:3]:
        text = str(v.get("text", ""))[:280]
        label = str(v.get("label", "?"))[:5]
        if not text:
            continue
        await conn.execute(
            "INSERT INTO variants (tweet_id, draft_text, variant_label) VALUES (?, ?, ?)",
            (tweet_id, text, label),
        )
        count += 1
    await conn.commit()
    return count


async def approve_variant(
    conn: aiosqlite.Connection,
    tweet_id: str,
    variant_id: int,
    reply_text: str,
    scheduled_for: str,
    send_window: str,
) -> bool:
    """Approve a variant and queue reply. Returns False if tweet not pending."""
    allowed_windows = {"morning", "lunch", "evening"}
    if send_window not in allowed_windows:
        log.warning("Invalid send_window: %s", send_window)
        return False
    if len(reply_text) > 280:
        log.warning("Reply text exceeds 280 chars, rejecting")
        return False
    cursor = await conn.execute(
        "SELECT id FROM variants WHERE id = ? AND tweet_id = ?",
        (variant_id, tweet_id),
    )
    if not await cursor.fetchone():
        log.warning("Variant %d not found for tweet %s", variant_id, tweet_id)
        return False
    cursor = await conn.execute(
        "UPDATE tweets SET status = 'approved' WHERE id = ? AND status = 'pending'",
        (tweet_id,),
    )
    if cursor.rowcount == 0:
        return False
    await conn.execute(
        "UPDATE variants SET chosen = 1 WHERE id = ?", (variant_id,)
    )
    await conn.execute(
        """INSERT INTO replies (tweet_id, variant_id, reply_text, scheduled_for, send_window)
           VALUES (?, ?, ?, ?, ?)""",
        (tweet_id, variant_id, reply_text, scheduled_for, send_window),
    )
    await conn.commit()
    return True


async def skip_tweet(conn: aiosqlite.Connection, tweet_id: str) -> bool:
    """Mark a tweet as skipped. Returns True if status changed."""
    cursor = await conn.execute(
        "UPDATE tweets SET status = 'skipped' WHERE id = ? AND status = 'pending'",
        (tweet_id,),
    )
    await conn.commit()
    return cursor.rowcount > 0


async def check_cooldown(
    conn: aiosqlite.Connection, author_id: str, cooldown_days: int = 7,
    user_id: int = 0,
) -> bool:
    """Returns True if author is on cooldown for this user."""
    cursor = await conn.execute(
        "SELECT last_replied_at FROM cooldowns WHERE author_id = ? AND user_id = ?",
        (author_id, user_id),
    )
    row = await cursor.fetchone()
    if row is None:
        return False
    if cooldown_days <= 0:
        return True
    last = datetime.fromisoformat(row["last_replied_at"])
    now = datetime.now(timezone.utc)
    return (now - last).days < cooldown_days


async def update_cooldown(conn: aiosqlite.Connection, author_id: str, user_id: int = 0) -> None:
    """Set or refresh cooldown for an author per user."""
    await conn.execute(
        "INSERT OR REPLACE INTO cooldowns (author_id, user_id, last_replied_at) VALUES (?, ?, ?)",
        (author_id, user_id, datetime.now(timezone.utc).isoformat()),
    )
    await conn.commit()


async def get_send_queue(conn: aiosqlite.Connection) -> list[dict]:
    """Return replies ready to send (scheduled time passed, not yet sent)."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = await conn.execute(
        """SELECT r.id as reply_id, r.tweet_id, r.reply_text, r.send_window,
                  t.author_id, t.author_name, t.user_id
           FROM replies r
           JOIN tweets t ON t.id = r.tweet_id
           WHERE r.sent_at IS NULL AND r.scheduled_for <= ?
           ORDER BY r.scheduled_for ASC""",
        (now,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def mark_sent(
    conn: aiosqlite.Connection, reply_id: int, twitter_reply_id: str
) -> None:
    """Mark a reply as sent. Only updates if not already sent (idempotent)."""
    await conn.execute(
        "UPDATE replies SET sent_at = ?, twitter_reply_id = ? WHERE id = ? AND sent_at IS NULL",
        (datetime.now(timezone.utc).isoformat(), str(twitter_reply_id), reply_id),
    )
    await conn.execute(
        """UPDATE tweets SET status = 'replied'
           WHERE id = (SELECT tweet_id FROM replies WHERE id = ?)""",
        (reply_id,),
    )
    await conn.commit()


async def mark_stale(conn: aiosqlite.Connection, tweet_id: str) -> None:
    """Mark a tweet as stale (deleted on Twitter)."""
    await conn.execute(
        "UPDATE tweets SET status = 'stale' WHERE id = ?", (tweet_id,)
    )
    await conn.commit()


async def claim_reply_for_send(conn: aiosqlite.Connection, reply_id: int) -> bool:
    """Atomically claim a reply for sending. Returns True if claimed, False if already claimed or max attempts exceeded."""
    cursor = await conn.execute(
        """UPDATE replies SET claimed_at = ?, send_attempts = send_attempts + 1
           WHERE id = ? AND sent_at IS NULL AND claimed_at IS NULL AND send_attempts < 3
           RETURNING id""",
        (datetime.now(timezone.utc).isoformat(), reply_id),
    )
    row = await cursor.fetchone()
    await conn.commit()
    return row is not None


async def record_send_failure(conn: aiosqlite.Connection, reply_id: int) -> None:
    """Release claim on a reply after a send failure so it can be retried (up to max attempts)."""
    await conn.execute(
        "UPDATE replies SET claimed_at = NULL WHERE id = ?", (reply_id,)
    )
    await conn.commit()


async def upsert_engagement(
    conn: aiosqlite.Connection, reply_id: int, likes: int, retweets: int
) -> None:
    """Insert or update engagement metrics for a reply."""
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        """INSERT INTO engagement (reply_id, likes, retweets, checked_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(reply_id) DO UPDATE SET
               likes = excluded.likes, retweets = excluded.retweets, checked_at = excluded.checked_at""",
        (reply_id, max(0, likes), max(0, retweets), now),
    )
    await conn.commit()


async def get_replies_needing_engagement_check(
    conn: aiosqlite.Connection, hours_ago: int
) -> list[dict]:
    """Get replies sent ~hours_ago that need engagement check."""
    now = datetime.now(timezone.utc)
    window_end = (now - timedelta(hours=hours_ago - 1)).isoformat()
    window_start = (now - timedelta(hours=hours_ago + 1)).isoformat()
    cursor = await conn.execute(
        """SELECT r.id as reply_id, r.twitter_reply_id
           FROM replies r
           WHERE r.sent_at IS NOT NULL
             AND r.twitter_reply_id IS NOT NULL
             AND r.sent_at BETWEEN ? AND ?""",
        (window_start, window_end),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def start_cycle(conn: aiosqlite.Connection, user_id: int = 0) -> int:
    """Record cycle start. Returns cycle_id."""
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO cycles (user_id, started_at) VALUES (?, ?)", (user_id, now)
    )
    await conn.commit()
    cursor = await conn.execute("SELECT last_insert_rowid()")
    row = await cursor.fetchone()
    return row[0]


async def end_cycle(
    conn: aiosqlite.Connection,
    cycle_id: int,
    tweets_found: int = 0,
    drafts_created: int = 0,
    errors: str = "",
) -> None:
    """Record cycle completion."""
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        """UPDATE cycles SET completed_at=?, tweets_found=?, drafts_created=?, errors=?
           WHERE id=?""",
        (now, tweets_found, drafts_created, str(errors)[:1000], cycle_id),
    )
    await conn.commit()


async def get_cycle_history(conn: aiosqlite.Connection, limit: int = 50, user_id: int = 0) -> list[dict]:
    """Get recent cycles, optionally filtered by user."""
    if user_id:
        cursor = await conn.execute(
            "SELECT * FROM cycles WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
    else:
        cursor = await conn.execute(
            "SELECT * FROM cycles ORDER BY id DESC LIMIT ?", (limit,)
        )
    return [dict(r) for r in await cursor.fetchall()]


async def get_stats(conn: aiosqlite.Connection, user_id: int = 0) -> dict:
    """Aggregate stats, optionally scoped to user."""
    user_filter = " AND user_id = ?" if user_id else ""
    user_params = (user_id,) if user_id else ()

    counts = {}
    for status in ("pending", "replied", "skipped", "stale", "approved"):
        cursor = await conn.execute(
            f"SELECT COUNT(*) as c FROM tweets WHERE status=?{user_filter}",
            (status,) + user_params,
        )
        counts[status] = (await cursor.fetchone())["c"]

    cursor = await conn.execute(
        f"SELECT COUNT(*) as c FROM tweets WHERE 1=1{user_filter}", user_params
    )
    counts["total"] = (await cursor.fetchone())["c"]

    # Engagement — join through replies/tweets for user scoping
    if user_id:
        cursor = await conn.execute(
            """SELECT COALESCE(SUM(e.likes),0) as l, COALESCE(SUM(e.retweets),0) as r
               FROM engagement e
               JOIN replies rp ON rp.id = e.reply_id
               JOIN tweets t ON t.id = rp.tweet_id
               WHERE t.user_id = ?""",
            (user_id,),
        )
    else:
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(likes),0) as l, COALESCE(SUM(retweets),0) as r FROM engagement"
        )
    eng = await cursor.fetchone()

    if user_id:
        cursor = await conn.execute(
            """SELECT r.send_window, COUNT(*) as count,
                      COALESCE(SUM(e.likes),0) as likes,
                      COALESCE(SUM(e.retweets),0) as retweets
               FROM replies r
               JOIN tweets t ON t.id = r.tweet_id
               LEFT JOIN engagement e ON e.reply_id = r.id
               WHERE r.sent_at IS NOT NULL AND t.user_id = ?
               GROUP BY r.send_window""",
            (user_id,),
        )
    else:
        cursor = await conn.execute(
            """SELECT r.send_window, COUNT(*) as count,
                      COALESCE(SUM(e.likes),0) as likes,
                      COALESCE(SUM(e.retweets),0) as retweets
               FROM replies r
               LEFT JOIN engagement e ON e.reply_id = r.id
               WHERE r.sent_at IS NOT NULL
               GROUP BY r.send_window"""
        )
    window_stats = [dict(r) for r in await cursor.fetchall()]

    return {
        **counts,
        "total_likes": eng["l"],
        "total_retweets": eng["r"],
        "window_stats": window_stats,
    }


async def get_health(conn: aiosqlite.Connection) -> dict:
    """Health check data with operational metrics."""
    cursor = await conn.execute(
        "SELECT completed_at FROM cycles ORDER BY id DESC LIMIT 1"
    )
    last_cycle = await cursor.fetchone()

    cursor = await conn.execute(
        "SELECT COUNT(*) as c FROM tweets WHERE status='pending'"
    )
    pending = (await cursor.fetchone())["c"]

    cursor = await conn.execute(
        "SELECT errors FROM cycles WHERE errors != '' ORDER BY id DESC LIMIT 1"
    )
    last_error = await cursor.fetchone()

    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cursor = await conn.execute(
        "SELECT COUNT(*) as c FROM cycles WHERE errors != '' AND started_at >= ?",
        (cutoff_24h,),
    )
    error_count_24h = (await cursor.fetchone())["c"]

    cursor = await conn.execute("SELECT COUNT(*) as c FROM tweets")
    total_tweets = (await cursor.fetchone())["c"]

    cursor = await conn.execute(
        "SELECT COUNT(*) as c FROM replies WHERE sent_at IS NOT NULL"
    )
    total_replies_sent = (await cursor.fetchone())["c"]

    cursor = await conn.execute("SELECT COUNT(*) as c FROM users")
    total_users = (await cursor.fetchone())["c"]

    return {
        "status": "ok",
        "last_cycle": last_cycle["completed_at"] if last_cycle else None,
        "pending_queue_depth": pending,
        "last_error": last_error["errors"] if last_error else None,
        "error_count_24h": error_count_24h,
        "total_tweets": total_tweets,
        "total_replies_sent": total_replies_sent,
        "total_users": total_users,
    }


async def get_weekly_digest(conn: aiosqlite.Connection, days: int = 7) -> dict:
    """Data for the weekly digest email."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    cursor = await conn.execute(
        "SELECT COUNT(*) as c FROM tweets WHERE found_at >= ?", (cutoff,)
    )
    tweets_found = (await cursor.fetchone())["c"]

    cursor = await conn.execute(
        """SELECT COUNT(*) as c FROM replies r
           WHERE r.sent_at IS NOT NULL AND r.sent_at >= ?""",
        (cutoff,),
    )
    replies_sent = (await cursor.fetchone())["c"]

    cursor = await conn.execute(
        """SELECT COALESCE(SUM(e.likes),0) as l, COALESCE(SUM(e.retweets),0) as r
           FROM engagement e JOIN replies rp ON rp.id = e.reply_id
           WHERE rp.sent_at >= ?""",
        (cutoff,),
    )
    eng = await cursor.fetchone()

    cursor = await conn.execute(
        """SELECT v.draft_text, t.author_name, t.follower_count,
                  COALESCE(e.likes,0) as likes, COALESCE(e.retweets,0) as retweets
           FROM replies r
           JOIN variants v ON v.id = r.variant_id
           JOIN tweets t ON t.id = r.tweet_id
           LEFT JOIN engagement e ON e.reply_id = r.id
           WHERE r.sent_at >= ?
           ORDER BY COALESCE(e.likes,0)+COALESCE(e.retweets,0) DESC LIMIT 5""",
        (cutoff,),
    )
    top = [dict(r) for r in await cursor.fetchall()]

    cursor = await conn.execute(
        "SELECT COUNT(*) as c FROM cycles WHERE errors != '' AND started_at >= ?",
        (cutoff,),
    )
    errors = (await cursor.fetchone())["c"]

    return {
        "tweets_found": tweets_found,
        "replies_sent": replies_sent,
        "total_likes": eng["l"],
        "total_retweets": eng["r"],
        "top_replies": top,
        "error_cycles": errors,
    }


async def get_engagement_leaderboard(conn: aiosqlite.Connection, limit: int = 20) -> list[dict]:
    """Get engagement leaderboard for admin panel."""
    cursor = await conn.execute(
        """SELECT u.id as user_id, u.email, u.name, u.twitter_username,
                  COUNT(DISTINCT t.id) as tweet_count,
                  COUNT(DISTINCT CASE WHEN t.status='replied' THEN t.id END) as reply_count,
                  COALESCE(SUM(e.likes), 0) as total_likes,
                  COALESCE(SUM(e.retweets), 0) as total_retweets
           FROM users u
           LEFT JOIN tweets t ON t.user_id = u.id
           LEFT JOIN replies r ON r.tweet_id = t.id AND r.sent_at IS NOT NULL
           LEFT JOIN engagement e ON e.reply_id = r.id
           GROUP BY u.id
           ORDER BY total_likes + total_retweets DESC
           LIMIT ?""",
        (limit,),
    )
    return [dict(r) for r in await cursor.fetchall()]
