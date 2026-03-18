"""Tests for crypto.py — Fernet encryption helpers."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def fernet_key():
    """Set a valid Fernet key for all tests in this module."""
    key = Fernet.generate_key().decode()
    old = os.environ.get("APP_FERNET_KEY", "")
    os.environ["APP_FERNET_KEY"] = key
    yield key
    os.environ["APP_FERNET_KEY"] = old


def test_encrypt_decrypt_roundtrip():
    import crypto
    plaintext = "my-secret-twitter-token"
    encrypted = crypto.encrypt_token(plaintext)
    assert encrypted != plaintext
    decrypted = crypto.decrypt_token(encrypted)
    assert decrypted == plaintext


def test_encrypt_empty_raises():
    import crypto
    with pytest.raises(ValueError, match="empty"):
        crypto.encrypt_token("")


def test_decrypt_empty_raises():
    import crypto
    with pytest.raises(ValueError, match="empty"):
        crypto.decrypt_token("")


def test_decrypt_bad_ciphertext_raises():
    import crypto
    with pytest.raises(ValueError, match="decryption"):
        crypto.decrypt_token("not-valid-ciphertext")


def test_decrypt_wrong_key():
    import crypto
    encrypted = crypto.encrypt_token("secret")
    # Change the key
    os.environ["APP_FERNET_KEY"] = Fernet.generate_key().decode()
    with pytest.raises(ValueError, match="decryption"):
        crypto.decrypt_token(encrypted)


def test_encrypt_no_key():
    import crypto
    os.environ["APP_FERNET_KEY"] = ""
    with pytest.raises(ValueError, match="not set"):
        crypto.encrypt_token("test")


def test_generate_key():
    import crypto
    key = crypto.generate_key()
    assert len(key) == 44  # Fernet keys are 44 chars base64
    # Verify it's a valid Fernet key
    Fernet(key.encode())
