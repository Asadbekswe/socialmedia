from uuid import UUID

from sqlalchemy import delete, func, select

from app.models.like import Like
from app.repositories.base import BaseRepository


class LikeRepository(BaseRepository[Like]):
    model = Like

    async def count_for_post(self, post_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count()).select_from(Like).where(Like.post_id == post_id)
        )
        return result or 0

    async def exists(self, *, user_id: UUID, post_id: UUID) -> bool:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Like)
            .where(Like.user_id == user_id, Like.post_id == post_id)
        )
        return bool(result)

    async def remove(self, *, user_id: UUID, post_id: UUID) -> None:
        await self.session.execute(
            delete(Like).where(Like.user_id == user_id, Like.post_id == post_id)
        )
