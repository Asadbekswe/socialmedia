from datetime import datetime
from enum import StrEnum
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user, get_verified_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE, Page
from app.schemas.like import LikeOut
from app.schemas.post import PostCreateIn, PostDetailOut, PostOut, PostUpdateIn
from app.services.like_service import LikeService
from app.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=["posts"])


class SortOrder(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreateIn,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PostOut:
    post = await PostService(db).create_post(
        author=current_user, title=payload.title, content=payload.content
    )
    return PostOut.model_validate(post)


@router.get("", response_model=Page[PostOut])
async def list_posts(
    author: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: SortOrder = SortOrder.NEWEST,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    viewer: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> Page[PostOut]:
    return await PostService(db).list_posts(
        author_username=author,
        q=q,
        date_from=date_from,
        date_to=date_to,
        viewer_id=viewer.id if viewer else None,
        page=page,
        size=size,
        newest_first=(sort == SortOrder.NEWEST),
    )


@router.get("/{post_id}", response_model=PostDetailOut)
async def get_post(
    post_id: UUID,
    viewer: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    post = await PostService(db).get_post_detail(post_id, viewer_id=viewer.id if viewer else None)
    return PostDetailOut.model_validate(post)


@router.patch("/{post_id}", response_model=PostOut)
async def update_post(
    post_id: UUID,
    payload: PostUpdateIn,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PostOut:
    post = await PostService(db).update_post(
        user=current_user, post_id=post_id, title=payload.title, content=payload.content
    )
    return PostOut.model_validate(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await PostService(db).delete_post(user=current_user, post_id=post_id)


@router.post("/{post_id}/like", response_model=LikeOut)
async def like_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LikeOut:
    result = await LikeService(db).like_post(user_id=current_user.id, post_id=post_id)
    return LikeOut(liked=result.liked, like_count=result.like_count)


@router.delete("/{post_id}/like", response_model=LikeOut)
async def unlike_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LikeOut:
    result = await LikeService(db).unlike_post(user_id=current_user.id, post_id=post_id)
    return LikeOut(liked=result.liked, like_count=result.like_count)
