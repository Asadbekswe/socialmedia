import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.like import Like
    from app.models.user import User


class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint("char_length(content) between 1 and 500", name="content_length"),
        Index("ix_posts_author_created", "author_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(String(500))
    expires_at: Mapped[datetime | None] = mapped_column(default=None)

    author: Mapped["User"] = relationship(back_populates="posts", lazy="joined")
    likes: Mapped[list["Like"]] = relationship(cascade="all, delete-orphan")
