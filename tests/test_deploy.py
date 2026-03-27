"""Tests for deploy service and settings routes."""

import os
import json


def setup_user_with_deploy(db, user_id=1, deploy_config=None):
    """Create an approved user, optionally with deploy config."""
    db.execute(
        "INSERT OR IGNORE INTO users (id, google_id, email, name, is_approved, deploy_config) "
        "VALUES (?, 'g1', 'u@t.com', 'Test User', 1, ?)",
        (user_id, deploy_config)
    )
    db.commit()


def login(client, user_id=1):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id


# ── Crypto service ─────────────────────────────────────

def test_encrypt_decrypt_roundtrip(app):
    """Fernet encrypt/decrypt roundtrip works."""
    os.environ['DEPLOY_ENCRYPTION_KEY'] = app.config['DEPLOY_ENCRYPTION_KEY']
    from app.services.crypto import encrypt_deploy_config, decrypt_deploy_config

    plaintext = 'fly_abc123xyz'
    encrypted = encrypt_deploy_config(plaintext)
    assert encrypted != plaintext
    assert decrypt_deploy_config(encrypted) == plaintext


def test_decrypt_invalid_token(app):
    """Decrypting garbage raises InvalidToken."""
    os.environ['DEPLOY_ENCRYPTION_KEY'] = app.config['DEPLOY_ENCRYPTION_KEY']
    from app.services.crypto import decrypt_deploy_config
    from cryptography.fernet import InvalidToken
    import pytest

    with pytest.raises(InvalidToken):
        decrypt_deploy_config('not-valid-fernet-token')


def test_encrypt_missing_key():
    """Encrypting without key raises ValueError."""
    old = os.environ.pop('DEPLOY_ENCRYPTION_KEY', None)
    from app.services.crypto import encrypt_deploy_config
    import pytest

    try:
        with pytest.raises(ValueError):
            encrypt_deploy_config('test')
    finally:
        if old:
            os.environ['DEPLOY_ENCRYPTION_KEY'] = old


# ── Settings routes ────────────────────────────────────

def test_settings_page_loads(client, db):
    """Settings page loads for approved user."""
    setup_user_with_deploy(db)
    login(client)

    resp = client.get('/settings')
    assert resp.status_code == 200
    assert b'Deploy' in resp.data


def test_settings_shows_configured_status(client, db):
    """Settings shows 'configured' when deploy config exists."""
    setup_user_with_deploy(db, deploy_config='encrypted-token')
    login(client)

    resp = client.get('/settings')
    assert b'configured' in resp.data


def test_settings_shows_not_configured(client, db):
    """Settings shows 'not configured' when no deploy config."""
    setup_user_with_deploy(db)
    login(client)

    resp = client.get('/settings')
    assert b'not configured' in resp.data


def test_settings_clear_deploy_config(client, db):
    """Posting empty token clears deploy config."""
    setup_user_with_deploy(db, deploy_config='old-encrypted')
    login(client)

    resp = client.post('/settings/deploy',
                       data={'fly_token': ''},
                       follow_redirects=True)
    assert b'cleared' in resp.data

    user = db.execute('SELECT deploy_config FROM users WHERE id = 1').fetchone()
    assert user['deploy_config'] is None


def test_settings_rejects_short_token(client, db):
    """Posting a very short token is rejected."""
    setup_user_with_deploy(db)
    login(client)

    resp = client.post('/settings/deploy',
                       data={'fly_token': 'short'},
                       follow_redirects=True)
    assert b'too short' in resp.data


# ── Deploy status endpoint ─────────────────────────────

def test_deploy_status_endpoint(client, db):
    """Deploy status returns current deploy status."""
    setup_user_with_deploy(db)
    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) "
        "VALUES (1, 1, 'T', 'completed')"
    )
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, deploy_status) "
        "VALUES (1, 1, 1, 'tok', 'completed', 'deployed')"
    )
    db.commit()
    login(client)

    resp = client.get('/builds/1/deploy-status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['deploy_status'] == 'deployed'


def test_deploy_status_none(client, db):
    """Deploy status returns 'none' when not deployed."""
    setup_user_with_deploy(db)
    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) "
        "VALUES (1, 1, 'T', 'completed')"
    )
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status) "
        "VALUES (1, 1, 1, 'tok', 'completed')"
    )
    db.commit()
    login(client)

    resp = client.get('/builds/1/deploy-status')
    data = resp.get_json()
    assert data['deploy_status'] == 'none'


# ── Deploy route guards ───────────────────────────────

def test_deploy_requires_fly_app_name(client, db):
    """Deploy rejects builds without fly_app_name."""
    setup_user_with_deploy(db, deploy_config='encrypted')
    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) "
        "VALUES (1, 1, 'T', 'completed')"
    )
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status) "
        "VALUES (1, 1, 1, 'tok', 'completed')"
    )
    db.commit()
    login(client)

    resp = client.post('/builds/1/deploy', follow_redirects=True)
    assert b'No Fly app' in resp.data


def test_deploy_requires_deploy_config(client, db):
    """Deploy rejects when user has no deploy config."""
    setup_user_with_deploy(db)  # no deploy_config
    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) "
        "VALUES (1, 1, 'T', 'completed')"
    )
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, fly_app_name) "
        "VALUES (1, 1, 1, 'tok', 'completed', 'my-app')"
    )
    db.commit()
    login(client)

    resp = client.post('/builds/1/deploy', follow_redirects=True)
    assert b'Settings' in resp.data
