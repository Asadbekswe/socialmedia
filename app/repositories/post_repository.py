from uuid import UUID

from sqlalchemy import func, literal, select
from sqlalchemy.orm import selectinload

from app.models.like import Like
from app.models.post import Post
from app.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    model = Post
    # Post.author is mapped with lazy="joined" (see app/models/post.py), so the
    # inherited get_by_id() already eager-loads the author in one query.

    async def list_paginated(
        self,
        *,
        author_id: UUID | None,
        q: str | None,
        viewer_id: UUID | None,
        limit: int,
        offset: int,
        newest_first: bool = True,
    ) -> tuple[list[tuple[Post, int, bool]], int]:
        filters = []
        if author_id is not None:
            filters.append(Post.author_id == author_id)
        if q:
            filters.append(Post.content.ilike(f"%{q}%"))

        liked_by_me_expr = (
            select(Like.id)
            .where(Like.post_id == Post.id, Like.user_id == viewer_id)
            .correlate(Post)
            .exists()
            if viewer_id is not None
            else literal(False)
        )

        order_col = Post.created_at.desc() if newest_first else Post.created_at.asc()

        stmt = (
            select(
                Post,
                func.count(Like.id).label("like_count"),
                liked_by_me_expr.label("liked_by_me"),
            )
            .outerjoin(Like, Like.post_id == Post.id)
            .where(*filters)
            .options(selectinload(Post.author))
            .group_by(Post.id)
            .order_by(order_col)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).all()

        total = await self.session.scalar(select(func.count()).select_from(Post).where(*filters))
        return [(post, count, bool(liked)) for post, count, liked in rows], total or 0
