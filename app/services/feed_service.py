from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.like import Like
from app.models.post import Post
from app.repositories.follow_repository import FollowRepository
from app.schemas.common import Page
from app.schemas.post import PostOut


class FeedService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.follows = FollowRepository(session)

    async def get_feed(self, *, user_id: UUID, page: int, size: int) -> Page[PostOut]:
        followee_ids = await self.follows.followee_ids_for(user_id)
        if not followee_ids:
            return Page(items=[], total=0, page=page, size=size)

        offset = (page - 1) * size

        liked_by_me_subq = (
            select(Like.id)
            .where(Like.post_id == Post.id, Like.user_id == user_id)
            .correlate(Post)
            .exists()
        )

        # 1 query: page of posts + like_count + liked_by_me, aggregated in the DB.
        # selectinload issues exactly 1 more query for authors, batched via IN(...).
        # Total: 2 queries regardless of page size - see Phase 15 of the design doc.
        stmt = (
            select(
                Post,
                func.count(Like.id).label("like_count"),
                liked_by_me_subq.label("liked_by_me"),
            )
            .outerjoin(Like, Like.post_id == Post.id)
            .where(Post.author_id.in_(followee_ids))
            .options(selectinload(Post.author))
            .group_by(Post.id)
            .order_by(Post.created_at.desc())
            .limit(size)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).all()

        total = await self.session.scalar(
            select(func.count()).select_from(Post).where(Post.author_id.in_(followee_ids))
        )

        items = []
        for post, like_count, liked_by_me in rows:
            post.like_count = like_count
            post.liked_by_me = bool(liked_by_me)
            items.append(PostOut.model_validate(post))

        return Page(items=items, total=total or 0, page=page, size=size)
