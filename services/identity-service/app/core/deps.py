"""FastAPI dependencies for Identity Service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from naql_common.auth import AuthManager, Permission, TokenPayload, UserRole

from .config import settings

security = HTTPBearer()
auth_manager = AuthManager(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenPayload:
    """Extract and validate JWT token from Authorization header."""
    try:
        return auth_manager.verify_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def require_permission(permission: Permission):
    """Create a dependency that checks for a specific permission."""

    async def checker(
        user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        if not AuthManager.has_permission(UserRole(user.role), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return user

    return checker
