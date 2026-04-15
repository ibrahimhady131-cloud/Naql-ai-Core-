"""Pydantic schemas for Identity Service API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    phone: str = Field(..., pattern=r"^\+20\d{10}$")  # Egyptian phone format
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(default="client_individual", pattern=r"^(client_individual|client_enterprise|driver)$")
    region_code: str = Field(..., pattern=r"^EG-[A-Z]{3}$")
    national_id: str | None = Field(None, pattern=r"^\d{14}$")


class UserLoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""

    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    region_code: str


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: str
    email: str
    phone: str
    full_name: str
    role: str
    kyc_status: str
    reputation_score: float
    region_code: str
    profile_image_url: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile."""

    full_name: str | None = None
    phone: str | None = Field(None, pattern=r"^\+20\d{10}$")
    profile_image_url: str | None = None


class KYCVerifyRequest(BaseModel):
    """Request schema for KYC verification."""

    kyc_status: str = Field(..., pattern=r"^(verified|rejected)$")
    verified_by: str


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
