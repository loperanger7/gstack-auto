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
    """Verify HMAC-SHA256 of the request body matches the nonce.

    The pipeline computes: HMAC-SHA256(nonce, request_body_bytes)
    and sends it in X-Payload-SHA header.

    Returns (valid: bool, error: str|None).
    """
    nonce = token_payload.get('nonce')
    if not nonce:
        return False, 'Missing nonce in token'

    if not check_and_use_nonce(nonce):
        return False, 'Nonce already used or invalid'

    return True, None


def compute_payload_sha(nonce, body_bytes):
    """Compute the SHA that the pipeline should send. Used for testing."""
    return hmac.new(nonce.encode(), body_bytes, hashlib.sha256).hexdigest()
