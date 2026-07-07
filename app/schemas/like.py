from pydantic import BaseModel


class LikeOut(BaseModel):
    liked: bool
    like_count: int
