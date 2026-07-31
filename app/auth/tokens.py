from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.config import settings


def issue_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def read_token_subject(token: str) -> UUID | None:
    """Decode a token and return its subject id, or None for any invalid token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            leeway=10,  # tolerate small clock skew (WSL2 drifts after sleep)
        )
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None