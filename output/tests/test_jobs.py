"""Tests for jobs.py — scheduled jobs and email sending."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


@pytest_asyncio.fixture
async def job_db(tmp_path):
    """File-based SQLite DB for job tests (not :memory: — needs cross-connection)."""
    db_path = str(tmp_path / "jobs_test.db")
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path
    app_module.DB_PATH = old_path


# ── monitor_cycle ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_monitor_cycle_happy_path(job_db):
    """Monitor cycle finds tweets, classifies, drafts variants, records cycle."""
    import jobs

    mock_mentions = [
        {
            "id": "tweet-mc-1", "author_id": "auth-1",
            "author_name": "User One", "author_username": "user1",
            "follower_count": 500, "text": "gstack is great!",
            "conversation_id": "conv-1",
        },
    ]

    with patch.object(jobs.twitter, "search_mentions", new_callable=AsyncMock, return_value=mock_mentions), \
         patch.object(jobs.twitter, "fetch_thread", new_callable=AsyncMock, return_value=[]), \
         patch.object(jobs.drafter, "classify_sentiment", new_callable=AsyncMock, return_value="praise"), \
         patch.object(jobs.drafter, "draft_variants", new_callable=AsyncMock, return_value=[
             {"label": "A", "text": "Thanks!"},
             {"label": "B", "text": "Love it!"},
         ]), \
         patch("jobs._send_email") as mock_email:

        await jobs.monitor_cycle()

    conn = await db.get_connection(job_db)
    try:
        row = await conn.execute("SELECT * FROM tweets WHERE id = ?", ("tweet-mc-1",))
        tweet = await row.fetchone()
        assert tweet is not None
        assert tweet["sentiment"] == "praise"

        rows = await conn.execute("SELECT * FROM variants WHERE tweet_id = ?", ("tweet-mc-1",))
        variants = await rows.fetchall()
        assert len(variants) == 2

        rows = await conn.execute("SELECT * FROM cycles")
        cycles = await rows.fetchall()
        assert len(cycles) >= 1
        assert cycles[-1]["tweets_found"] == 1
        assert cycles[-1]["drafts_created"] == 2
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_monitor_cycle_skips_duplicate(job_db):
    """Already-seen tweets are not re-drafted."""
    import jobs

    # Pre-insert the tweet
    conn = await db.get_connection(job_db)
    await db.upsert_tweet(conn, tweet_id="tweet-dup", author_id="auth-dup",
                          author_name="Dup", follower_count=100, text="old tweet")
    await conn.close()

    mock_mentions = [
        {"id": "tweet-dup", "author_id": "auth-dup", "author_name": "Dup",
         "follower_count": 100, "text": "old tweet", "conversation_id": "c1"},
    ]

    with patch.object(jobs.twitter, "search_mentions", new_callable=AsyncMock, return_value=mock_mentions), \
         patch.object(jobs.drafter, "classify_sentiment", new_callable=AsyncMock) as mock_classify:
        await jobs.monitor_cycle()

    mock_classify.assert_not_called()


@pytest.mark.asyncio
async def test_monitor_cycle_skips_cooldown(job_db):
    """Author on cooldown is skipped."""
    import jobs

    mock_mentions = [
        {"id": "tweet-cool", "author_id": "auth-cool", "author_name": "Cool",
         "follower_count": 100, "text": "gstack", "conversation_id": "c2"},
    ]

    with patch.object(jobs.twitter, "search_mentions", new_callable=AsyncMock, return_value=mock_mentions), \
         patch.object(jobs.db, "check_cooldown", new_callable=AsyncMock, return_value=True), \
         patch.object(jobs.drafter, "classify_sentiment", new_callable=AsyncMock) as mock_classify:
        await jobs.monitor_cycle()

    mock_classify.assert_not_called()


@pytest.mark.asyncio
async def test_monitor_cycle_rate_limit(job_db):
    """RateLimitError is caught and recorded in cycle errors."""
    import jobs

    with patch.object(jobs.twitter, "search_mentions", new_callable=AsyncMock,
                      side_effect=jobs.twitter.RateLimitError("429")):
        await jobs.monitor_cycle()

    conn = await db.get_connection(job_db)
    try:
        rows = await conn.execute("SELECT * FROM cycles ORDER BY id DESC LIMIT 1")
        cycle = await rows.fetchone()
        assert cycle is not None
        assert "Rate limit" in (cycle["errors"] or "")
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_monitor_cycle_auth_failure(job_db):
    """TwitterAuthError triggers email alert."""
    import jobs

    with patch.object(jobs.twitter, "search_mentions", new_callable=AsyncMock,
                      side_effect=jobs.twitter.TwitterAuthError("401")), \
         patch("jobs._send_email") as mock_email:
        await jobs.monitor_cycle()

    mock_email.assert_called_once()
    assert "Auth Failed" in mock_email.call_args[0][0]


@pytest.mark.asyncio
async def test_monitor_cycle_hot_tweet_email(job_db):
    """Tweet from author with 100K+ followers triggers hot-tweet email."""
    import jobs

    mock_mentions = [
        {"id": "tweet-hot", "author_id": "auth-hot", "author_name": "BigUser",
         "follower_count": 100000, "text": "gstack rocks",
         "conversation_id": "c3", "author_username": "biguser"},
    ]

    with patch.object(jobs.twitter, "search_mentions", new_callable=AsyncMock, return_value=mock_mentions), \
         patch.object(jobs.twitter, "fetch_thread", new_callable=AsyncMock, return_value=[]), \
         patch.object(jobs.drafter, "classify_sentiment", new_callable=AsyncMock, return_value="praise"), \
         patch.object(jobs.drafter, "draft_variants", new_callable=AsyncMock, return_value=[
             {"label": "A", "text": "Thanks!"},
         ]), \
         patch("jobs._send_email") as mock_email:
        await jobs.monitor_cycle()

    assert mock_email.called
    assert "HOT TWEET" in mock_email.call_args[0][0]


@pytest.mark.asyncio
async def test_monitor_cycle_shutdown(job_db):
    """shutdown_event causes immediate return."""
    import jobs
    import app as app_module

    app_module.shutdown_event.set()
    try:
        with patch.object(jobs.twitter, "search_mentions", new_callable=AsyncMock) as mock_search:
            await jobs.monitor_cycle()
        mock_search.assert_not_called()
    finally:
        app_module.shutdown_event.clear()


# ── send_approved_replies ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_replies_happy_path(job_db):
    """Approved reply in active window gets sent."""
    import jobs

    mock_queue = [
        {"tweet_id": "t1", "reply_id": 1, "reply_text": "Hello!", "author_id": "a1"},
    ]

    with patch.object(jobs.db, "get_send_queue", new_callable=AsyncMock, return_value=mock_queue), \
         patch("jobs._is_in_send_window", return_value=True), \
         patch.object(jobs.twitter, "post_reply", new_callable=AsyncMock, return_value="reply-id-1"), \
         patch.object(jobs.db, "mark_sent", new_callable=AsyncMock) as mock_sent, \
         patch.object(jobs.db, "update_cooldown", new_callable=AsyncMock) as mock_cool, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        await jobs.send_approved_replies()

    mock_sent.assert_called_once()
    mock_cool.assert_called_once()


@pytest.mark.asyncio
async def test_send_replies_outside_window(job_db):
    """No replies sent when outside all send windows."""
    import jobs

    mock_queue = [
        {"tweet_id": "t1", "reply_id": 1, "reply_text": "Hello!", "author_id": "a1"},
    ]

    with patch.object(jobs.db, "get_send_queue", new_callable=AsyncMock, return_value=mock_queue), \
         patch("jobs._is_in_send_window", return_value=False), \
         patch.object(jobs.twitter, "post_reply", new_callable=AsyncMock) as mock_post:
        await jobs.send_approved_replies()

    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_send_replies_tweet_deleted(job_db):
    """TweetDeletedError triggers mark_stale."""
    import jobs

    mock_queue = [
        {"tweet_id": "t-del", "reply_id": 2, "reply_text": "Hey!", "author_id": "a2"},
    ]

    with patch.object(jobs.db, "get_send_queue", new_callable=AsyncMock, return_value=mock_queue), \
         patch("jobs._is_in_send_window", return_value=True), \
         patch.object(jobs.twitter, "post_reply", new_callable=AsyncMock,
                      side_effect=jobs.twitter.TweetDeletedError("gone")), \
         patch.object(jobs.db, "mark_stale", new_callable=AsyncMock) as mock_stale:
        await jobs.send_approved_replies()

    mock_stale.assert_called_once_with(mock_stale.call_args[0][0], "t-del")


@pytest.mark.asyncio
async def test_send_replies_rate_limit_breaks(job_db):
    """RateLimitError on second reply stops the loop after first success."""
    import jobs

    mock_queue = [
        {"tweet_id": "t1", "reply_id": 1, "reply_text": "Hi!", "author_id": "a1"},
        {"tweet_id": "t2", "reply_id": 2, "reply_text": "Hey!", "author_id": "a2"},
    ]

    call_count = 0

    async def post_side_effect(client, tweet_id, text):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise jobs.twitter.RateLimitError("429")
        return f"reply-{call_count}"

    with patch.object(jobs.db, "get_send_queue", new_callable=AsyncMock, return_value=mock_queue), \
         patch("jobs._is_in_send_window", return_value=True), \
         patch.object(jobs.twitter, "post_reply", new_callable=AsyncMock, side_effect=post_side_effect), \
         patch.object(jobs.db, "mark_sent", new_callable=AsyncMock) as mock_sent, \
         patch.object(jobs.db, "update_cooldown", new_callable=AsyncMock), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        await jobs.send_approved_replies()

    # Only first reply was marked sent
    assert mock_sent.call_count == 1


# ── check_engagement ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_engagement_happy_path(job_db):
    """Engagement data is fetched and stored."""
    import jobs

    mock_replies = [{"reply_id": 10, "twitter_reply_id": "tr-10"}]

    with patch.object(jobs.db, "get_replies_needing_engagement_check",
                      new_callable=AsyncMock, return_value=mock_replies), \
         patch.object(jobs.twitter, "get_tweet_engagement", new_callable=AsyncMock,
                      return_value={"likes": 5, "retweets": 2}), \
         patch.object(jobs.db, "upsert_engagement", new_callable=AsyncMock) as mock_eng:
        await jobs.check_engagement()

    # Called for both 24h and 72h windows
    assert mock_eng.call_count == 2


@pytest.mark.asyncio
async def test_check_engagement_skip_no_twitter_id(job_db):
    """Reply without twitter_reply_id is skipped."""
    import jobs

    mock_replies = [{"reply_id": 11, "twitter_reply_id": None}]

    with patch.object(jobs.db, "get_replies_needing_engagement_check",
                      new_callable=AsyncMock, return_value=mock_replies), \
         patch.object(jobs.twitter, "get_tweet_engagement", new_callable=AsyncMock) as mock_get:
        await jobs.check_engagement()

    mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_check_engagement_error_continues(job_db):
    """Error on first reply doesn't prevent checking second."""
    import jobs

    mock_replies = [
        {"reply_id": 12, "twitter_reply_id": "tr-12"},
        {"reply_id": 13, "twitter_reply_id": "tr-13"},
    ]

    call_count = 0

    async def eng_side_effect(client, tweet_id):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("API error")
        return {"likes": 3, "retweets": 1}

    with patch.object(jobs.db, "get_replies_needing_engagement_check",
                      new_callable=AsyncMock, return_value=mock_replies), \
         patch.object(jobs.twitter, "get_tweet_engagement", new_callable=AsyncMock,
                      side_effect=eng_side_effect), \
         patch.object(jobs.db, "upsert_engagement", new_callable=AsyncMock) as mock_eng:
        await jobs.check_engagement()

    # Second reply's engagement was stored despite first failing
    assert mock_eng.call_count >= 1


# ── weekly_digest ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weekly_digest_with_data(job_db):
    """Digest email is sent with correct subject."""
    import jobs

    mock_data = {
        "tweets_found": 10, "replies_sent": 5,
        "total_likes": 20, "total_retweets": 8, "error_cycles": 1,
        "top_replies": [
            {"author_name": "Bob", "follower_count": 5000,
             "draft_text": "Thanks for the kind words!", "likes": 10, "retweets": 3},
        ],
    }

    with patch.object(jobs.db, "get_weekly_digest", new_callable=AsyncMock, return_value=mock_data), \
         patch("jobs._send_email") as mock_email:
        await jobs.weekly_digest()

    mock_email.assert_called_once()
    assert "Weekly Digest" in mock_email.call_args[0][0]
    assert "Bob" in mock_email.call_args[0][1]


@pytest.mark.asyncio
async def test_weekly_digest_no_replies(job_db):
    """Digest with no replies shows appropriate message."""
    import jobs

    mock_data = {
        "tweets_found": 3, "replies_sent": 0,
        "total_likes": 0, "total_retweets": 0, "error_cycles": 0,
        "top_replies": [],
    }

    with patch.object(jobs.db, "get_weekly_digest", new_callable=AsyncMock, return_value=mock_data), \
         patch("jobs._send_email") as mock_email:
        await jobs.weekly_digest()

    mock_email.assert_called_once()
    assert "No replies sent" in mock_email.call_args[0][1]


# ── _send_email ────────────────────────────────────────────────────────


def test_send_email_no_credentials():
    """No SMTP attempt when credentials missing."""
    import jobs

    with patch.dict(os.environ, {"GMAIL_ADDRESS": "", "GMAIL_APP_PASSWORD": ""}, clear=False), \
         patch("smtplib.SMTP") as mock_smtp:
        jobs._send_email("Test Subject", "Test body")

    mock_smtp.assert_not_called()


def test_send_email_smtp_error():
    """SMTP error is caught — no crash."""
    import jobs

    with patch.dict(os.environ, {
        "GMAIL_ADDRESS": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "app-password",
    }, clear=False), \
         patch("smtplib.SMTP", side_effect=OSError("Connection refused")):
        # Should not raise
        jobs._send_email("Test Subject", "Test body")
