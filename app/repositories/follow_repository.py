from uuid import UUID

from sqlalchemy import delete, func, select

from app.models.follow import Follow
from app.repositories.base import BaseRepository


class FollowRepository(BaseRepository[Follow]):
    model = Follow

    async def is_following(self, *, follower_id: UUID, followee_id: UUID) -> bool:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Follow)
            .where(Follow.follower_id == follower_id, Follow.followee_id == followee_id)
        )
        return bool(result)

    async def follow(self, *, follower_id: UUID, followee_id: UUID) -> None:
        await self.create(follower_id=follower_id, followee_id=followee_id)

    async def unfollow(self, *, follower_id: UUID, followee_id: UUID) -> None:
        await self.session.execute(
            delete(Follow).where(
                Follow.follower_id == follower_id, Follow.followee_id == followee_id
            )
        )

    async def followee_ids_for(self, follower_id: UUID) -> list[UUID]:
        result = await self.session.scalars(
            select(Follow.followee_id).where(Follow.follower_id == follower_id)
        )
        return list(result)
