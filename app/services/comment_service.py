from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ForbiddenException, NotFoundException
from app.models.comment import Comment
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.comments = CommentRepository(session)
        self.posts = PostRepository(session)

    async def create_comment(self, *, author: User, post_id: UUID, content: str) -> Comment:
        if await self.posts.get_by_id(post_id) is None:
            raise NotFoundException("Post not found")

        comment = await self.comments.create(post_id=post_id, author_id=author.id, content=content)
        await self.session.flush()
        comment.author = author
        return comment

    async def list_comments(self, post_id: UUID) -> list[Comment]:
        if await self.posts.get_by_id(post_id) is None:
            raise NotFoundException("Post not found")
        return await self.comments.list_for_post(post_id)

    async def delete_comment(self, *, user: User, post_id: UUID, comment_id: UUID) -> None:
        comment = await self.comments.get_by_id(comment_id)
        if comment is None or comment.post_id != post_id:
            raise NotFoundException("Comment not found")
        if comment.author_id != user.id:
            raise ForbiddenException("You can only delete your own comments")
        await self.comments.delete(comment)
