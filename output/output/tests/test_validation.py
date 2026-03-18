"""Tests for input validation hardening in app.py routes.
Paranoid edge cases: SQL injection, control chars, boundary values."""

import base64
import json
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


def _set_session_cookie(client, user_id: int = 1, email: str = "test@example.com"):
    """Set a valid session cookie for the Starlette SessionMiddleware.
    Uses the conftest default key since SessionMiddleware captures it at import time."""
    from itsdangerous import TimestampSigner
    secret = "test-secret-key-for-signing"
    signer = TimestampSigner(secret)
    data = {"user_id": user_id, "user_email": email, "user_name": "Test"}
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    signed = signer.sign(payload).decode()
    client.cookies.set("session", signed)
    return client


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    """Async TestClient with temp DB, user, and session auth for validation tests."""
    db_path = str(tmp_path / "test_validation.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key-for-signing")

    import app as app_mod
    app_mod.DB_PATH = db_path

    conn = await db.get_connection(db_path)
    await db.init_db(conn)
    user = await db.get_or_create_user(conn, "test@example.com", name="Test")
    await db.update_user(conn, user["id"], onboard_step=3,
                         twitter_access_token="t", twitter_access_secret="s")
    await conn.close()

    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        _set_session_cookie(c, user_id=user["id"])
        c._test_user_id = user["id"]
        yield c


@pytest.mark.asyncio
async def test_approve_rejects_sql_injection_tweet_id(client):
    """SQL injection in tweet_id returns 400, never reaches DB."""
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "'; DROP TABLE tweets--",
            "variant_id": "1",
            "reply_text": "test reply",
            "send_window": "morning",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Invalid request"


@pytest.mark.asyncio
async def test_approve_rejects_negative_variant_id(client):
    """Negative variant_id returns 400."""
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "12345",
            "variant_id": "-1",
            "reply_text": "test reply",
            "send_window": "morning",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_strips_control_chars(client):
    """Control characters in reply_text are stripped before validation."""
    import app as app_mod

    conn = await db.get_connection(app_mod.DB_PATH)
    await db.upsert_tweet(conn, "t1", "a1", "user", 100, "text",
                          user_id=client._test_user_id)
    await db.save_variants(conn, "t1", [{"text": "reply", "label": "A"}])
    cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id = 't1'")
    vid = (await cursor.fetchone())[0]
    await conn.close()

    # Reply with null bytes and control chars — should be stripped, not rejected
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "t1",
            "variant_id": str(vid),
            "reply_text": "clean\x00text\x07here",
            "send_window": "morning",
        },
        follow_redirects=False,
    )
    # Should succeed (redirect) or conflict (409), but NOT crash
    assert resp.status_code in (303, 409, 200)


@pytest.mark.asyncio
async def test_approve_rejects_very_long_tweet_id(client):
    """Tweet ID over 64 chars is rejected."""
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "a" * 200,
            "variant_id": "1",
            "reply_text": "test reply",
            "send_window": "morning",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_skip_rejects_invalid_tweet_id(client):
    """Skip with special chars in tweet_id returns 400."""
    resp = await client.post(
        "/skip",
        data={"tweet_id": "<script>alert(1)</script>"},
        follow_redirects=False,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_generic_error_no_leak(client):
    """Error messages don't leak valid send window names."""
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "12345",
            "variant_id": "1",
            "reply_text": "test",
            "send_window": "midnight",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 400
    body = resp.json()
    # Error message should be generic, not reveal valid options
    assert "morning" not in body.get("error", "").lower()
    assert "lunch" not in body.get("error", "").lower()
    assert "evening" not in body.get("error", "").lower()


@pytest.mark.asyncio
async def test_approve_rejects_zero_variant_id(client):
    """variant_id=0 is rejected (must be positive)."""
    resp = await client.post(
        "/approve",
        data={
            "tweet_id": "12345",
            "variant_id": "0",
            "reply_text": "test reply",
            "send_window": "morning",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 400
