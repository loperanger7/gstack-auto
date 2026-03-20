"""Tests for robustness improvements — error handling, connection failures, edge cases."""

import base64
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


def _set_session_cookie(client, user_id: int, email: str = "test@example.com"):
    """Set a valid session cookie for the Starlette SessionMiddleware."""
    from itsdangerous import TimestampSigner
    secret = "test-secret-key-for-signing"
    signer = TimestampSigner(secret)
    data = {"user_id": user_id, "user_email": email, "user_name": "Test"}
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    signed = signer.sign(payload).decode()
    client.cookies.set("session", signed)
    return client


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    """File-based SQLite DB with a user for robustness tests."""
    db_path = str(tmp_path / "robust_test.db")
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    user = await db.get_or_create_user(conn, "test@example.com", name="Test")
    await db.update_user(conn, user["id"], onboard_step=3,
                         twitter_access_token="t", twitter_access_secret="s")
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path, user["id"]
    app_module.DB_PATH = old_path


@pytest.fixture
def client(seeded_db):
    from starlette.testclient import TestClient
    import app as app_module
    _, user_id = seeded_db
    c = TestClient(app_module.app)
    _set_session_cookie(c, user_id=user_id)
    return c


# --- Health endpoint robustness ---

def test_health_returns_json_on_db_error(seeded_db):
    """Health endpoint returns 503 JSON even when DB is unreachable."""
    from starlette.testclient import TestClient
    import app as app_module
    old = app_module.DB_PATH
    app_module.DB_PATH = "/nonexistent/path/bad.db"
    try:
        c = TestClient(app_module.app)
        resp = c.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "error"
        assert "detail" in data
    finally:
        app_module.DB_PATH = old


def test_health_error_detail_truncated():
    """Error detail is truncated to 100 chars to prevent info leak."""
    import routes.health as h
    assert "str(e)[:100]" in open(h.__file__).read()


# --- Dashboard robustness ---

def test_dashboard_returns_200_with_empty_db(client):
    """Dashboard works even when DB has no tweets."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "No tweets" in resp.text


def test_approve_nonexistent_tweet_returns_error(client):
    """Approve with nonexistent tweet returns 403 (not owned) or 409, not 500."""
    resp = client.post("/approve", data={
        "tweet_id": "does-not-exist",
        "variant_id": "1",
        "reply_text": "Hello!",
    })
    # 403 because the tweet doesn't exist so ownership check fails
    assert resp.status_code in (403, 409)


def test_skip_nonexistent_tweet_returns_error(client):
    """Skip with nonexistent tweet returns 403 (not owned) or 409, not 500."""
    resp = client.post("/skip", data={
        "tweet_id": "does-not-exist",
    })
    assert resp.status_code in (403, 409)


# --- Input boundary robustness ---

def test_approve_variant_id_zero_rejected(client):
    """variant_id=0 is rejected (must be >= 1)."""
    resp = client.post("/approve", data={
        "tweet_id": "t1",
        "variant_id": "0",
        "reply_text": "Hello!",
    })
    assert resp.status_code == 400


def test_approve_negative_variant_id_rejected(client):
    """Negative variant_id is rejected."""
    resp = client.post("/approve", data={
        "tweet_id": "t1",
        "variant_id": "-1",
        "reply_text": "Hello!",
    })
    assert resp.status_code == 400


def test_approve_exactly_280_chars_accepted(seeded_db):
    """Reply of exactly 280 chars is accepted."""
    import asyncio
    db_path, user_id = seeded_db

    variant_id = None

    async def setup():
        nonlocal variant_id
        conn = await db.get_connection(db_path)
        await db.upsert_tweet(conn, tweet_id="t280", author_id="a1",
                             author_name="Test", follower_count=100, text="test",
                             user_id=user_id)
        await db.save_variants(conn, "t280", [{"label": "A", "text": "x" * 280}])
        cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't280'")
        variant_id = (await cursor.fetchone())[0]
        await conn.close()

    asyncio.get_event_loop().run_until_complete(setup())

    from starlette.testclient import TestClient
    import app as app_module
    c = TestClient(app_module.app)
    _set_session_cookie(c, user_id=user_id)

    resp = c.post("/approve", data={
        "tweet_id": "t280",
        "variant_id": str(variant_id),
        "reply_text": "x" * 280,
    }, follow_redirects=False)
    # Should redirect to Twitter intent URL, not 400
    assert resp.status_code == 303
    assert "x.com/intent/post" in resp.headers.get("location", "")
