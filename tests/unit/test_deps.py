from unittest.mock import MagicMock

import pytest

from app.api.deps import get_verified_user
from app.exceptions.base import ForbiddenException
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_get_verified_user_passes_through_verified_user():
    user = MagicMock(spec=User)
    user.is_verified = True

    result = await get_verified_user(user=user)

    assert result is user


async def test_get_verified_user_rejects_unverified_user():
    user = MagicMock(spec=User)
    user.is_verified = False

    with pytest.raises(ForbiddenException):
        await get_verified_user(user=user)
