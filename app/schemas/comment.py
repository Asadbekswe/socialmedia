from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserPublicOut


class CommentCreateIn(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=2000)]


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    author: UserPublicOut
    created_at: datetime
