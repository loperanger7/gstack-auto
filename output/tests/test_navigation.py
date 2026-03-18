"""Tests for cross-page navigation, edit textarea, and char count badges."""

import base64
import json
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


def _set_session_cookie(client, user_id: int, email: str = "test@example.com"):
    """Set a valid session cookie for the Starlette SessionMiddleware."""
    from itsdangerous import TimestampSigner
    secret = "test-secret-key-for-signing"
    signer = TimestampSigner(secret)
    data = {"user_id": user_id, "user_email": email, "user_name": "Nav Test"}
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    signed = signer.sign(payload).decode()
    client.cookies.set("session", signed)
    return client


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    """Create a real SQLite db file with test data and a user."""
    db_path = str(tmp_path / "nav_test.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)

    user = await db.get_or_create_user(conn, "test@example.com", name="Nav Test")
    await db.update_user(conn, user["id"], onboard_step=3,
                         twitter_access_token="t", twitter_access_secret="s")

    await db.upsert_tweet(
        conn, tweet_id="tweet-nav-1", author_id="author-1",
        author_name="Nav Test", follower_count=1000,
        text="gstack is great!", sentiment="praise",
        user_id=user["id"],
    )
    await db.save_variants(conn, "tweet-nav-1", [
        {"label": "A", "text": "Short reply"},
        {"label": "B", "text": "x" * 265},
        {"label": "C", "text": "x" * 275},
    ])
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


# --- Navigation link tests ---

def test_dashboard_has_stats_link(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert 'href="/stats"' in resp.text


def test_dashboard_has_dashboard_active_link(client):
    resp = client.get("/dashboard")
    assert 'class="nav-link active"' in resp.text
    assert 'href="/dashboard" class="nav-link active"' in resp.text


def test_stats_has_dashboard_link(client):
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert 'href="/dashboard"' in resp.text


def test_stats_has_stats_active_link(client):
    resp = client.get("/stats")
    assert 'href="/stats" class="nav-link active"' in resp.text


def test_dashboard_has_nav_bar(client):
    resp = client.get("/dashboard")
    assert 'class="nav-bar"' in resp.text


def test_stats_has_nav_bar(client):
    resp = client.get("/stats")
    assert 'class="nav-bar"' in resp.text


# --- Edit textarea tests ---

def test_dashboard_has_edit_area_wrap(client):
    """Edit textarea wrapper exists and starts hidden."""
    resp = client.get("/dashboard")
    assert 'class="edit-area-wrap"' in resp.text
    assert 'style="display:none"' in resp.text


def test_dashboard_has_edit_button(client):
    resp = client.get("/dashboard")
    assert 'class="btn btn-edit"' in resp.text


def test_dashboard_edit_area_has_maxlength(client):
    """Edit textarea has maxlength=280 for fail-safe."""
    resp = client.get("/dashboard")
    assert 'maxlength="280"' in resp.text


# --- Character count badge tests ---

def test_dashboard_char_count_green(client):
    """Short variant (11 chars) gets green badge."""
    resp = client.get("/dashboard")
    assert 'char-green' in resp.text


def test_dashboard_char_count_yellow(client):
    """265-char variant gets yellow badge."""
    resp = client.get("/dashboard")
    assert 'char-yellow' in resp.text


def test_dashboard_char_count_red(client):
    """275-char variant gets red badge."""
    resp = client.get("/dashboard")
    assert 'char-red' in resp.text


# --- Variant radio data attribute tests ---

def test_dashboard_variants_have_data_text(client):
    """Each variant radio has a data-text attribute for JS edit population."""
    resp = client.get("/dashboard")
    assert 'data-text="Short reply"' in resp.text


def test_dashboard_has_reply_text_hidden_field(client):
    """Hidden reply_text field exists for form submission."""
    resp = client.get("/dashboard")
    assert 'class="reply-text-hidden"' in resp.text
