"""Fernet encryption helpers for Twitter OAuth tokens.
Every input is hostile. Fail closed on any error."""

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Get Fernet instance from APP_FERNET_KEY env var.
    Raises ValueError if key is missing or invalid."""
    key = os.environ.get("APP_FERNET_KEY", "")
    if not key:
        raise ValueError("APP_FERNET_KEY not set")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string. Returns base64-encoded ciphertext."""
    if not plaintext or not plaintext.strip():
        raise ValueError("Cannot encrypt empty token")
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a token string. Raises ValueError on any failure (fail closed)."""
    if not ciphertext or not ciphertext.strip():
        raise ValueError("Cannot decrypt empty ciphertext")
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        log.error("Token decryption failed — possible key rotation or corruption")
        raise ValueError("Token decryption failed")
    except Exception as e:
        log.error("Unexpected decryption error: %s", e)
        raise ValueError(f"Decryption error: {e}")


def generate_key() -> str:
    """Generate a new Fernet key. Utility for setup."""
    return Fernet.generate_key().decode("utf-8")
