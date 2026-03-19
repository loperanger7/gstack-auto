"""Shared fixtures for all tests."""

import os
import sys

# Add output/ to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required env vars for tests
os.environ.setdefault("CONSUMER_KEY", "test-consumer-key")
os.environ.setdefault("CONSUMER_KEY_SECRET", "test-consumer-secret")
os.environ.setdefault("ACCESS_TOKEN", "test-access-token")
os.environ.setdefault("ACCESS_TOKEN_SECRET", "test-access-token-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-signing")
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("APP_FERNET_KEY", "")  # Will be set by fixtures that need it
os.environ.setdefault("ADMIN_EMAILS", "admin@test.com")
os.environ.setdefault("APP_BEARER_TOKEN", "test-bearer-token")

import pytest
import pytest_asyncio
import aiosqlite
import db


@pytest_asyncio.fixture
async def conn():
    """In-memory SQLite connection with schema initialized."""
    c = await aiosqlite.connect(":memory:")
    c.row_factory = aiosqlite.Row
    await c.execute("PRAGMA foreign_keys=ON")
    await db.init_db(c)
    yield c
    await c.close()


@pytest_asyncio.fixture
async def conn_with_user(conn):
    """Connection with one user pre-loaded."""
    user = await db.get_or_create_user(conn, email="test@example.com", name="Test User")
    await db.update_user(conn, user["id"], onboard_step=3, tone="professional",
                         twitter_access_token="enc_token", twitter_access_secret="enc_secret",
                         twitter_username="testhandle")
    return conn, user["id"]


@pytest_asyncio.fixture
async def conn_with_tweet(conn):
    """Connection with a default user, one pending tweet, and two variants pre-loaded."""
    # Create a default user first (user_id=0 no longer works with FK)
    user = await db.get_or_create_user(conn, email="default@example.com", name="Default")
    user_id = user["id"]

    await db.upsert_tweet(
        conn,
        tweet_id="tweet-1",
        author_id="author-1",
        author_name="Test User",
        follower_count=5000,
        text="gstack is amazing!",
        sentiment="praise",
        user_id=user_id,
    )
    await db.save_variants(conn, "tweet-1", [
        {"label": "A", "text": "Thanks! Check out gstack-auto."},
        {"label": "B", "text": "Glad you like it!"},
    ])
    return conn
