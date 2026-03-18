"""Tests for db.py — database operations."""

import pytest
from datetime import datetime, timedelta, timezone

import db


@pytest.mark.asyncio
async def test_upsert_tweet_new(conn):
    result = await db.upsert_tweet(
        conn, tweet_id="t1", author_id="a1", author_name="Alice",
        follower_count=1000, text="Hello gstack",
    )
    assert result is True
    tweets = await db.get_pending_tweets(conn)
    assert len(tweets) == 1
    assert tweets[0]["id"] == "t1"
    assert tweets[0]["author_name"] == "Alice"
    assert tweets[0]["follower_count"] == 1000


@pytest.mark.asyncio
async def test_upsert_tweet_duplicate(conn):
    await db.upsert_tweet(conn, "t1", "a1", "Alice", 1000, "Hello")
    result = await db.upsert_tweet(conn, "t1", "a1", "Alice", 1000, "Hello again")
    # INSERT OR IGNORE — second insert is silently ignored
    tweets = await db.get_pending_tweets(conn)
    assert len(tweets) == 1
    assert tweets[0]["text"] == "Hello"


@pytest.mark.asyncio
async def test_upsert_tweet_rejects_empty_id(conn):
    result = await db.upsert_tweet(conn, "", "a1", "Alice", 100, "text")
    assert result is False


@pytest.mark.asyncio
async def test_upsert_tweet_sanitizes_negative_followers(conn):
    await db.upsert_tweet(conn, "t1", "a1", "Alice", -50, "text")
    tweets = await db.get_pending_tweets(conn)
    assert tweets[0]["follower_count"] == 0


@pytest.mark.asyncio
async def test_cooldown_within_window(conn):
    await db.update_cooldown(conn, "a1")
    on_cooldown = await db.check_cooldown(conn, "a1", cooldown_days=7)
    assert on_cooldown is True


@pytest.mark.asyncio
async def test_cooldown_expired(conn):
    # Manually insert an old cooldown
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    await conn.execute(
        "INSERT INTO cooldowns (author_id, last_replied_at) VALUES (?, ?)",
        ("a1", old_time),
    )
    await conn.commit()
    on_cooldown = await db.check_cooldown(conn, "a1", cooldown_days=7)
    assert on_cooldown is False


@pytest.mark.asyncio
async def test_cooldown_no_record(conn):
    on_cooldown = await db.check_cooldown(conn, "unknown-author")
    assert on_cooldown is False


@pytest.mark.asyncio
async def test_get_pending_ordered_by_followers(conn):
    await db.upsert_tweet(conn, "t1", "a1", "Low", 100, "text1")
    await db.upsert_tweet(conn, "t2", "a2", "High", 50000, "text2")
    await db.upsert_tweet(conn, "t3", "a3", "Mid", 5000, "text3")
    tweets = await db.get_pending_tweets(conn)
    followers = [t["follower_count"] for t in tweets]
    assert followers == [50000, 5000, 100]


@pytest.mark.asyncio
async def test_approve_variant_sets_status(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    variant_id = tweets[0]["variants"][0]["id"]
    ok = await db.approve_variant(
        conn, "tweet-1", variant_id, "Thanks!", "2025-01-01T09:00:00+00:00", "morning"
    )
    assert ok is True
    pending = await db.get_pending_tweets(conn)
    assert len(pending) == 0  # No longer pending


@pytest.mark.asyncio
async def test_approve_variant_wrong_tweet(conn_with_tweet):
    """Approving with wrong variant_id returns False."""
    conn = conn_with_tweet
    ok = await db.approve_variant(
        conn, "tweet-1", 99999, "Thanks!", "2025-01-01T09:00:00+00:00", "morning"
    )
    assert ok is False


@pytest.mark.asyncio
async def test_approve_variant_invalid_window(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    vid = tweets[0]["variants"][0]["id"]
    ok = await db.approve_variant(
        conn, "tweet-1", vid, "Thanks!", "2025-01-01T09:00:00+00:00", "midnight"
    )
    assert ok is False


@pytest.mark.asyncio
async def test_approve_variant_over_280(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    vid = tweets[0]["variants"][0]["id"]
    ok = await db.approve_variant(
        conn, "tweet-1", vid, "x" * 281, "2025-01-01T09:00:00+00:00", "morning"
    )
    assert ok is False


@pytest.mark.asyncio
async def test_get_send_queue_respects_window(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    vid = tweets[0]["variants"][0]["id"]
    # Schedule in the past
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await db.approve_variant(conn, "tweet-1", vid, "Reply!", past, "morning")
    queue = await db.get_send_queue(conn)
    assert len(queue) == 1
    assert queue[0]["reply_text"] == "Reply!"


@pytest.mark.asyncio
async def test_get_send_queue_future_not_ready(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    vid = tweets[0]["variants"][0]["id"]
    future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    await db.approve_variant(conn, "tweet-1", vid, "Reply!", future, "morning")
    queue = await db.get_send_queue(conn)
    assert len(queue) == 0


@pytest.mark.asyncio
async def test_mark_sent(conn_with_tweet):
    conn = conn_with_tweet
    tweets = await db.get_pending_tweets(conn)
    vid = tweets[0]["variants"][0]["id"]
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await db.approve_variant(conn, "tweet-1", vid, "Reply!", past, "morning")
    queue = await db.get_send_queue(conn)
    await db.mark_sent(conn, queue[0]["reply_id"], "twitter-reply-123")
    queue_after = await db.get_send_queue(conn)
    assert len(queue_after) == 0


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
    await db.upsert_tweet(conn, "t1", "a1", "Alice", 100, "text")
    count = await db.save_variants(conn, "t1", [
        {"label": "A", "text": "one"},
        {"label": "B", "text": "two"},
        {"label": "C", "text": "three"},
        {"label": "D", "text": "four"},
    ])
    assert count == 3


@pytest.mark.asyncio
async def test_save_variants_skips_empty(conn):
    await db.upsert_tweet(conn, "t1", "a1", "Alice", 100, "text")
    count = await db.save_variants(conn, "t1", [
        {"label": "A", "text": ""},
        {"label": "B", "text": "valid"},
    ])
    assert count == 1
