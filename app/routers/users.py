"""HTTP surface for the user service.

Registration takes the JSON UserCreate payload the schema layer already
validates. Login deliberately accepts the OAuth2 password form instead
of JSON: OAuth2PasswordBearer advertises a form-encoded token endpoint,
so this is what makes the Swagger UI Authorize button work end to end.
Both failure modes of login — unknown username and wrong password —
return byte-identical 401 responses, so the API never confirms whether
a username exists.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import Token, UserCreate, UserRead
from app.services.user_service import (
    DuplicateUserError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    """Create a user; 409 when username or email is already taken."""
    try:
        user = register_user(db, payload)
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from None
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    """Exchange form credentials for a bearer token."""
    token = authenticate_user(db, form.username, form.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# The assignment names the endpoints /register and /login; this project's
# routes carry a /users prefix inherited from the previous module. Rather
# than move them and break every existing test and the Swagger token URL,
# a second router exposes the spec paths and delegates to the same two
# functions. One implementation, two addresses. The GET routes serving
# the HTML pages live at the same paths on a different method, which
# FastAPI resolves independently.
alias_router = APIRouter(tags=["users"])


@alias_router.post(
    "/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
def register_alias(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    """Spec-path alias for POST /users/register."""
    return register(payload, db)


@alias_router.post("/login", response_model=Token)
def login_alias(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    """Spec-path alias for POST /users/login."""
    return login(form, db)