from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_verified_user
from app.database.session import get_db
from app.exceptions.base import NotFoundException
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.follow import FollowOut
from app.schemas.user import UserOut, UserPublicOut
from app.services.follow_service import FollowService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get("/{username}", response_model=UserPublicOut)
async def get_user_by_username(username: str, db: AsyncSession = Depends(get_db)) -> UserPublicOut:
    user = await UserRepository(db).get_by_username(username.lower())
    if user is None:
        raise NotFoundException("User not found")
    return UserPublicOut.model_validate(user)


@router.post("/{username}/follow", response_model=FollowOut)
async def follow_user(
    username: str,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> FollowOut:
    following = await FollowService(db).follow(follower=current_user, target_username=username)
    return FollowOut(following=following)


@router.delete("/{username}/follow", response_model=FollowOut)
async def unfollow_user(
    username: str,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> FollowOut:
    following = await FollowService(db).unfollow(follower=current_user, target_username=username)
    return FollowOut(following=following)
