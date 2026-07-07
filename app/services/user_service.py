from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ConflictException
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def update_profile(
        self, *, user: User, username: str | None, full_name: str | None
    ) -> User:
        if username is not None and username != user.username:
            existing = await self.users.get_by_username(username)
            if existing is not None and existing.id != user.id:
                raise ConflictException("Username already taken")
            user.username = username

        if full_name is not None:
            user.full_name = full_name

        await self.session.flush()
        return user
