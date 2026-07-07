from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import NotFoundException
from app.repositories.like_repository import LikeRepository
from app.repositories.post_repository import PostRepository


@dataclass
class LikeResult:
    liked: bool
    like_count: int


class LikeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.likes = LikeRepository(session)
        self.posts = PostRepository(session)

    async def like_post(self, *, user_id: UUID, post_id: UUID) -> LikeResult:
        if await self.posts.get_by_id(post_id) is None:
            raise NotFoundException("Post not found")

        try:
            async with self.session.begin_nested():
                await self.likes.create(user_id=user_id, post_id=post_id)
        except IntegrityError:
            pass  # already liked - idempotent no-op, not an error

        count = await self.likes.count_for_post(post_id)
        return LikeResult(liked=True, like_count=count)

    async def unlike_post(self, *, user_id: UUID, post_id: UUID) -> LikeResult:
        if await self.posts.get_by_id(post_id) is None:
            raise NotFoundException("Post not found")

        await self.likes.remove(user_id=user_id, post_id=post_id)
        count = await self.likes.count_for_post(post_id)
        return LikeResult(liked=False, like_count=count)
