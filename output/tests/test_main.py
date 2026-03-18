"""Tests for app.py — FastAPI routes, auth, approval flow."""

import base64
import os
import sys

import pytest
import pytest_asyncio

# Ensure output/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _basic_auth_header(username: str = "testuser", password: str = "testpass") -> dict:
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {creds}"}


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    """Create an async TestClient for the FastAPI app with a temp DB."""
    db_path = str(tmp_path / "test_main.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("DASHBOARD_USERNAME", "testuser")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "testpass")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-key-for-signing")

    import app as app_mod
    app_mod.DB_PATH = db_path

    # Initialize schema before tests (ASGI transport skips lifespan)
    import db
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await conn.close()

    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_no_auth(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    resp = await client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_with_basic_auth(client):
    resp = await client.get("/dashboard", headers=_basic_auth_header())
    assert resp.status_code == 200
    assert "gstack" in resp.text.lower()


@pytest.mark.asyncio
async def test_dashboard_wrong_password(client):
    resp = await client.get(
        "/dashboard",
        headers=_basic_auth_header("testuser", "wrong"),
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_sets_cookie(client):
    resp = await client.get("/dashboard", headers=_basic_auth_header())
    assert resp.status_code == 200
    assert "gstack_session" in resp.cookies


@pytest.mark.asyncio
async def test_skip_requires_auth(client):
    resp = await client.post("/skip", data={"tweet_id": "t1"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_approve_empty_text_rejected(client):
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "t1",
            "variant_id": "1",
            "reply_text": "",
            "send_window": "morning",
        },
        headers=_basic_auth_header(),
        follow_redirects=False,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_approve_over_280_rejected(client):
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "t1",
            "variant_id": "1",
            "reply_text": "x" * 281,
            "send_window": "morning",
        },
        headers=_basic_auth_header(),
        follow_redirects=False,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_invalid_window_rejected(client):
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "t1",
            "variant_id": "1",
            "reply_text": "Hello!",
            "send_window": "midnight",
        },
        headers=_basic_auth_header(),
        follow_redirects=False,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_root_redirects_to_dashboard(client):
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302, 303, 307, 308)
    assert "/dashboard" in resp.headers.get("location", "")
