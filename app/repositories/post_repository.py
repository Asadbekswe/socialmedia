from datetime import datetime
from uuid import UUID

from sqlalchemy import func, literal, or_, select
from sqlalchemy.orm import selectinload

from app.models.like import Like
from app.models.post import Post
from app.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    model = Post
    # Post.author is mapped with lazy="joined" (see app/models/post.py), so the
    # inherited get_by_id() already eager-loads the author in one query.

    async def get_by_id_with_comments(self, id_: UUID) -> Post | None:
        result = await self.session.scalars(
            select(Post).options(selectinload(Post.comments)).where(Post.id == id_)
        )
        return result.first()

    async def list_by_author_ids_with_likes(self, author_ids: list[UUID]) -> list[Post]:
        if not author_ids:
            return []
        result = await self.session.scalars(
            select(Post)
            .where(Post.author_id.in_(author_ids))
            .options(selectinload(Post.likes))
            .order_by(Post.created_at)
        )
        return list(result)

    async def list_paginated(
        self,
        *,
        author_id: UUID | None,
        q: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        viewer_id: UUID | None,
        limit: int,
        offset: int,
        newest_first: bool = True,
    ) -> tuple[list[tuple[Post, int, bool]], int]:
        filters = []
        if author_id is not None:
            filters.append(Post.author_id == author_id)
        if q:
            filters.append(or_(Post.title.ilike(f"%{q}%"), Post.content.ilike(f"%{q}%")))
        if date_from is not None:
            filters.append(Post.created_at >= date_from)
        if date_to is not None:
            filters.append(Post.created_at <= date_to)

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
