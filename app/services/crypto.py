"""Fernet encryption for deploy tokens (Fly API keys)."""

import os
from cryptography.fernet import Fernet, InvalidToken


def _get_fernet():
    """Get Fernet instance using DEPLOY_ENCRYPTION_KEY env var."""
    key = os.environ.get('DEPLOY_ENCRYPTION_KEY', '')
    if not key:
        raise ValueError('DEPLOY_ENCRYPTION_KEY not set')
    return Fernet(key.encode())


def encrypt_deploy_config(plaintext: str) -> str:
    """Encrypt a deploy config string. Returns base64 Fernet token."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_deploy_config(ciphertext: str) -> str:
    """Decrypt a deploy config string. Raises InvalidToken on failure."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
