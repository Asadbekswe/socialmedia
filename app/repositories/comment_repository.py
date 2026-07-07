from uuid import UUID

from sqlalchemy import select

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment
    # Comment.author is mapped with lazy="joined" (see app/models/comment.py), so the
    # inherited get_by_id() already eager-loads the author in one query.

    async def list_for_post(self, post_id: UUID) -> list[Comment]:
        result = await self.session.scalars(
            select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at)
        )
        return list(result)
