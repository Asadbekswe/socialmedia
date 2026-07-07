from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_verified_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.comment import CommentCreateIn, CommentOut
from app.services.comment_service import CommentService

router = APIRouter(prefix="/posts/{post_id}/comments", tags=["comments"])


@router.get("", response_model=list[CommentOut])
async def list_comments(post_id: UUID, db: AsyncSession = Depends(get_db)) -> list[CommentOut]:
    comments = await CommentService(db).list_comments(post_id)
    return [CommentOut.model_validate(c) for c in comments]


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: UUID,
    payload: CommentCreateIn,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> CommentOut:
    comment = await CommentService(db).create_comment(
        author=current_user, post_id=post_id, content=payload.content
    )
    return CommentOut.model_validate(comment)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await CommentService(db).delete_comment(
        user=current_user, post_id=post_id, comment_id=comment_id
    )
