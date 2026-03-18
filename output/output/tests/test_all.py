"""Comprehensive test suite — db, twitter, drafter, app logic.
Multi-tenant version."""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

import db
import twitter
import drafter


# ============================================================
# DB TESTS
# ============================================================

@pytest_asyncio.fixture
async def conn():
    """Fresh in-memory DB for each test."""
    c = await db.get_connection(":memory:")
    await db.init_db(c)
    yield c
    await c.close()


@pytest.mark.asyncio
async def test_schema_creation(conn):
    """Fresh DB has all 8 tables including schema_version and users."""
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in await cursor.fetchall()]
    for expected in ["tweets", "variants", "replies", "cooldowns", "engagement",
                     "cycles", "schema_version", "users", "queries"]:
        assert expected in tables, f"Missing table: {expected}"


@pytest.mark.asyncio
async def test_wal_mode_enforced():
    """WAL mode is set on file-based connection."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    try:
        c = await db.get_connection(path)
        await db.init_db(c)
        cursor = await c.execute("PRAGMA journal_mode")
        mode = (await cursor.fetchone())[0]
        assert mode == "wal"
        await c.close()
    finally:
        for f in [path, path + "-wal", path + "-shm"]:
            if os.path.exists(f):
                os.unlink(f)


@pytest.mark.asyncio
async def test_dedup_rejects_duplicate_tweet_id(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    ok1 = await db.upsert_tweet(conn, "t1", "a1", "user1", 100, "hello gstack", user_id=user["id"])
    ok2 = await db.upsert_tweet(conn, "t1", "a1", "user1", 100, "hello gstack", user_id=user["id"])
    assert ok1 is True
    assert ok2 is False


@pytest.mark.asyncio
async def test_dedup_rejects_empty_ids(conn):
    ok = await db.upsert_tweet(conn, "", "a1", "user", 0, "text")
    assert ok is False
    ok = await db.upsert_tweet(conn, "t1", "", "user", 0, "text")
    assert ok is False


@pytest.mark.asyncio
async def test_cooldown_filters_recent_author(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    await conn.execute(
        "INSERT INTO cooldowns (author_id, user_id, last_replied_at) VALUES (?, ?, ?)",
        ("author1", user["id"], three_days_ago),
    )
    await conn.commit()
    assert await db.check_cooldown(conn, "author1", 7, user_id=user["id"]) is True


@pytest.mark.asyncio
async def test_cooldown_allows_expired_author(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    eight_days_ago = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    await conn.execute(
        "INSERT INTO cooldowns (author_id, user_id, last_replied_at) VALUES (?, ?, ?)",
        ("author2", user["id"], eight_days_ago),
    )
    await conn.commit()
    assert await db.check_cooldown(conn, "author2", 7, user_id=user["id"]) is False


@pytest.mark.asyncio
async def test_cooldown_new_author_not_on_cooldown(conn):
    assert await db.check_cooldown(conn, "never-seen", 7) is False


@pytest.mark.asyncio
async def test_save_variants_limits_to_3(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text", user_id=user["id"])
    count = await db.save_variants(conn, "t1", [
        {"text": "v1", "label": "A"},
        {"text": "v2", "label": "B"},
        {"text": "v3", "label": "C"},
        {"text": "v4", "label": "D"},
    ])
    assert count == 3


@pytest.mark.asyncio
async def test_approve_sets_chosen_and_creates_reply(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text", user_id=user["id"])
    await db.save_variants(conn, "t1", [{"text": "reply text", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]
    ok = await db.approve_variant(
        conn, "t1", vid, "reply text",
        datetime.now(timezone.utc).isoformat(), "morning"
    )
    assert ok is True
    cursor = await conn.execute("SELECT chosen FROM variants WHERE id = ?", (vid,))
    assert (await cursor.fetchone())[0] == 1


@pytest.mark.asyncio
async def test_approve_rejects_invalid_window(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text", user_id=user["id"])
    await db.save_variants(conn, "t1", [{"text": "hi", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]
    ok = await db.approve_variant(
        conn, "t1", vid, "hi",
        datetime.now(timezone.utc).isoformat(), "midnight"
    )
    assert ok is False


@pytest.mark.asyncio
async def test_approve_rejects_long_reply(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text", user_id=user["id"])
    await db.save_variants(conn, "t1", [{"text": "x" * 281, "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]
    ok = await db.approve_variant(
        conn, "t1", vid, "x" * 281,
        datetime.now(timezone.utc).isoformat(), "morning"
    )
    assert ok is False


@pytest.mark.asyncio
async def test_skip_tweet(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text", user_id=user["id"])
    ok = await db.skip_tweet(conn, "t1")
    assert ok is True
    ok2 = await db.skip_tweet(conn, "t1")
    assert ok2 is False


@pytest.mark.asyncio
async def test_upsert_engagement(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text", user_id=user["id"])
    await db.save_variants(conn, "t1", [{"text": "reply", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await db.approve_variant(conn, "t1", vid, "reply", past, "morning")
    cursor = await conn.execute("SELECT id FROM replies LIMIT 1")
    rid = (await cursor.fetchone())[0]
    await db.upsert_engagement(conn, rid, 5, 2)
    cursor = await conn.execute("SELECT likes, retweets FROM engagement WHERE reply_id=?", (rid,))
    row = await cursor.fetchone()
    assert row["likes"] == 5
    await db.upsert_engagement(conn, rid, 10, 3)
    cursor = await conn.execute("SELECT likes FROM engagement WHERE reply_id=?", (rid,))
    assert (await cursor.fetchone())["likes"] == 10


@pytest.mark.asyncio
async def test_cycle_tracking(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    cid = await db.start_cycle(conn, user_id=user["id"])
    assert cid > 0
    await db.end_cycle(conn, cid, tweets_found=5, drafts_created=3)
    history = await db.get_cycle_history(conn, user_id=user["id"])
    assert len(history) == 1
    assert history[0]["tweets_found"] == 5


@pytest.mark.asyncio
async def test_get_pending_tweets_order(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    uid = user["id"]
    await db.upsert_tweet(conn, "t1", "a1", "small", 10, "text1", user_id=uid)
    await db.upsert_tweet(conn, "t2", "a2", "big", 10000, "text2", user_id=uid)
    tweets = await db.get_pending_tweets(conn, user_id=uid)
    assert tweets[0]["follower_count"] == 10000


@pytest.mark.asyncio
async def test_get_stats(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    uid = user["id"]
    await db.upsert_tweet(conn, "t1", "a1", "u", 0, "text", user_id=uid)
    await db.upsert_tweet(conn, "t2", "a2", "u", 0, "text2", user_id=uid)
    await db.skip_tweet(conn, "t2")
    stats = await db.get_stats(conn, user_id=uid)
    assert stats["pending"] == 1
    assert stats["skipped"] == 1
    assert stats["total"] == 2


@pytest.mark.asyncio
async def test_get_health(conn):
    health = await db.get_health(conn)
    assert health["status"] == "ok"
    assert "total_users" in health


@pytest.mark.asyncio
async def test_mark_stale(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "u", 0, "text", user_id=user["id"])
    await db.mark_stale(conn, "t1")
    cursor = await conn.execute("SELECT status FROM tweets WHERE id='t1'")
    assert (await cursor.fetchone())[0] == "stale"


# ============================================================
# TWITTER TESTS
# ============================================================

@pytest.fixture(autouse=True)
def reset_twitter_budget():
    twitter.reset_budget()
    yield
    twitter.reset_budget()


@pytest.mark.asyncio
async def test_oauth_signature_format():
    import base64
    sig = twitter._oauth_signature(
        "GET", "https://api.twitter.com/2/tweets",
        {"oauth_consumer_key": "key", "oauth_timestamp": "123"},
        "secret", "token_secret",
    )
    assert len(sig) > 0
    base64.b64decode(sig)


@pytest.mark.asyncio
async def test_oauth_header_contains_required_params():
    creds = {"consumer_key": "ck", "consumer_secret": "cs", "token": "tk", "token_secret": "ts"}
    header = twitter._oauth_header("GET", "https://example.com", creds)
    assert header.startswith("OAuth ")
    assert "oauth_consumer_key" in header
    assert "oauth_signature" in header


@pytest.mark.asyncio
async def test_rate_budget_blocks_at_limit():
    twitter._rate_budget["count"] = twitter.RATE_LIMIT
    twitter._rate_budget["window_start"] = time.monotonic()
    assert twitter._check_budget() is False


@pytest.mark.asyncio
async def test_rate_budget_resets_after_window():
    twitter._rate_budget["count"] = twitter.RATE_LIMIT
    twitter._rate_budget["window_start"] = time.monotonic() - 1000
    assert twitter._check_budget() is True


@pytest.mark.asyncio
async def test_post_reply_validates_length():
    import httpx
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.TwitterError):
            await twitter.post_reply(client, "t1", "x" * 281)


@pytest.mark.asyncio
async def test_post_reply_rejects_empty():
    import httpx
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.TwitterError):
            await twitter.post_reply(client, "t1", "")


# ============================================================
# DRAFTER TESTS
# ============================================================

@pytest.mark.asyncio
async def test_parse_variants_valid_json():
    raw = '[{"label": "A", "text": "Great stuff!"}, {"label": "B", "text": "Nice work!"}]'
    result = drafter._parse_variants(raw)
    assert len(result) == 2
    assert result[0]["label"] == "A"


@pytest.mark.asyncio
async def test_parse_variants_strips_code_fence():
    raw = '```json\n[{"label": "A", "text": "reply"}]\n```'
    result = drafter._parse_variants(raw)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_parse_variants_rejects_over_280():
    raw = json.dumps([{"label": "A", "text": "x" * 281}])
    result = drafter._parse_variants(raw)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_xml_escape():
    assert "&lt;" in drafter._xml_escape("<script>")
    assert "&amp;" in drafter._xml_escape("a&b")


@pytest.mark.asyncio
async def test_classify_sentiment_mock():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="praise")]
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    result = await drafter.classify_sentiment(mock_client, "gstack is amazing!")
    assert result == "praise"


@pytest.mark.asyncio
async def test_draft_variants_mock():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='[{"label": "A", "text": "Thanks!"}, {"label": "B", "text": "Check out gstack-auto!"}]'
    )]
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    result = await drafter.draft_variants(
        mock_client, "gstack is cool", "User", "user1", "praise"
    )
    assert len(result) == 2


# ============================================================
# APP AUTH TESTS (session-based)
# ============================================================

@pytest.mark.asyncio
async def test_auth_check_rejects_no_credentials():
    from app import check_auth
    mock_request = MagicMock()
    mock_request.session = {}
    assert check_auth(mock_request) is False


@pytest.mark.asyncio
async def test_auth_check_accepts_valid_session():
    from app import check_auth
    mock_request = MagicMock()
    mock_request.session = {"user_id": 1}
    assert check_auth(mock_request) is True


@pytest.mark.asyncio
async def test_auth_check_rejects_invalid_session():
    from app import check_auth
    mock_request = MagicMock()
    mock_request.session = {"user_id": -1}
    assert check_auth(mock_request) is False


@pytest.mark.asyncio
async def test_send_window_logic():
    from app import _next_send_time
    result = _next_send_time("morning")
    parsed = datetime.fromisoformat(result)
    assert parsed > datetime.now(timezone.utc) - timedelta(days=2)


@pytest.mark.asyncio
async def test_send_window_logic_all_windows():
    from app import _next_send_time
    for window in ("morning", "lunch", "evening"):
        result = _next_send_time(window)
        datetime.fromisoformat(result)


# ============================================================
# INTEGRATION-STYLE TESTS
# ============================================================

@pytest.mark.asyncio
async def test_full_cycle_search_to_pending(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    uid = user["id"]
    ok = await db.upsert_tweet(conn, "t100", "a100", "testauthor", 5000, "gstack is great", user_id=uid)
    assert ok is True
    on_cd = await db.check_cooldown(conn, "a100", 7, user_id=uid)
    assert on_cd is False
    count = await db.save_variants(conn, "t100", [
        {"text": "Thanks!", "label": "A"},
        {"text": "Check out gstack-auto", "label": "B"},
    ])
    assert count == 2
    pending = await db.get_pending_tweets(conn, user_id=uid)
    assert any(t["id"] == "t100" for t in pending)


@pytest.mark.asyncio
async def test_full_cycle_approve_to_send(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    uid = user["id"]
    await db.upsert_tweet(conn, "t200", "a200", "author200", 1000, "text", user_id=uid)
    await db.save_variants(conn, "t200", [{"text": "my reply", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't200'")
    vid = (await cursor.fetchone())[0]
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    ok = await db.approve_variant(conn, "t200", vid, "my reply", past, "morning")
    assert ok is True
    queue = await db.get_send_queue(conn)
    assert len(queue) == 1
    await db.mark_sent(conn, queue[0]["reply_id"], "tw-reply-999")
    await db.update_cooldown(conn, "a200", user_id=uid)
    queue2 = await db.get_send_queue(conn)
    assert len(queue2) == 0
    assert await db.check_cooldown(conn, "a200", 7, user_id=uid) is True


# ============================================================
# HEALTH ENRICHMENT TESTS
# ============================================================

@pytest.mark.asyncio
async def test_health_includes_error_count_24h(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    cid = await db.start_cycle(conn, user_id=user["id"])
    await db.end_cycle(conn, cid, errors="test error")
    health = await db.get_health(conn)
    assert health["error_count_24h"] == 1


@pytest.mark.asyncio
async def test_health_includes_total_users(conn):
    await db.get_or_create_user(conn, "a@test.com")
    await db.get_or_create_user(conn, "b@test.com")
    health = await db.get_health(conn)
    assert health["total_users"] == 2
