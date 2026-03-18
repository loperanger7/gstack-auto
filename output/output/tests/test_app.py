"""Tests for app.py — FastAPI routes with session-based auth (multi-tenant)."""

import os
import re
import sys

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

    # Create a test user
    user = await db.get_or_create_user(conn, email="test@example.com", name="Test User")
    await db.update_user(conn, user["id"], onboard_step=3, tone="professional",
                         twitter_access_token="enc", twitter_access_secret="enc",
                         twitter_username="testhandle")

    await db.upsert_tweet(
        conn, tweet_id="tweet-1", author_id="author-1",
        author_name="Test User", follower_count=5000,
        text="gstack is amazing!", sentiment="praise",
        user_id=user["id"],
    )
    await db.save_variants(conn, "tweet-1", [
        {"label": "A", "text": "Thanks! Check out gstack-auto."},
        {"label": "B", "text": "Glad you like it!"},
    ])
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path, user["id"]
    app_module.DB_PATH = old_path


@pytest.fixture
def client(seeded_db):
    """FastAPI TestClient with seeded database and authenticated session."""
    from starlette.testclient import TestClient
    import app as app_module

    c = TestClient(app_module.app)
    return c


def _auth_session(client, user_id=1):
    """Set session cookie matching Starlette SessionMiddleware format."""
    import json
    import base64
    from itsdangerous import TimestampSigner

    secret = "test-secret-key-for-signing"
    signer = TimestampSigner(secret)
    session_data = {"user_id": user_id, "user_email": "test@example.com", "user_name": "Test User"}
    payload = base64.b64encode(json.dumps(session_data).encode()).decode()
    signed = signer.sign(payload).decode()
    client.cookies.set("session", signed)
    return client


@pytest.fixture
def auth_client(client, seeded_db):
    """Authenticated test client."""
    _, user_id = seeded_db
    return _auth_session(client, user_id)


def test_health_no_auth(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_dashboard_requires_auth(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("location", "")


def test_login_page_renders(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert "Sign in with Google" in resp.text


def test_dashboard_with_auth(auth_client):
    resp = auth_client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    assert "gstack Reply Queue" in resp.text


def test_dashboard_renders_tweets(auth_client):
    resp = auth_client.get("/dashboard")
    assert "gstack is amazing!" in resp.text
    assert "Test User" in resp.text
    assert "praise" in resp.text


def test_dashboard_renders_variants(auth_client):
    resp = auth_client.get("/dashboard")
    assert "Thanks! Check out gstack-auto." in resp.text
    assert "Glad you like it!" in resp.text


def test_approve_creates_reply(auth_client):
    dash = auth_client.get("/dashboard")
    match = re.search(r'name="variant_id" value="(\d+)"', dash.text)
    assert match, "Could not find variant_id in dashboard HTML"
    variant_id = match.group(1)

    resp = auth_client.post("/approve", data={
        "tweet_id": "tweet-1",
        "variant_id": variant_id,
        "reply_text": "Thanks! Check out gstack-auto.",
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code == 303


def test_approve_rejects_over_280(auth_client):
    resp = auth_client.post("/approve", data={
        "tweet_id": "tweet-1",
        "variant_id": "1",
        "reply_text": "x" * 281,
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code == 400


def test_approve_rejects_empty(auth_client):
    resp = auth_client.post("/approve", data={
        "tweet_id": "tweet-1",
        "variant_id": "1",
        "reply_text": "",
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code in (400, 422)


def test_approve_rejects_invalid_window(auth_client):
    resp = auth_client.post("/approve", data={
        "tweet_id": "tweet-1",
        "variant_id": "1",
        "reply_text": "Hello",
        "send_window": "midnight",
    }, follow_redirects=False)
    assert resp.status_code == 400


def test_skip_updates_status(auth_client):
    resp = auth_client.post("/skip", data={
        "tweet_id": "tweet-1",
    }, follow_redirects=False)
    assert resp.status_code == 303
    dash = auth_client.get("/dashboard")
    assert "gstack is amazing!" not in dash.text


def test_approve_requires_auth(client):
    resp = client.post("/approve", data={
        "tweet_id": "tweet-1", "variant_id": "1",
        "reply_text": "hi", "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_skip_requires_auth(client):
    resp = client.post("/skip", data={"tweet_id": "tweet-1"}, follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_index_redirects_to_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302, 307, 308)
    assert "/auth/login" in resp.headers.get("location", "")


def test_logout(auth_client):
    resp = auth_client.get("/auth/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers.get("location", "")


# --- Nav and UX tests ---

def test_dashboard_has_stats_link(auth_client):
    resp = auth_client.get("/dashboard")
    assert resp.status_code == 200
    assert 'href="/stats"' in resp.text


def test_dashboard_has_settings_link(auth_client):
    resp = auth_client.get("/dashboard")
    assert 'href="/settings"' in resp.text


def test_dashboard_renders_health_dot(auth_client):
    resp = auth_client.get("/dashboard")
    assert "health-dot" in resp.text


def test_dashboard_has_keyboard_hint(auth_client):
    resp = auth_client.get("/dashboard")
    assert "<kbd>" in resp.text


def test_dashboard_edit_textarea_present(auth_client):
    resp = auth_client.get("/dashboard")
    assert "edit-area" in resp.text


def test_dashboard_char_count_rendered(auth_client):
    resp = auth_client.get("/dashboard")
    assert "char-count" in resp.text
    assert "char-green" in resp.text


def test_dashboard_send_window_options(auth_client):
    resp = auth_client.get("/dashboard")
    assert 'value="morning"' in resp.text
    assert 'value="lunch"' in resp.text
    assert 'value="evening"' in resp.text


def test_dashboard_favicon_present(auth_client):
    resp = auth_client.get("/dashboard")
    assert 'rel="icon"' in resp.text


def test_dashboard_tone_badge(auth_client):
    resp = auth_client.get("/dashboard")
    assert "tone-badge" in resp.text


def test_approve_returns_json_for_xhr(auth_client):
    dash = auth_client.get("/dashboard")
    match = re.search(r'name="variant_id" value="(\d+)"', dash.text)
    assert match
    variant_id = match.group(1)

    resp = auth_client.post("/approve", headers={
        "X-Requested-With": "XMLHttpRequest",
    }, data={
        "tweet_id": "tweet-1",
        "variant_id": variant_id,
        "reply_text": "Thanks! Check out gstack-auto.",
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


def test_skip_returns_json_for_xhr(auth_client):
    resp = auth_client.post("/skip", headers={
        "X-Requested-With": "XMLHttpRequest",
    }, data={
        "tweet_id": "tweet-1",
    }, follow_redirects=False)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


def test_stats_requires_auth(client):
    resp = client.get("/stats", follow_redirects=False)
    assert resp.status_code == 302


def test_stats_with_auth(auth_client):
    resp = auth_client.get("/stats")
    assert resp.status_code == 200
    assert "gstack Stats" in resp.text


def test_settings_requires_auth(client):
    resp = client.get("/settings", follow_redirects=False)
    assert resp.status_code == 302


def test_settings_with_auth(auth_client):
    resp = auth_client.get("/settings")
    assert resp.status_code == 200
    assert "Settings" in resp.text


def test_dashboard_card_has_data_index(auth_client):
    resp = auth_client.get("/dashboard")
    assert 'data-card-index="0"' in resp.text


def test_dashboard_toast_element_present(auth_client):
    resp = auth_client.get("/dashboard")
    assert 'id="toast"' in resp.text
