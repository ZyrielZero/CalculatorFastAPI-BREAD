"""Password hashing helpers. bcrypt is used directly rather than through
passlib: passlib 1.7.4 is unmaintained and raises AttributeError against
bcrypt >= 4.1 when reading the removed __about__ attribute."""

import bcrypt

_BCRYPT_INPUT_LIMIT = 72  # bytes; bcrypt silently truncates beyond this


def hash_password(raw: str) -> str:
    """Hash a plaintext password with bcrypt; returns the encoded hash string."""
    material = raw.encode("utf-8")
    if len(material) > _BCRYPT_INPUT_LIMIT:
        raise ValueError("password exceeds bcrypt's 72-byte input limit")
    return bcrypt.hashpw(material, bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, stored_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash.

    Returns False (rather than raising) for malformed stored hashes, so a
    corrupted row reads as a failed login instead of a 500.
    """
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False