"""SQLAlchemy base models and mixins for Naql.ai."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft-delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class RegionalMixin:
    """Mixin for regional sharding — every entity is bound to a Cell (region)."""

    region_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Regional cell code: e.g. EG-CAI, EG-ALX, EG-SUE",
    )


def generate_uuid() -> str:
    """Generate a UUID7 (time-sortable) as string."""
    return str(uuid.uuid4())
