from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

RESERVED_USERNAMES = {"admin", "root", "api", "me"}
FULL_NAME_PATTERN = r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\s\-]*[A-Za-zА-Яа-яЁё]$|^[A-Za-zА-Яа-яЁё]$"


class UserRegisterIn(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")]
    email: EmailStr
    full_name: Annotated[str, Field(min_length=2, max_length=100, pattern=FULL_NAME_PATTERN)]
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


class UserUpdateIn(BaseModel):
    username: (
        Annotated[str, Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")] | None
    ) = None
    full_name: (
        Annotated[str, Field(min_length=2, max_length=100, pattern=FULL_NAME_PATTERN)] | None
    ) = None

    @field_validator("username")
    @classmethod
    def username_not_reserved(cls, v: str | None) -> str | None:
        if v is not None and v.lower() in RESERVED_USERNAMES:
            raise ValueError("username is reserved")
        return v.lower() if v is not None else v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    full_name: str
    is_verified: bool


class UserPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str
