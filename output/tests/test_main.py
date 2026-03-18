"""Tests for app.py — FastAPI routes, auth, approval flow (multi-tenant)."""

import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    """Create an async TestClient for the FastAPI app with a temp DB and authenticated session."""
    db_path = str(tmp_path / "test_main.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key-for-signing")

    import app as app_mod
    app_mod.DB_PATH = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    # Create a test user
    user = await db.get_or_create_user(conn, "test@example.com", name="Test")
    await db.update_user(conn, user["id"], onboard_step=3, twitter_access_token="t", twitter_access_secret="s")
    await conn.close()

    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Authenticate by setting session cookie (must match Starlette SessionMiddleware format)
        import base64, json
        from itsdangerous import TimestampSigner
        signer = TimestampSigner("test-secret-key-for-signing")
        session_data = {"user_id": user["id"], "user_email": "test@example.com", "user_name": "Test"}
        payload = base64.b64encode(json.dumps(session_data).encode()).decode()
        signed = signer.sign(payload).decode()
        c.cookies.set("session", signed)
        c._test_user_id = user["id"]
        yield c


@pytest.mark.asyncio
async def test_health_no_auth(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_health.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import app as app_mod
    app_mod.DB_PATH = db_path
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await conn.close()
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_dashboard_requires_auth(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_noauth.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import app as app_mod
    app_mod.DB_PATH = db_path
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await conn.close()
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302


@pytest.mark.asyncio
async def test_dashboard_with_auth(client):
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert "gstack" in resp.text.lower()


@pytest.mark.asyncio
async def test_skip_requires_auth(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_skipauth.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import app as app_mod
    app_mod.DB_PATH = db_path
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await conn.close()
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/skip", data={"tweet_id": "t1"}, follow_redirects=False)
        assert resp.status_code in (302, 401)


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
        follow_redirects=False,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_root_redirects_to_login(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_root.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import app as app_mod
    app_mod.DB_PATH = db_path
    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    await conn.close()
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/", follow_redirects=False)
        assert resp.status_code in (301, 302, 303, 307, 308)
        assert "/auth/login" in resp.headers.get("location", "")
