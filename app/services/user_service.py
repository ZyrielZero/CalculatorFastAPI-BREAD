from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.tokens import issue_access_token
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead
from app.security import hash_password, verify_password


class DuplicateUserError(Exception):
    """Raised when username or email collides with an existing row."""


def register_user(db: Session, payload: UserCreate) -> User:
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUserError("username or email is already taken") from None
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> Token | None:
    """Authenticate by username or email.

    The OAuth2 password form only carries a ``username`` field, but the
    login page asks for an email per the assignment. Matching on either
    column lets both flows share one endpoint without changing the form
    contract Swagger's Authorize button depends on.
    """
    user = db.scalar(
        select(User).where(
            (User.username == identifier) | (User.email == identifier)
        )
    )
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return Token(
        access_token=issue_access_token(user.id),
        user=UserRead.model_validate(user),
    )