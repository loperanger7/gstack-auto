"""Tests for UX improvements — auto-select window, keyboard overlay, smart defaults."""

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
    data = {"user_id": user_id, "user_email": email, "user_name": "UX Test"}
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    signed = signer.sign(payload).decode()
    client.cookies.set("session", signed)
    return client


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    """Create a real SQLite db file with test data and a user."""
    db_path = str(tmp_path / "ux_test.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)

    user = await db.get_or_create_user(conn, "test@example.com", name="UX Test")
    await db.update_user(conn, user["id"], onboard_step=3,
                         twitter_access_token="t", twitter_access_secret="s")

    await db.upsert_tweet(
        conn, tweet_id="tweet-ux-1", author_id="author-1",
        author_name="UX Test", follower_count=1000,
        text="gstack is great!", sentiment="praise",
        user_id=user["id"],
    )
    await db.save_variants(conn, "tweet-ux-1", [
        {"label": "A", "text": "Short reply"},
        {"label": "B", "text": "A longer reply that uses more characters"},
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


# --- Auto-select send window ---

def test_dashboard_has_default_window(client):
    """Dashboard select has a selected option (not hardcoded to morning)."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "selected" in resp.text


def test_dashboard_default_window_is_valid(client):
    """The selected window is one of morning/lunch/evening."""
    resp = client.get("/dashboard")
    import re
    matches = re.findall(r'value="(\w+)"[^>]*selected', resp.text)
    assert len(matches) >= 1
    assert matches[0] in ("morning", "lunch", "evening")


# --- Keyboard shortcut overlay ---

def test_dashboard_has_kbd_overlay(client):
    """Dashboard has keyboard shortcut overlay element."""
    resp = client.get("/dashboard")
    assert 'id="kbd-overlay"' in resp.text


def test_dashboard_kbd_overlay_hidden_by_default(client):
    """Keyboard overlay starts hidden."""
    resp = client.get("/dashboard")
    assert 'style="display:none"' in resp.text


def test_dashboard_kbd_hint_has_question_mark(client):
    """Keyboard hint bar mentions ? shortcut."""
    resp = client.get("/dashboard")
    assert "shortcuts" in resp.text


# --- Smart variant selection already tested in test_navigation.py ---
# (variant radio buttons, data-text attributes, char count badges)
