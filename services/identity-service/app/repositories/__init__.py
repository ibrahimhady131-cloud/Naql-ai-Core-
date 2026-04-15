"""Identity Service repository — database-backed user operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from naql_common.db.models.identity import User


class UserRepository:
    """CRUD operations for the users table via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch a user by their UUID."""
        result = await self._session.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address."""
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        """Fetch a user by phone number."""
        result = await self._session.execute(
            select(User).where(User.phone == phone)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        phone: str,
        password_hash: str,
        full_name: str,
        role: str,
        region_code: str,
        national_id: str | None = None,
    ) -> User:
        """Create a new user and return the ORM instance."""
        user = User(
            id=uuid.uuid4(),
            email=email,
            phone=phone,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            region_code=region_code,
            national_id=national_id,
            kyc_status="pending",
            reputation_score=5.00,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user: User, **kwargs: object) -> User:
        """Partial-update a user's fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.now(UTC)
        await self._session.flush()
        return user

    async def list_users(
        self,
        *,
        region_code: str | None = None,
        role: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[User]:
        """List users with optional filters."""
        stmt = select(User).where(User.deleted_at.is_(None))
        if region_code:
            stmt = stmt.where(User.region_code == region_code)
        if role:
            stmt = stmt.where(User.role == role)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, user: User) -> None:
        """Soft-delete a user by setting deleted_at."""
        user.deleted_at = datetime.now(UTC)
        user.is_active = False
        await self._session.flush()
