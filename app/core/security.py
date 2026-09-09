"""
Enterprise Security & Cryptographic Utilities.
Provides standard, dependency-free PBKDF2-HMAC password hashing,
timing-attack resilient verification, and legacy password auto-migration.
"""

import hashlib
import secrets

PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16


def hash_password(plain_password: str) -> str:
    """
    Hashes a plain-text password using PBKDF2-HMAC-SHA256 with a unique random salt.
    Returns: 'salt_hex:hash_hex'
    """
    salt = secrets.token_hex(SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{salt}:{derived_key.hex()}"


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Verifies a plain-text password against a stored password string.
    Supports both PBKDF2 hashed passwords and legacy plain-text passwords
    with constant-time comparison to protect against timing attacks.
    """
    if not stored_password or not plain_password:
        return False

    if ":" not in stored_password:
        # Legacy plain-text fallback (allows seamless login & on-the-fly migration)
        return secrets.compare_digest(plain_password, stored_password)

    parts = stored_password.split(":", 1)
    if len(parts) != 2:
        return False

    salt, expected_hash = parts
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return secrets.compare_digest(derived_key.hex(), expected_hash)


def needs_rehash(stored_password: str) -> bool:
    """
    Checks whether a stored password needs to be upgraded to a modern PBKDF2 hash.
    """
    return ":" not in stored_password

