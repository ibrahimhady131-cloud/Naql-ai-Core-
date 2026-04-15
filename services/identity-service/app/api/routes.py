"""Identity Service API routes — fully DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from naql_common.auth import AuthManager, Permission, UserRole
from naql_common.db.deps import CockroachSession
from naql_common.db.models.identity import User

from ..core.config import settings
from ..core.deps import get_current_user, require_permission
from ..repositories import UserRepository
from ..schemas.user import (
    KYCVerifyRequest,
    TokenResponse,
    UserListResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/v1", tags=["identity"])
auth_manager = AuthManager(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        kyc_status=user.kyc_status,
        reputation_score=float(user.reputation_score),
        region_code=user.region_code,
        profile_image_url=user.profile_image_url,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, session: CockroachSession) -> TokenResponse:
    """Register a new user account."""
    repo = UserRepository(session)
    if await repo.get_by_email(request.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if await repo.get_by_phone(request.phone):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered")

    password_hash = _bcrypt.hashpw(request.password.encode(), _bcrypt.gensalt()).decode()
    user = await repo.create(
        email=request.email,
        phone=request.phone,
        password_hash=password_hash,
        full_name=request.full_name,
        role=request.role,
        region_code=request.region_code,
        national_id=request.national_id,
    )
    role = UserRole(request.role)
    access_token = auth_manager.create_access_token(
        user_id=str(user.id),
        role=role,
        region=request.region_code,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = auth_manager.create_refresh_token(
        user_id=str(user.id),
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return TokenResponse(
        user_id=str(user.id),
        access_token=access_token,
        refresh_token=refresh_token,
        role=request.role,
        region_code=request.region_code,
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, session: CockroachSession) -> TokenResponse:
    """Authenticate a user and return tokens."""
    repo = UserRepository(session)
    user = await repo.get_by_email(request.email)
    if user is None or not _bcrypt.checkpw(request.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    await repo.update(user, last_login_at=datetime.now(UTC))
    role = UserRole(user.role)
    access_token = auth_manager.create_access_token(
        user_id=str(user.id), role=role, region=user.region_code
    )
    refresh_token = auth_manager.create_refresh_token(user_id=str(user.id))
    return TokenResponse(
        user_id=str(user.id),
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        region_code=user.region_code,
    )


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[object, Depends(get_current_user)],
    session: CockroachSession,
) -> UserResponse:
    """Get the authenticated user's profile."""
    repo = UserRepository(session)
    user = await repo.get_by_id(current_user.sub)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_response(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    _current_user: Annotated[object, Depends(require_permission(Permission.USERS_READ))],
    session: CockroachSession,
) -> UserResponse:
    """Get a user by ID. Requires USERS_READ permission."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    session: CockroachSession,
) -> UserResponse:
    """Update user profile. Users can only edit their own profile unless they have USERS_WRITE."""
    is_own = current_user.sub == user_id
    has_perm = AuthManager.has_permission(UserRole(current_user.role), Permission.USERS_WRITE)
    if not is_own and not has_perm:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own profile")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    update_data = {k: v for k, v in request.model_dump(exclude_unset=True).items() if v is not None}
    user = await repo.update(user, **update_data)
    return _to_response(user)


@router.post("/users/{user_id}/kyc", response_model=UserResponse)
async def verify_kyc(
    user_id: str,
    request: KYCVerifyRequest,
    _current_user: Annotated[object, Depends(require_permission(Permission.USERS_WRITE))],
    session: CockroachSession,
) -> UserResponse:
    """Verify or reject a user's KYC status. Requires USERS_WRITE permission."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user = await repo.update(user, kyc_status=request.kyc_status)
    return _to_response(user)


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    region_code: str | None = None,
    session: CockroachSession = None,
) -> UserListResponse:
    """List users with pagination and filtering."""
    repo = UserRepository(session)
    offset = (page - 1) * page_size
    users = await repo.list_users(role=role, region_code=region_code, offset=offset, limit=page_size)

    count_stmt = select(func.count(User.id)).where(User.deleted_at.is_(None))
    if role:
        count_stmt = count_stmt.where(User.role == role)
    if region_code:
        count_stmt = count_stmt.where(User.region_code == region_code)
    total = (await session.execute(count_stmt)).scalar_one()

    return UserListResponse(
        users=[_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )
