"""JWT-based authentication and RBAC utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt
from pydantic import BaseModel


class UserRole(StrEnum):
    """Role-Based Access Control roles."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATIONS_MANAGER = "operations_manager"
    DISPATCHER = "dispatcher"
    DRIVER = "driver"
    CLIENT_ENTERPRISE = "client_enterprise"
    CLIENT_INDIVIDUAL = "client_individual"
    FINANCE_OFFICER = "finance_officer"
    SUPPORT_AGENT = "support_agent"


class Permission(StrEnum):
    """Granular permissions for RBAC."""

    # User management
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"

    # Fleet management
    FLEET_READ = "fleet:read"
    FLEET_WRITE = "fleet:write"
    FLEET_ASSIGN = "fleet:assign"

    # Shipment management
    SHIPMENTS_CREATE = "shipments:create"
    SHIPMENTS_READ = "shipments:read"
    SHIPMENTS_UPDATE = "shipments:update"
    SHIPMENTS_CANCEL = "shipments:cancel"

    # Financial operations
    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"
    FINANCE_ESCROW = "finance:escrow"

    # Agent operations
    AGENT_INTERACT = "agent:interact"
    AGENT_CONFIGURE = "agent:configure"

    # Telemetry
    TELEMETRY_READ = "telemetry:read"
    TELEMETRY_WRITE = "telemetry:write"


# Role → Permissions mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.SUPER_ADMIN: set(Permission),
    UserRole.ADMIN: {
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.FLEET_READ,
        Permission.FLEET_WRITE,
        Permission.FLEET_ASSIGN,
        Permission.SHIPMENTS_CREATE,
        Permission.SHIPMENTS_READ,
        Permission.SHIPMENTS_UPDATE,
        Permission.SHIPMENTS_CANCEL,
        Permission.FINANCE_READ,
        Permission.AGENT_INTERACT,
        Permission.AGENT_CONFIGURE,
        Permission.TELEMETRY_READ,
    },
    UserRole.OPERATIONS_MANAGER: {
        Permission.FLEET_READ,
        Permission.FLEET_WRITE,
        Permission.FLEET_ASSIGN,
        Permission.SHIPMENTS_CREATE,
        Permission.SHIPMENTS_READ,
        Permission.SHIPMENTS_UPDATE,
        Permission.TELEMETRY_READ,
        Permission.AGENT_INTERACT,
    },
    UserRole.DISPATCHER: {
        Permission.FLEET_READ,
        Permission.FLEET_ASSIGN,
        Permission.SHIPMENTS_READ,
        Permission.SHIPMENTS_UPDATE,
        Permission.TELEMETRY_READ,
        Permission.AGENT_INTERACT,
    },
    UserRole.DRIVER: {
        Permission.FLEET_READ,
        Permission.SHIPMENTS_READ,
        Permission.TELEMETRY_WRITE,
        Permission.AGENT_INTERACT,
    },
    UserRole.CLIENT_ENTERPRISE: {
        Permission.SHIPMENTS_CREATE,
        Permission.SHIPMENTS_READ,
        Permission.SHIPMENTS_CANCEL,
        Permission.FINANCE_READ,
        Permission.AGENT_INTERACT,
    },
    UserRole.CLIENT_INDIVIDUAL: {
        Permission.SHIPMENTS_CREATE,
        Permission.SHIPMENTS_READ,
        Permission.SHIPMENTS_CANCEL,
        Permission.FINANCE_READ,
        Permission.AGENT_INTERACT,
    },
    UserRole.FINANCE_OFFICER: {
        Permission.FINANCE_READ,
        Permission.FINANCE_WRITE,
        Permission.FINANCE_ESCROW,
        Permission.SHIPMENTS_READ,
    },
    UserRole.SUPPORT_AGENT: {
        Permission.USERS_READ,
        Permission.SHIPMENTS_READ,
        Permission.FLEET_READ,
        Permission.FINANCE_READ,
        Permission.AGENT_INTERACT,
    },
}


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # user_id
    role: UserRole
    region: str
    permissions: list[str]
    exp: datetime
    iat: datetime


class AuthManager:
    """Handles JWT token creation, validation, and RBAC checks."""

    def __init__(self, secret_key: str, algorithm: str = "HS256") -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm

    def create_access_token(
        self,
        user_id: str,
        role: UserRole,
        region: str,
        *,
        expires_delta: timedelta = timedelta(hours=1),
    ) -> str:
        """Create a JWT access token."""
        now = datetime.now(UTC)
        permissions = [p.value for p in ROLE_PERMISSIONS.get(role, set())]

        payload: dict[str, Any] = {
            "sub": user_id,
            "role": role.value,
            "region": region,
            "permissions": permissions,
            "iat": now,
            "exp": now + expires_delta,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        *,
        expires_delta: timedelta = timedelta(days=30),
    ) -> str:
        """Create a JWT refresh token."""
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + expires_delta,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a JWT token."""
        decoded = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        return TokenPayload(**decoded)

    @staticmethod
    def has_permission(role: UserRole, permission: Permission) -> bool:
        """Check if a role has a specific permission."""
        return permission in ROLE_PERMISSIONS.get(role, set())
