from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: str
    username: str
    full_name: str | None = None
    email: str | None = None
    role: str
    permissions: list[str]


class LoginResponse(BaseModel):
    tokens: TokenPair
    user: UserProfile
