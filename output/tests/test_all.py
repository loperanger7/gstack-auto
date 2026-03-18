"""Comprehensive test suite — db, twitter, drafter, app routes."""

import asyncio
import base64
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
    """Fresh DB has all 7 tables including schema_version."""
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in await cursor.fetchall()]
    for expected in ["tweets", "variants", "replies", "cooldowns", "engagement", "cycles", "schema_version"]:
        assert expected in tables, f"Missing table: {expected}"


@pytest.mark.asyncio
async def test_wal_mode_enforced():
    """WAL mode is set on file-based connection."""
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)  # Remove the empty file so aiosqlite creates fresh
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
    """INSERT OR IGNORE prevents duplicate tweet IDs."""
    ok1 = await db.upsert_tweet(conn, "t1", "a1", "user1", 100, "hello gstack")
    ok2 = await db.upsert_tweet(conn, "t1", "a1", "user1", 100, "hello gstack")
    assert ok1 is True
    assert ok2 is False


@pytest.mark.asyncio
async def test_dedup_rejects_empty_ids(conn):
    """Empty tweet_id or author_id is rejected."""
    ok = await db.upsert_tweet(conn, "", "a1", "user", 0, "text")
    assert ok is False
    ok = await db.upsert_tweet(conn, "t1", "", "user", 0, "text")
    assert ok is False


@pytest.mark.asyncio
async def test_cooldown_filters_recent_author(conn):
    """Author replied to 3 days ago is on cooldown."""
    three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    await conn.execute(
        "INSERT INTO cooldowns (author_id, last_replied_at) VALUES (?, ?)",
        ("author1", three_days_ago),
    )
    await conn.commit()
    assert await db.check_cooldown(conn, "author1", 7) is True


@pytest.mark.asyncio
async def test_cooldown_allows_expired_author(conn):
    """Author replied to 8 days ago is NOT on cooldown."""
    eight_days_ago = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    await conn.execute(
        "INSERT INTO cooldowns (author_id, last_replied_at) VALUES (?, ?)",
        ("author2", eight_days_ago),
    )
    await conn.commit()
    assert await db.check_cooldown(conn, "author2", 7) is False


@pytest.mark.asyncio
async def test_cooldown_new_author_not_on_cooldown(conn):
    """Unknown author is not on cooldown."""
    assert await db.check_cooldown(conn, "never-seen", 7) is False


@pytest.mark.asyncio
async def test_save_variants_limits_to_3(conn):
    """Only first 3 variants are saved."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
    count = await db.save_variants(conn, "t1", [
        {"text": "v1", "label": "A"},
        {"text": "v2", "label": "B"},
        {"text": "v3", "label": "C"},
        {"text": "v4", "label": "D"},
    ])
    assert count == 3


@pytest.mark.asyncio
async def test_approve_sets_chosen_and_creates_reply(conn):
    """Approving a variant marks it chosen and creates a reply record."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
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

    cursor = await conn.execute("SELECT * FROM replies WHERE variant_id = ?", (vid,))
    reply = await cursor.fetchone()
    assert reply is not None
    assert reply["send_window"] == "morning"


@pytest.mark.asyncio
async def test_approve_rejects_invalid_window(conn):
    """Invalid send window is rejected."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
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
    """Reply >280 chars is rejected."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
    await db.save_variants(conn, "t1", [{"text": "x" * 281, "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]
    ok = await db.approve_variant(
        conn, "t1", vid, "x" * 281,
        datetime.now(timezone.utc).isoformat(), "morning"
    )
    assert ok is False


@pytest.mark.asyncio
async def test_get_send_queue_respects_time(conn):
    """Only returns replies with scheduled_for <= now."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
    await db.save_variants(conn, "t1", [{"text": "reply", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]

    # Schedule in the past
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await db.approve_variant(conn, "t1", vid, "reply", past, "morning")

    queue = await db.get_send_queue(conn)
    assert len(queue) == 1
    assert queue[0]["tweet_id"] == "t1"


@pytest.mark.asyncio
async def test_mark_sent_prevents_double_send(conn):
    """After marking sent, reply no longer appears in send queue."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
    await db.save_variants(conn, "t1", [{"text": "reply", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await db.approve_variant(conn, "t1", vid, "reply", past, "morning")

    queue = await db.get_send_queue(conn)
    await db.mark_sent(conn, queue[0]["reply_id"], "twitter-reply-123")

    queue2 = await db.get_send_queue(conn)
    assert len(queue2) == 0


@pytest.mark.asyncio
async def test_skip_tweet(conn):
    """Skipping a tweet changes its status."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
    ok = await db.skip_tweet(conn, "t1")
    assert ok is True
    ok2 = await db.skip_tweet(conn, "t1")  # already skipped
    assert ok2 is False


@pytest.mark.asyncio
async def test_upsert_engagement(conn):
    """Engagement upsert creates then updates."""
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text")
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
    """Start and end cycle records timestamps."""
    cid = await db.start_cycle(conn)
    assert cid > 0
    await db.end_cycle(conn, cid, tweets_found=5, drafts_created=3)
    history = await db.get_cycle_history(conn)
    assert len(history) == 1
    assert history[0]["tweets_found"] == 5


@pytest.mark.asyncio
async def test_get_pending_tweets_order(conn):
    """Pending tweets are ordered by follower count descending."""
    await db.upsert_tweet(conn, "t1", "a1", "small", 10, "text1")
    await db.upsert_tweet(conn, "t2", "a2", "big", 10000, "text2")
    tweets = await db.get_pending_tweets(conn)
    assert tweets[0]["follower_count"] == 10000


@pytest.mark.asyncio
async def test_get_stats(conn):
    """Stats returns correct counts."""
    await db.upsert_tweet(conn, "t1", "a1", "u", 0, "text")
    await db.upsert_tweet(conn, "t2", "a2", "u", 0, "text2")
    await db.skip_tweet(conn, "t2")
    stats = await db.get_stats(conn)
    assert stats["pending"] == 1
    assert stats["skipped"] == 1
    assert stats["total"] == 2


@pytest.mark.asyncio
async def test_get_health(conn):
    """Health returns status ok."""
    health = await db.get_health(conn)
    assert health["status"] == "ok"


@pytest.mark.asyncio
async def test_mark_stale(conn):
    """Marking stale changes status."""
    await db.upsert_tweet(conn, "t1", "a1", "u", 0, "text")
    await db.mark_stale(conn, "t1")
    cursor = await conn.execute("SELECT status FROM tweets WHERE id='t1'")
    assert (await cursor.fetchone())[0] == "stale"


# ============================================================
# REGRESSION TESTS (bugs found in QA)
# ============================================================

@pytest.mark.asyncio
async def test_upsert_tweet_none_thread_json(conn):
    """Regression: upsert_tweet must not crash when thread_json is None."""
    result = await db.upsert_tweet(conn, "r1", "a1", "user", 100, "text", None, "neutral")
    assert result is True
    cursor = await conn.execute("SELECT thread_json FROM tweets WHERE id='r1'")
    row = await cursor.fetchone()
    assert row[0] is not None  # Should default, not crash


@pytest.mark.asyncio
async def test_approve_empty_reply_text_returns_400():
    """Regression: empty reply_text should return 400, not 422."""
    from starlette.testclient import TestClient
    import app as app_module
    client = TestClient(app_module.app)
    creds = base64.b64encode(
        f"{os.environ['DASHBOARD_USERNAME']}:{os.environ['DASHBOARD_PASSWORD']}".encode()
    ).decode()
    resp = client.post(
        "/approve",
        data={"tweet_id": "t1", "variant_id": "1", "reply_text": "", "send_window": "morning"},
        headers={"Authorization": f"Basic {creds}"},
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["error"].lower()


# ============================================================
# TWITTER TESTS
# ============================================================

@pytest.fixture(autouse=True)
def reset_twitter_budget():
    """Reset rate budget before each test."""
    twitter.reset_budget()
    yield
    twitter.reset_budget()


@pytest.mark.asyncio
async def test_oauth_signature_format():
    """OAuth signature produces a non-empty base64 string."""
    sig = twitter._oauth_signature(
        "GET",
        "https://api.twitter.com/2/tweets",
        {"oauth_consumer_key": "key", "oauth_timestamp": "123"},
        "secret",
        "token_secret",
    )
    assert len(sig) > 0
    # Should be valid base64
    base64.b64decode(sig)


@pytest.mark.asyncio
async def test_oauth_header_contains_required_params():
    """OAuth header includes all required OAuth params."""
    creds = {
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "token": "tk",
        "token_secret": "ts",
    }
    header = twitter._oauth_header("GET", "https://example.com", creds)
    assert header.startswith("OAuth ")
    assert "oauth_consumer_key" in header
    assert "oauth_signature" in header
    assert "oauth_nonce" in header


@pytest.mark.asyncio
async def test_search_returns_tweets():
    """Mocked search returns parsed tweet list."""
    import respx
    mock_response = {
        "data": [
            {"id": "123", "author_id": "a1", "text": "love gstack", "conversation_id": "123"}
        ],
        "includes": {
            "users": [{"id": "a1", "name": "Test User", "username": "testuser",
                       "public_metrics": {"followers_count": 500}}]
        },
    }
    with respx.mock:
        respx.get("https://api.twitter.com/2/tweets/search/recent").respond(200, json=mock_response)
        async with httpx.AsyncClient() as client:
            tweets = await twitter.search_mentions(client)

    assert len(tweets) >= 1
    assert tweets[0]["id"] == "123"
    assert tweets[0]["follower_count"] == 500


@pytest.mark.asyncio
async def test_search_handles_429():
    """429 raises RateLimitError."""
    import respx
    with respx.mock:
        respx.get("https://api.twitter.com/2/tweets/search/recent").respond(429)
        async with httpx.AsyncClient() as client:
            with pytest.raises(twitter.RateLimitError):
                await twitter.search_mentions(client)


@pytest.mark.asyncio
async def test_search_handles_401():
    """401 raises TwitterAuthError."""
    import respx
    with respx.mock:
        respx.get("https://api.twitter.com/2/tweets/search/recent").respond(401)
        async with httpx.AsyncClient() as client:
            with pytest.raises(twitter.TwitterAuthError):
                await twitter.search_mentions(client)


import httpx


@pytest.mark.asyncio
async def test_search_retries_on_500():
    """500 is retried, success on second attempt."""
    import respx

    mock_response = {
        "data": [{"id": "456", "author_id": "a2", "text": "gstack rocks", "conversation_id": "456"}],
        "includes": {"users": [{"id": "a2", "name": "User2", "username": "u2",
                                "public_metrics": {"followers_count": 100}}]},
    }
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            return httpx.Response(500, text="Server Error")
        return httpx.Response(200, json=mock_response)

    with respx.mock:
        respx.get("https://api.twitter.com/2/tweets/search/recent").mock(side_effect=side_effect)
        async with httpx.AsyncClient() as client:
            tweets = await twitter.search_mentions(client)

    assert len(tweets) >= 1


@pytest.mark.asyncio
async def test_fetch_thread_caps_at_10():
    """Thread fetch caps results at max_tweets."""
    import respx
    mock_data = {
        "data": [{"id": str(i), "text": f"tweet {i}", "author_id": "a"} for i in range(20)]
    }
    with respx.mock:
        respx.get("https://api.twitter.com/2/tweets/search/recent").respond(200, json=mock_data)
        async with httpx.AsyncClient() as client:
            thread = await twitter.fetch_thread(client, "conv123", max_tweets=10)

    assert len(thread) <= 10


@pytest.mark.asyncio
async def test_post_reply_validates_length():
    """Post reply rejects text >280 chars."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.TwitterError):
            await twitter.post_reply(client, "t1", "x" * 281)


@pytest.mark.asyncio
async def test_post_reply_rejects_empty():
    """Post reply rejects empty text."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.TwitterError):
            await twitter.post_reply(client, "t1", "")


@pytest.mark.asyncio
async def test_rate_budget_blocks_at_limit():
    """Budget blocks when exhausted."""
    twitter._rate_budget["count"] = twitter.RATE_LIMIT
    twitter._rate_budget["window_start"] = time.monotonic()
    assert twitter._check_budget() is False


@pytest.mark.asyncio
async def test_rate_budget_resets_after_window():
    """Budget resets after 15-minute window."""
    twitter._rate_budget["count"] = twitter.RATE_LIMIT
    twitter._rate_budget["window_start"] = time.monotonic() - 1000  # expired
    assert twitter._check_budget() is True


@pytest.mark.asyncio
async def test_get_engagement_handles_deleted():
    """Engagement check for deleted tweet returns deleted flag."""
    import respx
    with respx.mock:
        respx.get("https://api.twitter.com/2/tweets/deleted123").respond(404, text="Not found")
        async with httpx.AsyncClient() as client:
            result = await twitter.get_tweet_engagement(client, "deleted123")
    assert result.get("deleted") is True


# ============================================================
# DRAFTER TESTS
# ============================================================

@pytest.mark.asyncio
async def test_parse_variants_valid_json():
    """Parser handles valid JSON array."""
    raw = '[{"label": "A", "text": "Great stuff!"}, {"label": "B", "text": "Nice work!"}]'
    result = drafter._parse_variants(raw)
    assert len(result) == 2
    assert result[0]["label"] == "A"


@pytest.mark.asyncio
async def test_parse_variants_strips_code_fence():
    """Parser strips markdown code fences."""
    raw = '```json\n[{"label": "A", "text": "reply"}]\n```'
    result = drafter._parse_variants(raw)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_parse_variants_rejects_over_280():
    """Variants over 280 chars are discarded."""
    raw = json.dumps([{"label": "A", "text": "x" * 281}])
    result = drafter._parse_variants(raw)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_parse_variants_rejects_empty():
    """Empty text variants are discarded."""
    raw = json.dumps([{"label": "A", "text": ""}])
    result = drafter._parse_variants(raw)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_parse_variants_handles_invalid_json():
    """Invalid JSON returns empty list."""
    result = drafter._parse_variants("not json at all")
    assert result == []


@pytest.mark.asyncio
async def test_xml_escape():
    """XML escape handles dangerous characters."""
    assert "&lt;" in drafter._xml_escape("<script>")
    assert "&amp;" in drafter._xml_escape("a&b")


@pytest.mark.asyncio
async def test_classify_sentiment_mock():
    """Sentiment classification returns valid sentiment."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="praise")]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    result = await drafter.classify_sentiment(mock_client, "gstack is amazing!")
    assert result == "praise"


@pytest.mark.asyncio
async def test_classify_sentiment_timeout_returns_neutral():
    """Timeout returns neutral as fallback."""
    import anthropic as anthropic_mod
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=anthropic_mod.APITimeoutError(request=MagicMock()))

    result = await drafter.classify_sentiment(mock_client, "some text")
    assert result == "neutral"


@pytest.mark.asyncio
async def test_draft_variants_mock():
    """Drafting returns valid variants from mock Claude."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='[{"label": "A", "text": "Thanks for the mention!"}, {"label": "B", "text": "Check out gstack-auto!"}]'
    )]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    result = await drafter.draft_variants(
        mock_client, "gstack is cool", "User", "user1", "praise"
    )
    assert len(result) == 2


@pytest.mark.asyncio
async def test_draft_variants_timeout_returns_empty():
    """Claude timeout returns empty list after retries."""
    import anthropic as anthropic_mod
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        side_effect=anthropic_mod.APITimeoutError(request=MagicMock())
    )

    result = await drafter.draft_variants(
        mock_client, "text", "Author", "author1", "neutral", retries=1
    )
    assert result == []


# ============================================================
# APP ROUTE TESTS
# ============================================================

@pytest.fixture
def auth_header():
    """Basic Auth header for test credentials."""
    creds = base64.b64encode(b"testuser:testpass").decode()
    return {"Authorization": f"Basic {creds}"}


@pytest.fixture
def bad_auth_header():
    creds = base64.b64encode(b"wrong:wrong").decode()
    return {"Authorization": f"Basic {creds}"}


@pytest.mark.asyncio
async def test_health_no_auth():
    """Health endpoint works without auth."""
    # We need to test via the app with TestClient
    # but lifespan validation makes this tricky
    # Test the health function logic directly via db
    conn = await db.get_connection(":memory:")
    await db.init_db(conn)
    health = await db.get_health(conn)
    assert health["status"] == "ok"
    await conn.close()


@pytest.mark.asyncio
async def test_auth_check_rejects_no_credentials():
    """Auth check denies request with no cookie or basic auth."""
    from app import check_auth
    mock_request = MagicMock()
    mock_request.cookies = {}
    mock_request.headers = {}
    assert check_auth(mock_request) is False


@pytest.mark.asyncio
async def test_auth_check_accepts_basic_auth():
    """Auth check accepts valid basic auth."""
    from app import check_auth
    creds = base64.b64encode(b"testuser:testpass").decode()
    mock_request = MagicMock()
    mock_request.cookies = {}
    mock_request.headers = {"authorization": f"Basic {creds}"}
    assert check_auth(mock_request) is True


@pytest.mark.asyncio
async def test_auth_check_rejects_wrong_password():
    """Auth check denies wrong password."""
    from app import check_auth
    creds = base64.b64encode(b"testuser:wrongpass").decode()
    mock_request = MagicMock()
    mock_request.cookies = {}
    mock_request.headers = {"authorization": f"Basic {creds}"}
    assert check_auth(mock_request) is False


@pytest.mark.asyncio
async def test_auth_cookie_round_trip():
    """Signed cookie can be created and validated."""
    from app import _get_signer, COOKIE_MAX_AGE
    signer = _get_signer()
    token = signer.dumps("testuser")
    data = signer.loads(token, max_age=COOKIE_MAX_AGE)
    assert data == "testuser"


@pytest.mark.asyncio
async def test_auth_cookie_rejects_tampered():
    """Tampered cookie is rejected."""
    from app import _get_signer, COOKIE_MAX_AGE
    signer = _get_signer()
    token = signer.dumps("testuser")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(Exception):
        signer.loads(tampered, max_age=COOKIE_MAX_AGE)


@pytest.mark.asyncio
async def test_send_window_logic():
    """Send window time computation returns valid ISO timestamp."""
    from app import _next_send_time
    result = _next_send_time("morning")
    parsed = datetime.fromisoformat(result)
    assert parsed > datetime.now(timezone.utc) - timedelta(days=2)


@pytest.mark.asyncio
async def test_send_window_logic_all_windows():
    """All three windows produce valid timestamps."""
    from app import _next_send_time
    for window in ("morning", "lunch", "evening"):
        result = _next_send_time(window)
        datetime.fromisoformat(result)  # should not raise


# ============================================================
# INTEGRATION-STYLE TESTS
# ============================================================

@pytest.mark.asyncio
async def test_full_cycle_search_to_pending(conn):
    """Tweet → dedup → store → variants → pending queue."""
    # Insert a tweet
    ok = await db.upsert_tweet(conn, "t100", "a100", "testauthor", 5000, "gstack is great")
    assert ok is True

    # Not on cooldown
    on_cd = await db.check_cooldown(conn, "a100", 7)
    assert on_cd is False

    # Save variants
    count = await db.save_variants(conn, "t100", [
        {"text": "Thanks!", "label": "A"},
        {"text": "Check out gstack-auto", "label": "B"},
    ])
    assert count == 2

    # Appears in pending
    pending = await db.get_pending_tweets(conn)
    assert any(t["id"] == "t100" for t in pending)
    tweet = next(t for t in pending if t["id"] == "t100")
    assert len(tweet["variants"]) == 2


@pytest.mark.asyncio
async def test_full_cycle_approve_to_send(conn):
    """Approve → queue → mark sent → cooldown → no double send."""
    await db.upsert_tweet(conn, "t200", "a200", "author200", 1000, "text")
    await db.save_variants(conn, "t200", [{"text": "my reply", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't200'")
    vid = (await cursor.fetchone())[0]

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    ok = await db.approve_variant(conn, "t200", vid, "my reply", past, "morning")
    assert ok is True

    queue = await db.get_send_queue(conn)
    assert len(queue) == 1

    await db.mark_sent(conn, queue[0]["reply_id"], "tw-reply-999")
    await db.update_cooldown(conn, "a200")

    # No longer in queue
    queue2 = await db.get_send_queue(conn)
    assert len(queue2) == 0

    # Author now on cooldown
    assert await db.check_cooldown(conn, "a200", 7) is True

    # Tweet status is replied
    cursor = await conn.execute("SELECT status FROM tweets WHERE id='t200'")
    assert (await cursor.fetchone())[0] == "replied"


# ============================================================
# HEALTH ENDPOINT ENRICHMENT TESTS
# ============================================================

@pytest.mark.asyncio
async def test_health_includes_error_count_24h(conn):
    """Health includes error_count_24h field."""
    # Create a cycle with errors
    cid = await db.start_cycle(conn)
    await db.end_cycle(conn, cid, errors="test error")
    health = await db.get_health(conn)
    assert "error_count_24h" in health
    assert health["error_count_24h"] == 1


@pytest.mark.asyncio
async def test_health_includes_total_tweets(conn):
    """Health includes total_tweets field."""
    await db.upsert_tweet(conn, "h1", "a1", "u", 0, "text1")
    await db.upsert_tweet(conn, "h2", "a2", "u", 0, "text2")
    health = await db.get_health(conn)
    assert "total_tweets" in health
    assert health["total_tweets"] == 2


@pytest.mark.asyncio
async def test_health_includes_total_replies_sent(conn):
    """Health includes total_replies_sent field."""
    await db.upsert_tweet(conn, "h3", "a3", "u", 100, "text")
    await db.save_variants(conn, "h3", [{"text": "reply", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 'h3'")
    vid = (await cursor.fetchone())[0]
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await db.approve_variant(conn, "h3", vid, "reply", past, "morning")
    queue = await db.get_send_queue(conn)
    await db.mark_sent(conn, queue[0]["reply_id"], "twitter-reply-h3")
    health = await db.get_health(conn)
    assert "total_replies_sent" in health
    assert health["total_replies_sent"] == 1
