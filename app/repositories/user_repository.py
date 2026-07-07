from sqlalchemy import select

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
