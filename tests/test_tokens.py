"""Tests for JWT token generation and validation."""

import time
import jwt as pyjwt


def test_generate_and_validate(app, db):
    """Generate a token and validate it."""
    with app.app_context():
        from app.services.tokens import generate_build_token, validate_build_token

        # Need a build in the DB for the nonce FK
        db.execute(
            "INSERT INTO users (id, google_id, email, is_approved) VALUES (1, 'g1', 'u@t.com', 1)"
        )
        db.execute(
            "INSERT INTO builds (id, user_id, build_token, status) VALUES (1, 1, 'tok', 'pending')"
        )
        db.commit()

        token = generate_build_token(user_id=1, build_id=1)
        assert token is not None

        payload = validate_build_token(token)
        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['build_id'] == 1
        assert 'nonce' in payload


def test_expired_token(app):
    """Expired tokens are rejected."""
    with app.app_context():
        from app.services.tokens import validate_build_token

        payload = {
            'user_id': 1,
            'build_id': 1,
            'nonce': 'test',
            'iat': int(time.time()) - 7200,
            'exp': int(time.time()) - 3600,  # Expired 1h ago
        }
        token = pyjwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

        result = validate_build_token(token)
        assert result is None


def test_invalid_token(app):
    """Tokens signed with wrong key are rejected."""
    with app.app_context():
        from app.services.tokens import validate_build_token

        payload = {'user_id': 1, 'build_id': 1, 'exp': int(time.time()) + 3600}
        token = pyjwt.encode(payload, 'wrong-secret', algorithm='HS256')

        result = validate_build_token(token)
        assert result is None


def test_nonce_one_time_use(app, db):
    """Nonce can only be checked/used once."""
    with app.app_context():
        from app.models import store_nonce, check_and_use_nonce

        db.execute(
            "INSERT INTO users (id, google_id, email, is_approved) VALUES (1, 'g1', 'u@t.com', 1)"
        )
        db.execute(
            "INSERT INTO builds (id, user_id, build_token, status) VALUES (1, 1, 'tok', 'pending')"
        )
        db.commit()

        store_nonce('test-nonce', build_id=1)

        assert check_and_use_nonce('test-nonce') is True
        assert check_and_use_nonce('test-nonce') is False  # Already used


def test_nonexistent_nonce(app, db):
    """Nonexistent nonce returns False."""
    with app.app_context():
        from app.models import check_and_use_nonce
        assert check_and_use_nonce('does-not-exist') is False
