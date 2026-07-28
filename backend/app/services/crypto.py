"""
crypto.py — Field-level encryption for sensitive credentials.

Used for proxy auth tokens (styxproxy_password) which need to be retrievable
as plaintext for receipt rendering, email delivery, and rotation, but should
not be visible to anyone with raw database read access.

Algorithm: Fernet (AES-128-CBC + HMAC-SHA256, versioned ciphertext format)
from the `cryptography` library. The key is a 32-byte URL-safe base64 string
loaded from the CRED_ENCRYPTION_KEY environment variable — generated once
and stored in your secrets manager (Doppler, Vault, AWS Secrets Manager, etc.).

Properties:
- Confidentiality: AES-128-CBC with the secret key
- Integrity: HMAC-SHA256 (tampering causes decryption failure)
- Versioned: Fernet ciphertexts embed a version byte, allowing future
  algorithm upgrades via key rotation
- Authenticated: decrypt returns None on bad ciphertext (vs raising)

Operational notes:
- Losing CRED_ENCRYPTION_KEY means losing access to all stored credentials —
  there is no recovery, so back up the key separately from the database.
- Rotation: add a new key, decrypt with old + re-encrypt with new in a
  background job, then deprecate the old. Out of scope for this PR.
"""

from __future__ import annotations

import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

logger = logging.getLogger(__name__)

# Lazily-initialized Fernet instance. We don't fail at import time because the
# settings module may be loaded in contexts (CLI scripts, tests) where the
# encryption key isn't required. The first call to encrypt/decrypt validates
# the key.
_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Optional[Fernet]:
    """Return a Fernet instance if CRED_ENCRYPTION_KEY is configured.

    Returns None if the key is missing — callers should treat this as "no
    encryption available" and refuse to read/write the encrypted column.
    """
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    # Use get_settings() rather than a module-level cache so test fixtures and
    # env-driven reloads see the latest value.
    settings = get_settings()
    key = settings.cred_encryption_key
    if not key:
        logger.warning(
            "CRED_ENCRYPTION_KEY not configured — credential encryption is "
            "disabled. styxproxy_password will NOT be encrypted at rest."
        )
        _fernet_instance = None
        return None

    try:
        _fernet_instance = Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as e:
        logger.error(
            "CRED_ENCRYPTION_KEY is malformed (must be a Fernet key, base64-url-safe "
            "32-byte string): %s — credential encryption disabled.",
            e,
        )
        _fernet_instance = None
        return None

    return _fernet_instance


def encrypt_credential(plaintext: str) -> Optional[bytes]:
    """Encrypt a credential value (e.g. proxy password) for storage.

    Returns the Fernet ciphertext as bytes (suitable for a LargeBinary column).
    Returns None if encryption is not configured — caller should refuse to write.
    """
    f = _get_fernet()
    if f is None:
        return None
    try:
        return f.encrypt(plaintext.encode("utf-8"))
    except Exception as e:
        logger.error("Failed to encrypt credential: %s", e)
        return None


def decrypt_credential(ciphertext: Optional[bytes]) -> Optional[str]:
    """Decrypt a stored credential value back to plaintext.

    Returns None on:
    - encryption not configured (so we don't accidentally return plaintext)
    - column is NULL
    - ciphertext is malformed/tampered
    """
    if ciphertext is None:
        return None

    f = _get_fernet()
    if f is None:
        logger.error(
            "Cannot decrypt credential: CRED_ENCRYPTION_KEY not configured. " "Set the key in your secrets manager."
        )
        return None

    try:
        return f.decrypt(ciphertext).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as e:
        logger.error("Failed to decrypt credential (tampered or wrong key?): %s", e)
        return None


def mask_credential(plaintext: Optional[str], visible_chars: int = 3) -> str:
    """Mask a credential for display in API responses (e.g. 'sty_********').

    Keeps only the first few chars visible so support staff can correlate a
    credential across logs without exposing the full secret.
    """
    if not plaintext:
        return "—"
    if len(plaintext) <= visible_chars:
        return "•" * len(plaintext)
    return plaintext[:visible_chars] + "•" * (len(plaintext) - visible_chars)


def generate_fernet_key() -> str:
    """Generate a new random Fernet key. Use this to create CRED_ENCRYPTION_KEY
    for your first deployment. Never reuse a key across environments."""
    return Fernet.generate_key().decode("ascii")
