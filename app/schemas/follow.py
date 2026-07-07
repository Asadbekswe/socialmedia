from pydantic import BaseModel


class FollowOut(BaseModel):
    following: bool
