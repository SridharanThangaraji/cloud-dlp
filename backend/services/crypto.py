"""Encrypt content and compute hash for integrity verification."""
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet

from config import ENCRYPTION_KEY_ENV, ENCRYPTION_KEY_FILE


def _get_key() -> bytes:
    """Load or create Fernet key from env or key file."""
    key_b64 = os.environ.get(ENCRYPTION_KEY_ENV)
    if key_b64:
        return key_b64.encode() if isinstance(key_b64, str) else key_b64
    if ENCRYPTION_KEY_FILE.exists():
        return ENCRYPTION_KEY_FILE.read_bytes().strip()
    key = Fernet.generate_key()
    ENCRYPTION_KEY_FILE.write_bytes(key)
    return key


def encrypt_and_hash(content: bytes) -> tuple[bytes, str]:
    """
    Encrypt content and return (encrypted_bytes, sha256_hex_of_encrypted).
    Hash is of the encrypted blob so we can verify stored file integrity.
    """
    f = Fernet(_get_key())
    encrypted = f.encrypt(content)
    h = hashlib.sha256(encrypted).hexdigest()
    return encrypted, h


def verify_hash(content: bytes, expected_hex: str) -> bool:
    """Return True if SHA-256(content).hexdigest() == expected_hex."""
    return hashlib.sha256(content).hexdigest() == expected_hex
