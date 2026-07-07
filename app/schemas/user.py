from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

RESERVED_USERNAMES = {"admin", "root", "api", "me"}


class UserRegisterIn(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=72)]

    @field_validator("username")
    @classmethod
    def username_not_reserved(cls, v: str) -> str:
        if v.lower() in RESERVED_USERNAMES:
            raise ValueError("username is reserved")
        return v.lower()

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()


class UserLoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    is_verified: bool


class UserPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
