from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Inbound payload for registration: the assignment's three fields."""

    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, value: str) -> str:
        if value == value.lower() or value == value.upper():
            raise ValueError("password must mix upper and lower case")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("password must include at least one digit")
        return value


class UserRead(BaseModel):
    """Outbound user representation. password_hash is not declared,
    so it cannot serialize — omission is the leak prevention."""

    id: UUID
    username: str
    email: EmailStr
    is_active: bool
    last_login: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Bearer token envelope returned by authentication."""

    access_token: str
    token_type: str = "bearer"
    user: UserRead