from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["participant", "admin"]
VerificationStatus = Literal["not_submitted", "pending", "approved", "rejected"]


class UserPublic(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    phone: str | None = None
    verification_status: VerificationStatus
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


class IdentitySubmissionCreate(BaseModel):
    nik: str = Field(min_length=16, max_length=16)
    address: str = Field(min_length=10, max_length=500)
    ktp_image_data: str = Field(min_length=20, max_length=6_000_000)


class IdentitySubmission(BaseModel):
    id: str
    user_id: str
    full_name: str
    email: str
    nik: str
    address: str
    ktp_image_data: str
    status: VerificationStatus
    submitted_at: str
    reviewed_at: str | None = None
    review_note: str | None = None


class IdentityReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=500)
