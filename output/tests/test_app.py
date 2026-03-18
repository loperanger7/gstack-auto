"""Tests for app.py — FastAPI routes with auth."""

import base64
import os
import re
import sys
import tempfile

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    """Create a real SQLite db file with test data for FastAPI routes."""
    db_path = str(tmp_path / "app_test.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await db.upsert_tweet(
        conn, tweet_id="tweet-1", author_id="author-1",
        author_name="Test User", follower_count=5000,
        text="gstack is amazing!", sentiment="praise",
    )
    await db.save_variants(conn, "tweet-1", [
        {"label": "A", "text": "Thanks! Check out gstack-auto."},
        {"label": "B", "text": "Glad you like it!"},
    ])
    await conn.close()

    # Patch DB_PATH in the app module
    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path
    app_module.DB_PATH = old_path


@pytest.fixture
def client(seeded_db):
    """FastAPI TestClient with seeded database."""
    from fastapi.testclient import TestClient
    import app as app_module
    return TestClient(app_module.app)


def _auth_header():
    creds = base64.b64encode(b"testuser:testpass").decode()
    return {"Authorization": f"Basic {creds}"}


def _bad_auth_header():
    creds = base64.b64encode(b"testuser:wrong").decode()
    return {"Authorization": f"Basic {creds}"}


def test_health_no_auth(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_dashboard_requires_auth(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_dashboard_bad_auth(client):
    resp = client.get("/dashboard", headers=_bad_auth_header(), follow_redirects=False)
    assert resp.status_code == 401


def test_dashboard_with_auth(client):
    resp = client.get("/dashboard", headers=_auth_header())
    assert resp.status_code == 200
    assert "gstack Reply Queue" in resp.text


def test_dashboard_renders_tweets(client):
    resp = client.get("/dashboard", headers=_auth_header())
    assert "gstack is amazing!" in resp.text
    assert "Test User" in resp.text
    assert "praise" in resp.text


def test_dashboard_renders_variants(client):
    resp = client.get("/dashboard", headers=_auth_header())
    assert "Thanks! Check out gstack-auto." in resp.text
    assert "Glad you like it!" in resp.text


def test_approve_creates_reply(client):
    dash = client.get("/dashboard", headers=_auth_header())
    match = re.search(r'name="variant_id" value="(\d+)"', dash.text)
    assert match, "Could not find variant_id in dashboard HTML"
    variant_id = match.group(1)

    resp = client.post("/approve", headers=_auth_header(), data={
        "tweet_id": "tweet-1",
        "variant_id": variant_id,
        "reply_text": "Thanks! Check out gstack-auto.",
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code == 303


def test_approve_rejects_over_280(client):
    resp = client.post("/approve", headers=_auth_header(), data={
        "tweet_id": "tweet-1",
        "variant_id": "1",
        "reply_text": "x" * 281,
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code == 400


def test_approve_rejects_empty(client):
    resp = client.post("/approve", headers=_auth_header(), data={
        "tweet_id": "tweet-1",
        "variant_id": "1",
        "reply_text": "",
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code in (400, 422)  # FastAPI may return 422 for empty form fields


def test_approve_rejects_invalid_window(client):
    resp = client.post("/approve", headers=_auth_header(), data={
        "tweet_id": "tweet-1",
        "variant_id": "1",
        "reply_text": "Hello",
        "send_window": "midnight",
    }, follow_redirects=False)
    assert resp.status_code == 400


def test_skip_updates_status(client):
    resp = client.post("/skip", headers=_auth_header(), data={
        "tweet_id": "tweet-1",
    }, follow_redirects=False)
    assert resp.status_code == 303
    dash = client.get("/dashboard", headers=_auth_header())
    assert "gstack is amazing!" not in dash.text


def test_approve_requires_auth(client):
    resp = client.post("/approve", data={
        "tweet_id": "tweet-1", "variant_id": "1",
        "reply_text": "hi", "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code == 401


def test_skip_requires_auth(client):
    resp = client.post("/skip", data={"tweet_id": "tweet-1"}, follow_redirects=False)
    assert resp.status_code == 401


def test_signed_cookie_persists(client):
    resp1 = client.get("/dashboard", headers=_auth_header())
    assert resp1.status_code == 200
    assert "gstack_session" in resp1.cookies

    resp2 = client.get("/dashboard")
    assert resp2.status_code == 200
    assert "gstack Reply Queue" in resp2.text


def test_index_redirects_to_dashboard(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302, 307, 308)
    assert "/dashboard" in resp.headers.get("location", "")
