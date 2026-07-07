from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import BadRequestException, NotFoundException
from app.models.user import User
from app.repositories.follow_repository import FollowRepository
from app.repositories.user_repository import UserRepository


class FollowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.follows = FollowRepository(session)
        self.users = UserRepository(session)

    async def _resolve_target(self, username: str) -> User:
        target = await self.users.get_by_username(username.lower())
        if target is None:
            raise NotFoundException("User not found")
        return target

    async def follow(self, *, follower: User, target_username: str) -> bool:
        target = await self._resolve_target(target_username)
        if target.id == follower.id:
            raise BadRequestException("You cannot follow yourself")

        try:
            async with self.session.begin_nested():
                await self.follows.follow(follower_id=follower.id, followee_id=target.id)
        except IntegrityError:
            pass  # already following - idempotent no-op
        return True

    async def unfollow(self, *, follower: User, target_username: str) -> bool:
        target = await self._resolve_target(target_username)
        await self.follows.unfollow(follower_id=follower.id, followee_id=target.id)
        return False
