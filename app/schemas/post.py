from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserPublicOut


class PostCreateIn(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=500)]


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    author: UserPublicOut
    created_at: datetime
    like_count: int = 0
    liked_by_me: bool = False
