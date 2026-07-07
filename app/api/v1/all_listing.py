from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.all_listing import AllListingUserOut
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE, Page
from app.services.all_listing_service import AllListingService

router = APIRouter(tags=["all"])


@router.get("/all", response_model=Page[AllListingUserOut])
async def list_all(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> Page[AllListingUserOut]:
    return await AllListingService(db).list_all(page=page, size=size)
