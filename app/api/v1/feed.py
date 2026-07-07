from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE, Page
from app.schemas.post import PostOut
from app.services.feed_service import FeedService

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=Page[PostOut])
async def get_feed(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[PostOut]:
    return await FeedService(db).get_feed(user_id=current_user.id, page=page, size=size)
