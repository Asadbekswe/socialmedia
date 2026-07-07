from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.all_listing import AllListingPostOut, AllListingUserOut
from app.schemas.common import Page


class AllListingService:
    """Backs GET /all: every user paired with their posts and each post's likers.

    Paginates over users (one page = N users), not posts - each user's full post
    list is nested underneath them, matching the shape the spec asks for.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.posts = PostRepository(session)

    async def list_all(self, *, page: int, size: int) -> Page[AllListingUserOut]:
        users, total = await self.users.list_paginated(limit=size, offset=(page - 1) * size)

        posts = await self.posts.list_by_author_ids_with_likes([u.id for u in users])
        posts_by_author: dict = {}
        for post in posts:
            posts_by_author.setdefault(post.author_id, []).append(post)

        items = [
            AllListingUserOut(
                username=user.username,
                posts=[
                    AllListingPostOut(
                        id=post.id,
                        title=post.title,
                        content=post.content,
                        likes=[like.user_id for like in post.likes],
                    )
                    for post in posts_by_author.get(user.id, [])
                ],
            )
            for user in users
        ]

        return Page(items=items, total=total, page=page, size=size)
