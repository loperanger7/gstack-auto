"""Tests for db.py — database operations (multi-tenant)."""

import pytest
from datetime import datetime, timedelta, timezone

import db


@pytest.mark.asyncio
async def test_upsert_tweet_new(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    result = await db.upsert_tweet(
        conn, tweet_id="t1", author_id="a1", author_name="Alice",
        follower_count=1000, text="Hello gstack", user_id=user["id"],
    )
    assert result is True
    tweets = await db.get_pending_tweets(conn, user_id=user["id"])
    assert len(tweets) == 1
    assert tweets[0]["id"] == "t1"
    assert tweets[0]["author_name"] == "Alice"
    assert tweets[0]["follower_count"] == 1000


@pytest.mark.asyncio
async def test_upsert_tweet_duplicate(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "Alice", 1000, "Hello", user_id=user["id"])
    result = await db.upsert_tweet(conn, "t1", "a1", "Alice", 1000, "Hello again", user_id=user["id"])
    assert result is False
    tweets = await db.get_pending_tweets(conn, user_id=user["id"])
    assert len(tweets) == 1
    assert tweets[0]["text"] == "Hello"


@pytest.mark.asyncio
async def test_upsert_tweet_rejects_empty_id(conn):
    result = await db.upsert_tweet(conn, "", "a1", "Alice", 100, "text")
    assert result is False


@pytest.mark.asyncio
async def test_upsert_tweet_sanitizes_negative_followers(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "Alice", -50, "text", user_id=user["id"])
    tweets = await db.get_pending_tweets(conn, user_id=user["id"])
    assert tweets[0]["follower_count"] == 0


@pytest.mark.asyncio
async def test_cooldown_within_window(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.update_cooldown(conn, "a1", user_id=user["id"])
    on_cooldown = await db.check_cooldown(conn, "a1", cooldown_days=7, user_id=user["id"])
    assert on_cooldown is True


@pytest.mark.asyncio
async def test_cooldown_expired(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    await conn.execute(
        "INSERT INTO cooldowns (author_id, user_id, last_replied_at) VALUES (?, ?, ?)",
        ("a1", user["id"], old_time),
    )
    await conn.commit()
    on_cooldown = await db.check_cooldown(conn, "a1", cooldown_days=7, user_id=user["id"])
    assert on_cooldown is False


@pytest.mark.asyncio
async def test_cooldown_no_record(conn):
    on_cooldown = await db.check_cooldown(conn, "unknown-author")
    assert on_cooldown is False


@pytest.mark.asyncio
async def test_get_pending_ordered_by_followers(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    uid = user["id"]
    await db.upsert_tweet(conn, "t1", "a1", "Low", 100, "text1", user_id=uid)
    await db.upsert_tweet(conn, "t2", "a2", "High", 50000, "text2", user_id=uid)
    await db.upsert_tweet(conn, "t3", "a3", "Mid", 5000, "text3", user_id=uid)
    tweets = await db.get_pending_tweets(conn, user_id=uid)
    followers = [t["follower_count"] for t in tweets]
    assert followers == [50000, 5000, 100]


@pytest.mark.asyncio
async def test_approve_variant_sets_status(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    variant_id = tweets[0]["variants"][0]["id"]
    reply_id = await db.approve_variant(
        conn, "tweet-1", variant_id, "Thanks!"
    )
    assert reply_id is not None
    pending = await db.get_pending_tweets(conn)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_approve_variant_wrong_tweet(conn_with_tweet):
    conn = conn_with_tweet
    reply_id = await db.approve_variant(
        conn, "tweet-1", 99999, "Thanks!"
    )
    assert reply_id is None


@pytest.mark.asyncio
async def test_approve_variant_over_280(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    vid = tweets[0]["variants"][0]["id"]
    reply_id = await db.approve_variant(
        conn, "tweet-1", vid, "x" * 281
    )
    assert reply_id is None


@pytest.mark.asyncio
async def test_mark_stale(conn_with_tweet):
    conn = conn_with_tweet
    await db.mark_stale(conn, "tweet-1")
    pending = await db.get_pending_tweets(conn)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_skip_tweet(conn_with_tweet):
    conn = conn_with_tweet
    ok = await db.skip_tweet(conn, "tweet-1")
    assert ok is True
    pending = await db.get_pending_tweets(conn)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_skip_tweet_already_skipped(conn_with_tweet):
    conn = conn_with_tweet
    await db.skip_tweet(conn, "tweet-1")
    ok = await db.skip_tweet(conn, "tweet-1")
    assert ok is False


@pytest.mark.asyncio
async def test_save_variants_limits_to_three(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "Alice", 100, "text", user_id=user["id"])
    count = await db.save_variants(conn, "t1", [
        {"label": "A", "text": "one"},
        {"label": "B", "text": "two"},
        {"label": "C", "text": "three"},
        {"label": "D", "text": "four"},
    ])
    assert count == 3


@pytest.mark.asyncio
async def test_save_variants_skips_empty(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.upsert_tweet(conn, "t1", "a1", "Alice", 100, "text", user_id=user["id"])
    count = await db.save_variants(conn, "t1", [
        {"label": "A", "text": ""},
        {"label": "B", "text": "valid"},
    ])
    assert count == 1


# --- Multi-tenant user tests ---

@pytest.mark.asyncio
async def test_get_or_create_user_new(conn):
    user = await db.get_or_create_user(conn, "alice@test.com", name="Alice")
    assert user["email"] == "alice@test.com"
    assert user["name"] == "Alice"
    assert user["id"] > 0


@pytest.mark.asyncio
async def test_get_or_create_user_existing(conn):
    u1 = await db.get_or_create_user(conn, "alice@test.com", name="Alice")
    u2 = await db.get_or_create_user(conn, "alice@test.com", name="Alice Updated")
    assert u1["id"] == u2["id"]


@pytest.mark.asyncio
async def test_get_or_create_user_case_insensitive(conn):
    u1 = await db.get_or_create_user(conn, "Alice@Test.COM")
    u2 = await db.get_or_create_user(conn, "alice@test.com")
    assert u1["id"] == u2["id"]


@pytest.mark.asyncio
async def test_get_or_create_user_empty_email(conn):
    with pytest.raises(ValueError):
        await db.get_or_create_user(conn, "")


@pytest.mark.asyncio
async def test_update_user(conn):
    user = await db.get_or_create_user(conn, "alice@test.com")
    ok = await db.update_user(conn, user["id"], tone="witty", onboard_step=2)
    assert ok is True
    updated = await db.get_user_by_id(conn, user["id"])
    assert updated["tone"] == "witty"
    assert updated["onboard_step"] == 2


@pytest.mark.asyncio
async def test_update_user_rejects_unknown_fields(conn):
    user = await db.get_or_create_user(conn, "alice@test.com")
    ok = await db.update_user(conn, user["id"], sql_injection="drop table")
    assert ok is False


@pytest.mark.asyncio
async def test_get_user_by_id_invalid(conn):
    assert await db.get_user_by_id(conn, -1) is None
    assert await db.get_user_by_id(conn, 99999) is None


@pytest.mark.asyncio
async def test_tenant_isolation(conn):
    """User A cannot see user B's tweets."""
    ua = await db.get_or_create_user(conn, "a@test.com")
    ub = await db.get_or_create_user(conn, "b@test.com")
    await db.upsert_tweet(conn, "t1", "auth1", "Author1", 100, "text1", user_id=ua["id"])
    await db.upsert_tweet(conn, "t2", "auth2", "Author2", 200, "text2", user_id=ub["id"])
    tweets_a = await db.get_pending_tweets(conn, user_id=ua["id"])
    tweets_b = await db.get_pending_tweets(conn, user_id=ub["id"])
    assert len(tweets_a) == 1
    assert tweets_a[0]["id"] == "t1"
    assert len(tweets_b) == 1
    assert tweets_b[0]["id"] == "t2"


@pytest.mark.asyncio
async def test_cooldown_per_user(conn):
    """Cooldown is per-user — same author can be replied to by different users."""
    ua = await db.get_or_create_user(conn, "a@test.com")
    ub = await db.get_or_create_user(conn, "b@test.com")
    await db.update_cooldown(conn, "author1", user_id=ua["id"])
    assert await db.check_cooldown(conn, "author1", user_id=ua["id"]) is True
    assert await db.check_cooldown(conn, "author1", user_id=ub["id"]) is False


# --- Query CRUD tests ---

@pytest.mark.asyncio
async def test_save_and_get_queries(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    count = await db.save_user_queries(conn, user["id"], ["gstack", '"g-stack"', "test query"])
    assert count == 3
    queries = await db.get_user_queries(conn, user["id"])
    assert len(queries) == 3
    assert queries[0]["query_text"] == "gstack"


@pytest.mark.asyncio
async def test_save_queries_replaces_old(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    await db.save_user_queries(conn, user["id"], ["old1", "old2"])
    await db.save_user_queries(conn, user["id"], ["new1"])
    queries = await db.get_user_queries(conn, user["id"])
    assert len(queries) == 1
    assert queries[0]["query_text"] == "new1"


@pytest.mark.asyncio
async def test_save_queries_max_20(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    count = await db.save_user_queries(conn, user["id"], [f"q{i}" for i in range(30)])
    assert count == 20


@pytest.mark.asyncio
async def test_save_queries_skips_empty(conn):
    user = await db.get_or_create_user(conn, "u@test.com")
    count = await db.save_user_queries(conn, user["id"], ["valid", "", "  ", "also valid"])
    assert count == 2


# --- Stats scoped ---

@pytest.mark.asyncio
async def test_stats_scoped_to_user(conn):
    ua = await db.get_or_create_user(conn, "a@test.com")
    ub = await db.get_or_create_user(conn, "b@test.com")
    await db.upsert_tweet(conn, "t1", "auth1", "A1", 100, "t1", user_id=ua["id"])
    await db.upsert_tweet(conn, "t2", "auth2", "A2", 200, "t2", user_id=ub["id"])
    stats_a = await db.get_stats(conn, user_id=ua["id"])
    stats_b = await db.get_stats(conn, user_id=ub["id"])
    assert stats_a["total"] == 1
    assert stats_b["total"] == 1


@pytest.mark.asyncio
async def test_engagement_leaderboard(conn):
    ua = await db.get_or_create_user(conn, "a@test.com", name="Alice")
    ub = await db.get_or_create_user(conn, "b@test.com", name="Bob")
    leaderboard = await db.get_engagement_leaderboard(conn)
    assert len(leaderboard) == 2


@pytest.mark.asyncio
async def test_get_all_active_users(conn):
    u = await db.get_or_create_user(conn, "a@test.com")
    # No twitter tokens yet
    active = await db.get_all_active_users(conn)
    assert len(active) == 0
    # Add tokens
    await db.update_user(conn, u["id"], twitter_access_token="tok", twitter_access_secret="sec")
    active = await db.get_all_active_users(conn)
    assert len(active) == 1


@pytest.mark.asyncio
async def test_cycle_scoped_to_user(conn):
    ua = await db.get_or_create_user(conn, "a@test.com")
    ub = await db.get_or_create_user(conn, "b@test.com")
    c1 = await db.start_cycle(conn, user_id=ua["id"])
    await db.end_cycle(conn, c1, tweets_found=5)
    c2 = await db.start_cycle(conn, user_id=ub["id"])
    await db.end_cycle(conn, c2, tweets_found=3)
    history_a = await db.get_cycle_history(conn, user_id=ua["id"])
    history_b = await db.get_cycle_history(conn, user_id=ub["id"])
    assert len(history_a) == 1
    assert history_a[0]["tweets_found"] == 5
    assert len(history_b) == 1
    assert history_b[0]["tweets_found"] == 3
