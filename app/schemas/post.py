from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.comment import CommentOut
from app.schemas.user import UserPublicOut


class PostCreateIn(BaseModel):
    title: Annotated[str, Field(min_length=5, max_length=255)]
    content: Annotated[str, Field(min_length=1, max_length=10000)]


class PostUpdateIn(BaseModel):
    title: Annotated[str, Field(min_length=5, max_length=255)] | None = None
    content: Annotated[str, Field(min_length=1, max_length=10000)] | None = None


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    author: UserPublicOut
    created_at: datetime
    like_count: int = 0
    liked_by_me: bool = False


class PostDetailOut(PostOut):
    comments: list[CommentOut] = []
