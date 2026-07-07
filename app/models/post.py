import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.like import Like
    from app.models.user import User


class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint("char_length(title) between 5 and 255", name="title_length"),
        CheckConstraint("char_length(content) between 1 and 10000", name="content_length"),
        Index("ix_posts_author_created", "author_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)

    author: Mapped["User"] = relationship(back_populates="posts", lazy="joined")
    likes: Mapped[list["Like"]] = relationship(cascade="all, delete-orphan")
    comments: Mapped[list["Comment"]] = relationship(
        cascade="all, delete-orphan", order_by="Comment.created_at"
    )
