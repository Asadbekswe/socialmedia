from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ForbiddenException, NotFoundException
from app.models.post import Post
from app.models.user import User
from app.repositories.like_repository import LikeRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.post import PostOut


class PostService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.posts = PostRepository(session)
        self.likes = LikeRepository(session)
        self.users = UserRepository(session)

    async def create_post(self, *, author: User, title: str, content: str) -> Post:
        post = await self.posts.create(author_id=author.id, title=title, content=content)
        await self.session.flush()
        post.author = author
        post.like_count = 0
        post.liked_by_me = False
        return post

    async def get_post(self, post_id: UUID, *, viewer_id: UUID | None = None) -> Post:
        post = await self.posts.get_by_id(post_id)
        if post is None:
            raise NotFoundException("Post not found")

        post.like_count = await self.likes.count_for_post(post_id)
        post.liked_by_me = (
            await self.likes.exists(user_id=viewer_id, post_id=post_id)
            if viewer_id is not None
            else False
        )
        return post

    async def get_post_detail(self, post_id: UUID, *, viewer_id: UUID | None = None) -> Post:
        post = await self.posts.get_by_id_with_comments(post_id)
        if post is None:
            raise NotFoundException("Post not found")

        post.like_count = await self.likes.count_for_post(post_id)
        post.liked_by_me = (
            await self.likes.exists(user_id=viewer_id, post_id=post_id)
            if viewer_id is not None
            else False
        )
        return post

    async def update_post(
        self, *, user: User, post_id: UUID, title: str | None, content: str | None
    ) -> Post:
        post = await self.get_post(post_id)
        if post.author_id != user.id:
            raise ForbiddenException("You can only edit your own posts")

        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        await self.session.flush()
        return post

    async def delete_post(self, *, user: User, post_id: UUID) -> None:
        post = await self.get_post(post_id)
        if post.author_id != user.id:
            raise ForbiddenException("You can only delete your own posts")
        await self.posts.delete(post)

    async def list_posts(
        self,
        *,
        author_username: str | None,
        q: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        viewer_id: UUID | None,
        page: int,
        size: int,
        newest_first: bool = True,
    ) -> Page[PostOut]:
        author_id: UUID | None = None
        if author_username:
            author = await self.users.get_by_username(author_username.lower())
            if author is None:
                return Page(items=[], total=0, page=page, size=size)
            author_id = author.id

        rows, total = await self.posts.list_paginated(
            author_id=author_id,
            q=q,
            date_from=date_from,
            date_to=date_to,
            viewer_id=viewer_id,
            limit=size,
            offset=(page - 1) * size,
            newest_first=newest_first,
        )

        items = []
        for post, like_count, liked_by_me in rows:
            post.like_count = like_count
            post.liked_by_me = liked_by_me
            items.append(PostOut.model_validate(post))

        return Page(items=items, total=total, page=page, size=size)
