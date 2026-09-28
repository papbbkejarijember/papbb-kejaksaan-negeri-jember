from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["participant", "admin"]


class UserPublic(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    phone: str | None = None
    created_at: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=128)


class SessionResponse(BaseModel):
    user: UserPublic
