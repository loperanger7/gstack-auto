"""Tests for robustness improvements — error handling, connection failures, edge cases."""

import base64
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    """File-based SQLite DB for robustness tests."""
    db_path = str(tmp_path / "robust_test.db")
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path
    app_module.DB_PATH = old_path


@pytest.fixture
def client(seeded_db):
    from fastapi.testclient import TestClient
    import app as app_module
    return TestClient(app_module.app)


def _auth():
    creds = base64.b64encode(b"testuser:testpass").decode()
    return {"Authorization": f"Basic {creds}"}


# --- Health endpoint robustness ---

def test_health_returns_json_on_db_error(client):
    """Health endpoint returns 503 JSON even when DB is unreachable."""
    import app as app_module
    old = app_module.DB_PATH
    app_module.DB_PATH = "/nonexistent/path/bad.db"
    try:
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "error"
        assert "detail" in data  # Error detail included
    finally:
        app_module.DB_PATH = old


def test_health_error_detail_truncated():
    """Error detail is truncated to 100 chars to prevent info leak."""
    # The health endpoint truncates str(e)[:100]
    # Verify this behavior in the route code
    import routes.health as h
    assert "str(e)[:100]" in open(h.__file__).read()


# --- Dashboard robustness ---

def test_dashboard_returns_200_with_empty_db(client):
    """Dashboard works even when DB has no tweets."""
    resp = client.get("/dashboard", headers=_auth())
    assert resp.status_code == 200
    assert "No tweets to review" in resp.text


def test_approve_nonexistent_tweet_returns_409(client):
    """Approve with nonexistent tweet returns 409, not 500."""
    resp = client.post("/approve", headers=_auth(), data={
        "tweet_id": "does-not-exist",
        "variant_id": "1",
        "reply_text": "Hello!",
        "send_window": "morning",
    })
    assert resp.status_code == 409


def test_skip_nonexistent_tweet_returns_409(client):
    """Skip with nonexistent tweet returns 409, not 500."""
    resp = client.post("/skip", headers=_auth(), data={
        "tweet_id": "does-not-exist",
    })
    assert resp.status_code == 409


# --- Input boundary robustness ---

def test_approve_variant_id_zero_rejected(client):
    """variant_id=0 is rejected (must be >= 1)."""
    resp = client.post("/approve", headers=_auth(), data={
        "tweet_id": "t1",
        "variant_id": "0",
        "reply_text": "Hello!",
        "send_window": "morning",
    })
    assert resp.status_code == 400


def test_approve_negative_variant_id_rejected(client):
    """Negative variant_id is rejected."""
    resp = client.post("/approve", headers=_auth(), data={
        "tweet_id": "t1",
        "variant_id": "-1",
        "reply_text": "Hello!",
        "send_window": "morning",
    })
    assert resp.status_code == 400


def test_approve_exactly_280_chars_accepted(seeded_db):
    """Reply of exactly 280 chars is accepted."""
    # Need a tweet with a variant first
    conn_setup = __import__('asyncio').get_event_loop().run_until_complete(
        db.get_connection(seeded_db)
    )
    __import__('asyncio').get_event_loop().run_until_complete(
        db.upsert_tweet(conn_setup, tweet_id="t280", author_id="a1",
                       author_name="Test", follower_count=100, text="test")
    )
    __import__('asyncio').get_event_loop().run_until_complete(
        db.save_variants(conn_setup, "t280", [{"label": "A", "text": "x" * 280}])
    )
    __import__('asyncio').get_event_loop().run_until_complete(conn_setup.close())

    from fastapi.testclient import TestClient
    import app as app_module
    client = TestClient(app_module.app)

    creds = base64.b64encode(b"testuser:testpass").decode()
    resp = client.post("/approve", headers={"Authorization": f"Basic {creds}"}, data={
        "tweet_id": "t280",
        "variant_id": "1",
        "reply_text": "x" * 280,
        "send_window": "morning",
    })
    # Should be accepted (200 or 303 redirect, not 400)
    assert resp.status_code in (200, 303)
