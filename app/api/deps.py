from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.session import get_db
from app.exceptions.base import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise UnauthorizedException("Invalid or expired token") from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedException("Invalid or expired token")
    return user


async def get_verified_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_verified:
        raise ForbiddenException("Email not verified")
    return user


async def get_optional_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """For public endpoints that personalize output (e.g. liked_by_me) when a
    valid token happens to be present, without requiring authentication."""
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
        user = await UserRepository(db).get_by_id(UUID(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    return user if (user and user.is_active) else None
