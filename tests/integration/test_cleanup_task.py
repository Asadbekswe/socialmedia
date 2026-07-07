from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.models.user import User
from app.models.verification_token import TokenPurpose, VerificationToken
from app.repositories.verification_token_repository import VerificationTokenRepository

pytestmark = pytest.mark.asyncio


async def _make_user(db_session: AsyncSession) -> User:
    user = User(username="zack", email="zack@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    return user


async def test_cleanup_deletes_only_tokens_past_the_retention_window(db_session: AsyncSession):
    user = await _make_user(db_session)
    now = datetime.now(UTC)

    # well past the 7-day retention grace period -> should be deleted
    old = VerificationToken(
        user_id=user.id,
        token_hash=hash_token("old"),
        purpose=TokenPurpose.EMAIL_VERIFICATION,
        expires_at=now - timedelta(days=10),
    )
    # expired, but still inside the 7-day grace window -> should survive
    recent = VerificationToken(
        user_id=user.id,
        token_hash=hash_token("recent"),
        purpose=TokenPurpose.EMAIL_VERIFICATION,
        expires_at=now - timedelta(days=1),
    )
    # not expired at all -> should survive
    valid = VerificationToken(
        user_id=user.id,
        token_hash=hash_token("valid"),
        purpose=TokenPurpose.EMAIL_VERIFICATION,
        expires_at=now + timedelta(hours=1),
    )
    db_session.add_all([old, recent, valid])
    await db_session.commit()

    cutoff = now - timedelta(days=7)
    deleted = await VerificationTokenRepository(db_session).delete_expired_before(cutoff)
    await db_session.commit()

    assert deleted == 1
    remaining = await VerificationTokenRepository(db_session).get_by_hash(hash_token("recent"))
    assert remaining is not None
    still_valid = await VerificationTokenRepository(db_session).get_by_hash(hash_token("valid"))
    assert still_valid is not None
    purged = await VerificationTokenRepository(db_session).get_by_hash(hash_token("old"))
    assert purged is None
