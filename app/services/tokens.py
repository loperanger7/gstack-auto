"""JWT build token generation and validation with nonce + SHA integrity."""

import hashlib
import hmac
import json
import secrets
import time

import jwt
from flask import current_app

from app.models import store_nonce, check_and_use_nonce


def generate_build_token(user_id, build_id):
    """Generate a JWT build token with an embedded nonce."""
    nonce = secrets.token_urlsafe(32)
    store_nonce(nonce, build_id)

    payload = {
        'user_id': user_id,
        'build_id': build_id,
        'nonce': nonce,
        'iat': int(time.time()),
        'exp': int(time.time()) + 86400,  # 24h
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token


def validate_build_token(token):
    """Validate JWT, check expiry. Returns decoded payload or None."""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_payload_integrity(token_payload, request_body):
    """Verify nonce one-time-use and HMAC-SHA256 payload integrity.

    The pipeline computes: HMAC-SHA256(nonce, request_body_bytes)
    and sends it in X-Payload-SHA header.

    Returns (valid: bool, error: str|None).
    """
    from flask import request as flask_request

    nonce = token_payload.get('nonce')
    if not nonce:
        return False, 'Missing nonce in token'

    if not check_and_use_nonce(nonce):
        return False, 'Nonce already used or invalid'

    # Verify payload SHA if header present (defense in depth)
    expected_sha = flask_request.headers.get('X-Payload-SHA')
    if expected_sha:
        actual_sha = compute_payload_sha(nonce, request_body)
        if not hmac.compare_digest(expected_sha, actual_sha):
            return False, 'Payload integrity check failed'

    return True, None


def compute_payload_sha(nonce, body_bytes):
    """Compute the HMAC-SHA256 that the pipeline should send."""
    return hmac.new(nonce.encode(), body_bytes, hashlib.sha256).hexdigest()  # hmac.new is an alias for hmac.HMAC
