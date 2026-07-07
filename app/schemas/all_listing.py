from uuid import UUID

from pydantic import BaseModel


class AllListingPostOut(BaseModel):
    id: UUID
    title: str
    content: str
    likes: list[UUID]


class AllListingUserOut(BaseModel):
    username: str
    posts: list[AllListingPostOut]
