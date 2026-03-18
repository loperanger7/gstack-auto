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

    # Patch DB_PATH in the app module (route modules read it via deferred import)
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


# --- Round 2 regression + UX tests ---


def test_dashboard_has_stats_link(client):
    """Dashboard nav bar contains a link to /stats."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert resp.status_code == 200
    assert 'href="/stats"' in resp.text


def test_dashboard_has_dashboard_active_link(client):
    """Dashboard nav bar has active class on dashboard link."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert 'class="nav-link active"' in resp.text
    assert 'href="/dashboard"' in resp.text


def test_dashboard_renders_health_dot(client):
    """Dashboard contains health indicator dot."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert "health-dot" in resp.text


def test_dashboard_has_keyboard_hint(client):
    """Dashboard shows keyboard shortcut hints when tweets exist."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert "<kbd>" in resp.text
    assert "approve" in resp.text.lower() or "skip" in resp.text.lower()


def test_dashboard_edit_textarea_present(client):
    """Each tweet card has an edit textarea."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert "edit-area" in resp.text
    assert 'rows="3"' in resp.text


def test_dashboard_char_count_rendered(client):
    """Variant character counts are rendered."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert "char-count" in resp.text
    assert "char-green" in resp.text


def test_dashboard_send_window_options(client):
    """All three send window options are present."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert 'value="morning"' in resp.text
    assert 'value="lunch"' in resp.text
    assert 'value="evening"' in resp.text


def test_dashboard_favicon_present(client):
    """Dashboard has an inline favicon."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert 'rel="icon"' in resp.text


def test_approve_returns_json_for_xhr(client):
    """POST /approve with XHR header returns JSON instead of redirect."""
    dash = client.get("/dashboard", headers=_auth_header())
    match = re.search(r'name="variant_id" value="(\d+)"', dash.text)
    assert match, "Could not find variant_id in dashboard HTML"
    variant_id = match.group(1)

    resp = client.post("/approve", headers={
        **_auth_header(),
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
    assert data["action"] == "approved"


def test_skip_returns_json_for_xhr(client):
    """POST /skip with XHR header returns JSON instead of redirect."""
    resp = client.post("/skip", headers={
        **_auth_header(),
        "X-Requested-With": "XMLHttpRequest",
    }, data={
        "tweet_id": "tweet-1",
    }, follow_redirects=False)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["action"] == "skipped"


def test_approve_xhr_rejects_over_280(client):
    """XHR approve with >280 chars returns JSON error."""
    resp = client.post("/approve", headers={
        **_auth_header(),
        "X-Requested-With": "XMLHttpRequest",
    }, data={
        "tweet_id": "tweet-1",
        "variant_id": "1",
        "reply_text": "x" * 281,
        "send_window": "morning",
    }, follow_redirects=False)
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_stats_has_dashboard_link(client):
    """Stats page has a link back to dashboard."""
    resp = client.get("/stats", headers=_auth_header())
    assert resp.status_code == 200
    assert 'href="/dashboard"' in resp.text


def test_stats_semantic_colors(client):
    """Stats page uses semantic color classes for stat values."""
    resp = client.get("/stats", headers=_auth_header())
    assert "stat-value-replied" in resp.text
    assert "stat-value-pending" in resp.text
    assert "stat-value-stale" in resp.text


def test_stats_favicon_present(client):
    """Stats page has an inline favicon."""
    resp = client.get("/stats", headers=_auth_header())
    assert 'rel="icon"' in resp.text


def test_dashboard_card_has_data_index(client):
    """Tweet cards have data-card-index for keyboard navigation."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert 'data-card-index="0"' in resp.text


def test_dashboard_toast_element_present(client):
    """Dashboard has a toast element for notifications."""
    resp = client.get("/dashboard", headers=_auth_header())
    assert 'id="toast"' in resp.text
    assert "toast" in resp.text
