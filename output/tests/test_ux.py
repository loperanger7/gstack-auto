"""Tests for UX improvements — auto-select window, keyboard overlay, smart defaults."""

import base64
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    """Create a real SQLite db file with test data."""
    db_path = str(tmp_path / "ux_test.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await db.upsert_tweet(
        conn, tweet_id="tweet-ux-1", author_id="author-1",
        author_name="UX Test", follower_count=1000,
        text="gstack is great!", sentiment="praise",
    )
    await db.save_variants(conn, "tweet-ux-1", [
        {"label": "A", "text": "Short reply"},
        {"label": "B", "text": "A longer reply that uses more characters"},
    ])
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


# --- Auto-select send window ---

def test_dashboard_has_default_window(client):
    """Dashboard select has a selected option (not hardcoded to morning)."""
    resp = client.get("/dashboard", headers=_auth())
    assert resp.status_code == 200
    assert "selected" in resp.text


def test_dashboard_default_window_is_valid(client):
    """The selected window is one of morning/lunch/evening."""
    resp = client.get("/dashboard", headers=_auth())
    # One of the options should have 'selected'
    import re
    matches = re.findall(r'value="(\w+)"[^>]*selected', resp.text)
    assert len(matches) >= 1
    assert matches[0] in ("morning", "lunch", "evening")


# --- Keyboard shortcut overlay ---

def test_dashboard_has_kbd_overlay(client):
    """Dashboard has keyboard shortcut overlay element."""
    resp = client.get("/dashboard", headers=_auth())
    assert 'id="kbd-overlay"' in resp.text


def test_dashboard_kbd_overlay_hidden_by_default(client):
    """Keyboard overlay starts hidden."""
    resp = client.get("/dashboard", headers=_auth())
    assert 'style="display:none"' in resp.text


def test_dashboard_kbd_hint_has_question_mark(client):
    """Keyboard hint bar mentions ? shortcut."""
    resp = client.get("/dashboard", headers=_auth())
    assert "shortcuts" in resp.text


# --- Smart variant selection already tested in test_navigation.py ---
# (variant radio buttons, data-text attributes, char count badges)
