from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.base import NotFoundException
from app.services.like_service import LikeService


class _NestedTransactionCM:
    """Stands in for `session.begin_nested()` without touching a real DB."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False  # don't swallow - let LikeService's own try/except handle it


def _make_service(*, post_exists: bool = True, like_raises: Exception | None = None) -> LikeService:
    service = LikeService.__new__(LikeService)
    service.session = MagicMock()
    service.session.begin_nested = MagicMock(return_value=_NestedTransactionCM())
    service.posts = MagicMock()
    service.posts.get_by_id = AsyncMock(return_value=MagicMock() if post_exists else None)
    service.likes = MagicMock()
    service.likes.create = AsyncMock(side_effect=like_raises)
    service.likes.count_for_post = AsyncMock(return_value=1)
    service.likes.remove = AsyncMock()
    return service


pytestmark = pytest.mark.asyncio


async def test_like_post_raises_not_found_when_post_missing():
    service = _make_service(post_exists=False)

    with pytest.raises(NotFoundException):
        await service.like_post(user_id=uuid4(), post_id=uuid4())


async def test_like_post_succeeds_on_first_like():
    service = _make_service()

    result = await service.like_post(user_id=uuid4(), post_id=uuid4())

    assert result.liked is True
    assert result.like_count == 1
    service.likes.create.assert_awaited_once()


async def test_like_post_swallows_duplicate_integrity_error_and_stays_idempotent():
    duplicate_error = IntegrityError("INSERT", {}, Exception("duplicate key"))
    service = _make_service(like_raises=duplicate_error)

    result = await service.like_post(user_id=uuid4(), post_id=uuid4())

    # the race-condition defense: a concurrent duplicate insert is swallowed,
    # not surfaced as a 500 - the caller just gets the current, correct state back.
    assert result.liked is True
    assert result.like_count == 1
