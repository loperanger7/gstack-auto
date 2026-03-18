"""Tests for twitter.py — Twitter API client with rate budget."""

import time

import pytest
import httpx
import respx

import twitter


@pytest.fixture(autouse=True)
def _reset_budget():
    twitter.reset_budget()
    yield
    twitter.reset_budget()


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_tweets():
    respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
        return_value=httpx.Response(200, json={
            "data": [
                {"id": "1", "text": "love gstack", "author_id": "a1",
                 "conversation_id": "1", "public_metrics": {}},
            ],
            "includes": {
                "users": [
                    {"id": "a1", "name": "Alice", "username": "alice",
                     "public_metrics": {"followers_count": 5000}},
                ]
            }
        })
    )
    async with httpx.AsyncClient() as client:
        tweets = await twitter.search_mentions(client)
    assert len(tweets) >= 1
    assert tweets[0]["id"] == "1"
    assert tweets[0]["author_name"] == "Alice"
    assert tweets[0]["follower_count"] == 5000


@pytest.mark.asyncio
@respx.mock
async def test_search_empty_results():
    respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
        return_value=httpx.Response(200, json={"data": [], "includes": {}})
    )
    async with httpx.AsyncClient() as client:
        tweets = await twitter.search_mentions(client)
    assert tweets == []


@pytest.mark.asyncio
@respx.mock
async def test_search_rate_limited():
    respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
        return_value=httpx.Response(429, json={"detail": "Rate limit"})
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.RateLimitError):
            await twitter.search_mentions(client)


@pytest.mark.asyncio
@respx.mock
async def test_search_deduplicates():
    """Same tweet ID from multiple queries is only returned once."""
    respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
        return_value=httpx.Response(200, json={
            "data": [
                {"id": "1", "text": "gstack", "author_id": "a1",
                 "conversation_id": "1", "public_metrics": {}},
            ],
            "includes": {
                "users": [{"id": "a1", "name": "A", "username": "a",
                           "public_metrics": {"followers_count": 100}}]
            }
        })
    )
    async with httpx.AsyncClient() as client:
        tweets = await twitter.search_mentions(client)
    assert len(tweets) == 1


@pytest.mark.asyncio
@respx.mock
async def test_fetch_thread():
    respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
        return_value=httpx.Response(200, json={
            "data": [
                {"id": "p1", "text": "parent tweet", "author_id": "a1"},
                {"id": "p2", "text": "another parent", "author_id": "a2"},
            ]
        })
    )
    async with httpx.AsyncClient() as client:
        thread = await twitter.fetch_thread(client, "conv-1")
    assert len(thread) == 2
    assert thread[0]["text"] == "parent tweet"


@pytest.mark.asyncio
@respx.mock
async def test_post_reply_success():
    respx.post("https://api.twitter.com/2/tweets").mock(
        return_value=httpx.Response(201, json={
            "data": {"id": "reply-123", "text": "My reply"}
        })
    )
    async with httpx.AsyncClient() as client:
        reply_id = await twitter.post_reply(client, "tweet-1", "My reply")
    assert reply_id == "reply-123"


@pytest.mark.asyncio
@respx.mock
async def test_post_reply_deleted_tweet():
    respx.post("https://api.twitter.com/2/tweets").mock(
        return_value=httpx.Response(403, json={"detail": "Forbidden"})
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.TweetDeletedError):
            await twitter.post_reply(client, "tweet-1", "My reply")


@pytest.mark.asyncio
async def test_rate_budget_stops_at_limit():
    twitter._rate_budget["count"] = twitter.RATE_LIMIT
    twitter._rate_budget["window_start"] = time.monotonic()
    with pytest.raises(twitter.RateLimitError, match="budget exhausted"):
        async with httpx.AsyncClient() as client:
            await twitter.post_reply(client, "t1", "text")


@pytest.mark.asyncio
@respx.mock
async def test_search_handles_missing_user_data():
    """Tweets with no matching user data get default values."""
    respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
        return_value=httpx.Response(200, json={
            "data": [
                {"id": "1", "text": "gstack", "author_id": "unknown",
                 "conversation_id": "1", "public_metrics": {}},
            ],
            "includes": {"users": []}
        })
    )
    async with httpx.AsyncClient() as client:
        tweets = await twitter.search_mentions(client)
    assert tweets[0]["author_name"] == ""
    assert tweets[0]["follower_count"] == 0


@pytest.mark.asyncio
async def test_post_reply_rejects_over_280():
    """post_reply validates text length before hitting the API."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.TwitterError, match="Invalid reply text length"):
            await twitter.post_reply(client, "t1", "x" * 281)


@pytest.mark.asyncio
async def test_post_reply_rejects_empty():
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.TwitterError, match="Invalid reply text length"):
            await twitter.post_reply(client, "t1", "")


@pytest.mark.asyncio
@respx.mock
async def test_get_tweet_engagement():
    respx.get("https://api.twitter.com/2/tweets/eng-1").mock(
        return_value=httpx.Response(200, json={
            "data": {
                "id": "eng-1",
                "public_metrics": {"like_count": 42, "retweet_count": 7},
            }
        })
    )
    async with httpx.AsyncClient() as client:
        result = await twitter.get_tweet_engagement(client, "eng-1")
    assert result["likes"] == 42
    assert result["retweets"] == 7


@pytest.mark.asyncio
@respx.mock
async def test_get_tweet_engagement_deleted():
    respx.get("https://api.twitter.com/2/tweets/gone-1").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    async with httpx.AsyncClient() as client:
        result = await twitter.get_tweet_engagement(client, "gone-1")
    assert result.get("deleted") is True


@pytest.mark.asyncio
async def test_fetch_thread_empty_conversation_id():
    async with httpx.AsyncClient() as client:
        result = await twitter.fetch_thread(client, "")
    assert result == []


@pytest.mark.asyncio
async def test_budget_usage_pct():
    twitter.reset_budget()
    assert twitter.budget_usage_pct() == 0.0
    twitter._rate_budget["count"] = 27
    twitter._rate_budget["window_start"] = time.monotonic()
    pct = twitter.budget_usage_pct()
    assert 40 < pct < 55  # ~49% of 55


@pytest.mark.asyncio
@respx.mock
async def test_request_syncs_budget_from_rate_headers():
    """When Twitter returns x-rate-limit-remaining, local budget syncs down."""
    twitter.reset_budget()
    twitter._rate_budget["count"] = 5  # local thinks 5 used
    twitter._rate_budget["window_start"] = time.monotonic()

    # Twitter says only 10 remaining (out of 55 limit) — means 45 used
    respx.get("https://api.twitter.com/2/tweets/sync-1").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"id": "sync-1", "public_metrics": {"like_count": 1, "retweet_count": 0}}},
            headers={"x-rate-limit-remaining": "10"},
        )
    )
    async with httpx.AsyncClient() as client:
        await twitter.get_tweet_engagement(client, "sync-1")

    # Budget should have been corrected: 55 - 10 = 45
    assert twitter._rate_budget["count"] == 45


@pytest.mark.asyncio
@respx.mock
async def test_429_error_includes_reset_time():
    """429 error message includes the reset timestamp from headers."""
    respx.get("https://api.twitter.com/2/tweets/search/recent").mock(
        return_value=httpx.Response(
            429,
            json={"detail": "Rate limit"},
            headers={"x-rate-limit-reset": "1700000000"},
        )
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(twitter.RateLimitError, match="1700000000"):
            await twitter.search_mentions(client)
