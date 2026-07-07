from datetime import datetime

from sqlalchemy import delete, func, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.scalars(select(User).where(User.email == email))
        return result.first()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.scalars(select(User).where(User.username == username))
        return result.first()

    async def list_paginated(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        rows = await self.session.scalars(
            select(User).order_by(User.username).limit(limit).offset(offset)
        )
        total = await self.session.scalar(select(func.count()).select_from(User))
        return list(rows), total or 0

    async def delete_unverified_created_before(self, cutoff: datetime) -> int:
        result = await self.session.execute(
            delete(User).where(User.is_verified.is_(False), User.created_at < cutoff)
        )
        return result.rowcount or 0
