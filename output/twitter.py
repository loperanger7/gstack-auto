"""Twitter API v2 client with OAuth 1.0a signing and rate budget.
Manual HMAC-SHA1 — no tweepy, no authlib."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
import urllib.parse
from typing import Any

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://api.twitter.com/2"

SEARCH_QUERIES = [
    "gstack",
    '"g-stack"',
    '"garry tan" gstack',
    "@garrytan gstack",
    "gstack-auto",
]

_rate_budget = {"count": 0, "window_start": 0.0}
RATE_LIMIT = 55  # out of Twitter's 60 per 15-min window
WINDOW_SECONDS = 900


class TwitterError(Exception):
    pass


class TwitterAuthError(TwitterError):
    pass


class TweetDeletedError(TwitterError):
    pass


class RateLimitError(TwitterError):
    pass


def _check_budget() -> bool:
    now = time.monotonic()
    if now - _rate_budget["window_start"] >= WINDOW_SECONDS:
        _rate_budget["count"] = 0
        _rate_budget["window_start"] = now
    return _rate_budget["count"] < RATE_LIMIT


def _spend_budget() -> None:
    _rate_budget["count"] += 1


def budget_usage_pct() -> float:
    now = time.monotonic()
    if now - _rate_budget["window_start"] >= WINDOW_SECONDS:
        return 0.0
    return (_rate_budget["count"] / RATE_LIMIT) * 100 if RATE_LIMIT else 100.0


def reset_budget() -> None:
    """Reset rate budget. Exposed for testing."""
    _rate_budget["count"] = 0
    _rate_budget["window_start"] = 0.0


def _get_credentials() -> dict:
    return {
        "consumer_key": os.environ["CONSUMER_KEY"],
        "consumer_secret": os.environ["CONSUMER_KEY_SECRET"],
        "token": os.environ["ACCESS_TOKEN"],
        "token_secret": os.environ["ACCESS_TOKEN_SECRET"],
    }


def _percent_encode(s: str) -> str:
    return urllib.parse.quote(str(s), safe="")


def _oauth_signature(
    method: str, url: str, params: dict,
    consumer_secret: str, token_secret: str,
) -> str:
    """OAuth 1.0a HMAC-SHA1 signature."""
    sorted_params = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}"
        for k, v in sorted(params.items())
    )
    base_string = f"{method.upper()}&{_percent_encode(url)}&{_percent_encode(sorted_params)}"
    signing_key = f"{_percent_encode(consumer_secret)}&{_percent_encode(token_secret)}"
    sig = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    return base64.b64encode(sig).decode()


def _oauth_header(method: str, url: str, creds: dict, extra_params: dict | None = None) -> str:
    """Build OAuth Authorization header."""
    oauth_params = {
        "oauth_consumer_key": creds["consumer_key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds["token"],
        "oauth_version": "1.0",
    }
    all_params = {**oauth_params}
    if extra_params:
        all_params.update(extra_params)
    sig = _oauth_signature(
        method, url, all_params, creds["consumer_secret"], creds["token_secret"]
    )
    oauth_params["oauth_signature"] = sig
    header_parts = ", ".join(
        f'{_percent_encode(k)}="{_percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


async def _request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    params: dict | None = None,
    json_body: dict | None = None,
    retries: int = 2,
) -> dict[str, Any]:
    """Authenticated request with retry, budget tracking, fail-safe error handling."""
    if not _check_budget():
        raise RateLimitError("Rate budget exhausted for this window")

    creds = _get_credentials()
    sig_params = {k: str(v) for k, v in params.items()} if params and method == "GET" else {}

    _spend_budget()  # count once per logical call, not per retry
    for attempt in range(retries + 1):
        auth_header = _oauth_header(method, url, creds, sig_params if method == "GET" else None)
        headers = {"Authorization": auth_header}

        try:
            resp = await client.request(
                method, url, params=params, json=json_body,
                headers=headers, timeout=15.0,
            )
        except httpx.TimeoutException:
            if attempt < retries:
                log.warning("Twitter timeout (attempt %d/%d)", attempt + 1, retries + 1)
                await asyncio.sleep((attempt + 1) * 1.5)
                continue
            raise TwitterError("Twitter request timed out after retries")
        except httpx.ConnectError as e:
            if attempt < retries:
                log.warning("Twitter connect error: %s", e)
                await asyncio.sleep((attempt + 1) * 1.5)
                continue
            raise TwitterError(f"Twitter connection failed: {e}")

        if resp.status_code in (200, 201):
            return resp.json()
        if resp.status_code == 401:
            raise TwitterAuthError("Twitter 401 — check API credentials")
        if resp.status_code == 429:
            raise RateLimitError("Twitter 429 rate limit")
        if resp.status_code == 404:
            raise TweetDeletedError(f"Tweet not found (404): {resp.text[:100]}")
        if resp.status_code == 403:
            raise TweetDeletedError(f"Forbidden (403): {resp.text[:100]}")

        if resp.status_code >= 500 and attempt < retries:
            log.warning("Twitter %d, retrying...", resp.status_code)
            import asyncio
            await asyncio.sleep((attempt + 1) * 1.5)
            continue

        raise TwitterError(f"Twitter API error {resp.status_code}: {resp.text[:200]}")

    return {}


async def search_mentions(client: httpx.AsyncClient) -> list[dict]:
    """Search for gstack mentions. Returns list of tweet dicts."""
    all_tweets = []
    seen_ids: set[str] = set()

    usage = budget_usage_pct()
    queries = SEARCH_QUERIES
    if usage >= 95:
        log.warning("Rate budget at %.0f%%, skipping search", usage)
        return []
    if usage >= 80:
        queries = queries[:2]
        log.info("Rate budget at %.0f%%, reducing to %d queries", usage, len(queries))

    for query in queries:
        if not _check_budget():
            log.warning("Budget exhausted mid-search, stopping")
            break

        try:
            data = await _request(client, "GET", f"{BASE_URL}/tweets/search/recent", params={
                "query": f"{query} -is:retweet",
                "max_results": "10",
                "tweet.fields": "author_id,created_at,conversation_id,public_metrics",
                "expansions": "author_id",
                "user.fields": "name,username,public_metrics",
            })
        except (RateLimitError, TwitterAuthError):
            raise
        except TwitterError as e:
            log.warning("Search failed for '%s': %s", query, e)
            continue

        tweets = data.get("data", [])
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        for t in tweets:
            tid = t["id"]
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            author = users.get(t.get("author_id", ""), {})
            fc = author.get("public_metrics", {}).get("followers_count", 0)
            all_tweets.append({
                "id": tid,
                "author_id": t.get("author_id", ""),
                "author_name": author.get("name", ""),
                "author_username": author.get("username", ""),
                "follower_count": fc if isinstance(fc, int) else 0,
                "text": t.get("text", ""),
                "conversation_id": t.get("conversation_id", tid),
            })

    log.info("Found %d tweets across %d queries", len(all_tweets), len(queries))
    return all_tweets


async def fetch_thread(
    client: httpx.AsyncClient, conversation_id: str, max_tweets: int = 10
) -> list[dict]:
    """Fetch thread context. Returns list of {id, text, author_id}."""
    if not conversation_id:
        return []
    try:
        data = await _request(client, "GET", f"{BASE_URL}/tweets/search/recent", params={
            "query": f"conversation_id:{conversation_id}",
            "max_results": str(min(max_tweets, 100)),
            "tweet.fields": "author_id,created_at,text",
        })
        return [
            {"id": t["id"], "text": t.get("text", ""), "author_id": t.get("author_id", "")}
            for t in data.get("data", [])[:max_tweets]
        ]
    except TweetDeletedError:
        return []
    except TwitterError as e:
        log.warning("Thread fetch failed for %s: %s", conversation_id, e)
        return []


async def post_reply(client: httpx.AsyncClient, tweet_id: str, text: str) -> str:
    """Post a reply. Returns the new tweet's ID."""
    if not text or len(text) > 280:
        raise TwitterError(f"Invalid reply text length: {len(text) if text else 0}")
    data = await _request(client, "POST", f"{BASE_URL}/tweets", json_body={
        "text": text,
        "reply": {"in_reply_to_tweet_id": tweet_id},
    })
    reply_id = data.get("data", {}).get("id", "")
    if not reply_id:
        raise TwitterError("Twitter did not return a reply ID")
    return reply_id


async def get_tweet_engagement(client: httpx.AsyncClient, tweet_id: str) -> dict:
    """Get engagement metrics. Returns {likes, retweets}."""
    try:
        data = await _request(client, "GET", f"{BASE_URL}/tweets/{tweet_id}", params={
            "tweet.fields": "public_metrics",
        })
        metrics = data.get("data", {}).get("public_metrics", {})
        return {
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
        }
    except TweetDeletedError:
        return {"likes": 0, "retweets": 0, "deleted": True}
    except TwitterError as e:
        log.warning("Engagement check failed for %s: %s", tweet_id, e)
        return {"likes": 0, "retweets": 0, "error": str(e)}
