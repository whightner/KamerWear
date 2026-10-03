"""Auth and account request/response shapes. Password hashes are never included."""

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from app.models import Role

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128


def check_password_policy(password: str) -> str:
    """Length-based policy: passphrases welcome, no composition rules, no truncation."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters. "
            "A short phrase works well."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters.")
    if not password.strip():
        raise ValueError("Password cannot be only spaces.")
    return password


def normalize_phone(value: str | None) -> str | None:
    """Accepts '+237 6 99 11 22 33' style input and stores '+237699112233'."""
    if value is None:
        return None
    compact = re.sub(r"[\s().-]", "", value)
    if not compact:
        return None
    if not re.fullmatch(r"\+?\d{6,15}", compact):
        raise ValueError("Enter a valid phone number, e.g. +237 6 99 11 22 33.")
    return compact


def _strip_name(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("This field is required.")
    return value


NewPassword = Annotated[str, AfterValidator(check_password_policy)]
Name = Annotated[str, Field(max_length=80), AfterValidator(_strip_name)]
Phone = Annotated[str | None, Field(max_length=30), AfterValidator(normalize_phone)]


class RegisterRequest(BaseModel):
    """Public registration. There is deliberately no `role` field: accounts are customers."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: NewPassword
    first_name: Name
    last_name: Name
    phone: Phone = None

    @model_validator(mode="after")
    def password_is_not_email(self) -> "RegisterRequest":
        if self.password.strip().lower() == str(self.email).lower():
            raise ValueError("Password must not be the same as your email.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=2048)


class ProfileUpdate(BaseModel):
    """Only these fields can be edited; anything else (role, email, ...) is rejected."""

    model_config = ConfigDict(extra="forbid")

    first_name: Name | None = None
    last_name: Name | None = None
    phone: Phone = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: NewPassword

    @model_validator(mode="after")
    def passwords_differ(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current one.")
        return self


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    phone: str | None
    avatar_path: str | None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Role
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile: ProfileResponse


class AuthResponse(BaseModel):
    """Returned by register, login and refresh. Web clients keep the tokens server-side."""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_token_expires_in: int = Field(description="Seconds until the access token expires.")
    refresh_token_expires_in: int = Field(description="Seconds until the refresh token expires.")
