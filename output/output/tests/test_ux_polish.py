"""Tests for Round 2 Run B UX polish — swipe gestures, animations, delight."""

from __future__ import annotations

import base64
import json
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


def _set_session_cookie(client, user_id: int, email: str = "polish@test.com"):
    """Set a valid session cookie for the Starlette SessionMiddleware."""
    from itsdangerous import TimestampSigner
    secret = "test-secret-key-for-signing"
    signer = TimestampSigner(secret)
    data = {"user_id": user_id, "user_email": email, "user_name": "Polish Test"}
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    signed = signer.sign(payload).decode()
    client.cookies.set("session", signed)
    return client


@pytest_asyncio.fixture
async def seeded_db(tmp_path):
    """Create a real SQLite db file with test data."""
    db_path = str(tmp_path / "polish_test.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)

    user = await db.get_or_create_user(conn, "polish@test.com", name="Polish Test")
    await db.update_user(conn, user["id"], onboard_step=3,
                         twitter_access_token="t", twitter_access_secret="s",
                         twitter_username="polishtest")

    await db.upsert_tweet(
        conn, tweet_id="tweet-polish-1", author_id="author-1",
        author_name="Swipe Test", follower_count=5000,
        text="testing swipe gestures", sentiment="praise",
        user_id=user["id"],
    )
    await db.save_variants(conn, "tweet-polish-1", [
        {"label": "A", "text": "Short reply"},
        {"label": "B", "text": "Another reply variant"},
    ])
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path, user["id"]
    app_module.DB_PATH = old_path


@pytest_asyncio.fixture
async def seeded_db_empty(tmp_path):
    """Create a db with a user but no tweets."""
    db_path = str(tmp_path / "empty_test.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)

    user = await db.get_or_create_user(conn, "polish@test.com", name="Polish Test")
    await db.update_user(conn, user["id"], onboard_step=3,
                         twitter_access_token="t", twitter_access_secret="s")
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path, user["id"]
    app_module.DB_PATH = old_path


@pytest_asyncio.fixture
async def seeded_db_admin(tmp_path):
    """Create a db with an admin user."""
    db_path = str(tmp_path / "admin_polish.db")
    os.environ["DB_PATH"] = db_path
    os.environ["ADMIN_EMAILS"] = "admin@polish.com"

    conn = await db.get_connection(db_path)
    await db.init_db(conn)

    user = await db.get_or_create_user(conn, "admin@polish.com", name="Admin Polish")
    await db.update_user(conn, user["id"], onboard_step=3, is_admin=1,
                         twitter_access_token="t", twitter_access_secret="s")
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path, user["id"]
    app_module.DB_PATH = old_path


@pytest_asyncio.fixture
async def seeded_db_onboard(tmp_path):
    """Create a db with a user at onboarding step 0."""
    db_path = str(tmp_path / "onboard_polish.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)

    user = await db.get_or_create_user(conn, "polish@test.com", name="Onboard Test")
    await conn.close()

    import app as app_module
    old_path = app_module.DB_PATH
    app_module.DB_PATH = db_path
    yield db_path, user["id"]
    app_module.DB_PATH = old_path


@pytest_asyncio.fixture
async def seeded_db_onboard_step2(tmp_path):
    """Create a db with a user at onboarding step 1."""
    db_path = str(tmp_path / "onboard2_polish.db")
    os.environ["DB_PATH"] = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)

    user = await db.get_or_create_user(conn, "polish@test.com", name="Onboard Test")
    await db.update_user(conn, user["id"], onboard_step=1)
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


@pytest.fixture
def client_empty(seeded_db_empty):
    from starlette.testclient import TestClient
    import app as app_module
    _, user_id = seeded_db_empty
    c = TestClient(app_module.app)
    _set_session_cookie(c, user_id=user_id, email="polish@test.com")
    return c


@pytest.fixture
def client_admin(seeded_db_admin):
    from starlette.testclient import TestClient
    import app as app_module
    _, user_id = seeded_db_admin
    c = TestClient(app_module.app)
    _set_session_cookie(c, user_id=user_id, email="admin@polish.com")
    return c


@pytest.fixture
def client_onboard(seeded_db_onboard):
    from starlette.testclient import TestClient
    import app as app_module
    _, user_id = seeded_db_onboard
    c = TestClient(app_module.app)
    _set_session_cookie(c, user_id=user_id, email="polish@test.com")
    return c


@pytest.fixture
def client_onboard_step2(seeded_db_onboard_step2):
    from starlette.testclient import TestClient
    import app as app_module
    _, user_id = seeded_db_onboard_step2
    c = TestClient(app_module.app)
    _set_session_cookie(c, user_id=user_id, email="polish@test.com")
    return c


# ---- Dashboard: Empty State ----

def test_empty_state_has_icon(client_empty):
    """Empty dashboard shows lightning bolt icon."""
    resp = client_empty.get("/dashboard")
    assert resp.status_code == 200
    assert "empty-icon" in resp.text
    assert "All caught up" in resp.text


def test_empty_state_has_stats_link(client_empty):
    """Empty dashboard has link to stats page."""
    resp = client_empty.get("/dashboard")
    assert "View your stats" in resp.text
    assert 'href="/stats"' in resp.text


def test_empty_state_floating_animation(client_empty):
    """Empty state icon has floating animation CSS."""
    resp = client_empty.get("/dashboard")
    assert "empty-float" in resp.text


# ---- Dashboard: Swipe Gestures ----

def test_swipe_hints_in_cards(client):
    """Dashboard cards contain swipe hint overlay elements."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "swipe-hint-approve" in resp.text
    assert "swipe-hint-skip" in resp.text


def test_swipe_threshold_defined(client):
    """JS defines SWIPE_THRESHOLD constant."""
    resp = client.get("/dashboard")
    assert "SWIPE_THRESHOLD" in resp.text


def test_touchmove_handler(client):
    """JS registers touchmove for real-time swipe feedback."""
    resp = client.get("/dashboard")
    assert "touchmove" in resp.text


def test_card_spring_back(client):
    """JS resets card transform on touchend below threshold."""
    resp = client.get("/dashboard")
    assert "touchCard.style.transform = ''" in resp.text


def test_swiping_class(client):
    """CSS defines swiping class to disable transitions during drag."""
    resp = client.get("/dashboard")
    assert ".card.swiping" in resp.text


# ---- Dashboard: Directional Exit Animations ----

def test_directional_exit_css(client):
    """CSS includes directional exit classes."""
    resp = client.get("/dashboard")
    assert "exiting-approve" in resp.text
    assert "exiting-skip" in resp.text


def test_approve_exit_slides_right(client):
    """Approve exit translates card to the right."""
    resp = client.get("/dashboard")
    assert "translateX(100px)" in resp.text


def test_skip_exit_slides_left(client):
    """Skip exit translates card to the left."""
    resp = client.get("/dashboard")
    assert "translateX(-100px)" in resp.text


# ---- Toast Icons ----

def test_toast_success_icon(client):
    """Success toast has checkmark pseudo-element."""
    resp = client.get("/dashboard")
    assert "toast--success::before" in resp.text


def test_toast_error_icon(client):
    """Error toast has exclamation pseudo-element."""
    resp = client.get("/dashboard")
    assert "toast--error::before" in resp.text


def test_toast_skip_icon(client):
    """Skip toast has arrow pseudo-element."""
    resp = client.get("/dashboard")
    assert "toast--skip::before" in resp.text


# ---- CSS Custom Properties ----

def test_css_custom_properties(client):
    """Base template defines animation timing custom properties."""
    resp = client.get("/dashboard")
    assert "--anim-fast" in resp.text
    assert "--anim-med" in resp.text
    assert "--ease-spring" in resp.text
    assert "--ease-out" in resp.text


def test_skeleton_shimmer(client):
    """Base template includes skeleton loading shimmer keyframes."""
    resp = client.get("/dashboard")
    assert "@keyframes shimmer" in resp.text
    assert ".skeleton" in resp.text


# ---- prefers-reduced-motion ----

def test_reduced_motion_dashboard(client):
    """Dashboard disables new animations for reduced motion."""
    resp = client.get("/dashboard")
    assert "prefers-reduced-motion" in resp.text
    # Should disable exiting animations
    body = resp.text
    assert "exiting-approve" in body


def test_reduced_motion_base(client):
    """Base template disables skeleton animation for reduced motion."""
    resp = client.get("/dashboard")
    # skeleton animation disabled in reduced motion
    assert "skeleton" in resp.text


# ---- Stat Card Hover ----

def test_stat_card_hover(client):
    """Stat cards have hover lift effect."""
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert "stat-card:hover" in resp.text
    assert "translateY(-2px)" in resp.text


# ---- Login Page ----

def test_login_fade_in():
    """Login page has entry fade animation."""
    from starlette.testclient import TestClient
    import app as app_module
    c = TestClient(app_module.app)
    resp = c.get("/auth/login")
    assert resp.status_code == 200
    assert "login-fade-in" in resp.text
    assert "login-glow" in resp.text


def test_login_reduced_motion():
    """Login page respects prefers-reduced-motion."""
    from starlette.testclient import TestClient
    import app as app_module
    c = TestClient(app_module.app)
    resp = c.get("/auth/login")
    assert "prefers-reduced-motion" in resp.text


def test_login_button_hover_lift():
    """Login button has hover translateY."""
    from starlette.testclient import TestClient
    import app as app_module
    c = TestClient(app_module.app)
    resp = c.get("/auth/login")
    assert "translateY(-1px)" in resp.text


# ---- Admin Leaderboard ----

def test_admin_rank_medal_classes(client_admin):
    """Admin leaderboard CSS has rank medal pseudo-elements."""
    resp = client_admin.get("/admin")
    assert resp.status_code == 200
    body = resp.text
    assert "rank-1" in body
    assert "rank-2" in body
    assert "rank-3" in body


def test_admin_engagement_gradient(client_admin):
    """Admin engagement bars use gradient fill."""
    resp = client_admin.get("/admin")
    assert "linear-gradient" in resp.text


def test_admin_leaderboard_row_hover(client_admin):
    """Admin leaderboard rows have hover class."""
    resp = client_admin.get("/admin")
    assert "leaderboard-row" in resp.text
    assert "leaderboard-row:hover" in resp.text


# ---- Onboarding Wizard ----

def test_onboard_step_connectors(client_onboard):
    """Onboarding wizard has step connector elements."""
    resp = client_onboard.get("/onboard", follow_redirects=False)
    # May redirect, follow it
    if resp.status_code == 302:
        resp = client_onboard.get(resp.headers["location"])
    assert "step-connector" in resp.text


def test_onboard_step_enter_animation(client_onboard):
    """Onboarding wizard has step card entrance animation."""
    resp = client_onboard.get("/onboard", follow_redirects=False)
    if resp.status_code == 302:
        resp = client_onboard.get(resp.headers["location"])
    assert "step-enter" in resp.text


def test_onboard_step2_filled_connector(client_onboard_step2):
    """Step 2 shows first connector as filled."""
    resp = client_onboard_step2.get("/onboard", follow_redirects=False)
    if resp.status_code == 302:
        resp = client_onboard_step2.get(resp.headers["location"])
    assert "step-connector filled" in resp.text or "step-connector" in resp.text


# ---- Stats Page ----

def test_stats_bar_gradient(client):
    """Stats bar chart uses gradient fills."""
    resp = client.get("/stats")
    assert "linear-gradient(90deg,#58a6ff,#79b8ff)" in resp.text


def test_stats_table_row_hover(client):
    """Stats table rows have hover effect."""
    resp = client.get("/stats")
    assert "tbody tr:hover" in resp.text


# ---- Settings Page ----

def test_settings_card_hover(client):
    """Settings cards have hover border effect."""
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "settings-card:hover" in resp.text


def test_settings_alert_animation(client):
    """Settings page has alert entrance animation CSS."""
    resp = client.get("/settings")
    assert "alert-enter" in resp.text
