from datetime import datetime

from sqlalchemy import delete, select

from app.models.verification_token import TokenPurpose, VerificationToken
from app.repositories.base import BaseRepository


class VerificationTokenRepository(BaseRepository[VerificationToken]):
    model = VerificationToken

    async def get_valid_by_hash(
        self, token_hash: str, *, purpose: TokenPurpose, now: datetime
    ) -> VerificationToken | None:
        result = await self.session.scalars(
            select(VerificationToken).where(
                VerificationToken.token_hash == token_hash,
                VerificationToken.purpose == purpose,
                VerificationToken.used_at.is_(None),
                VerificationToken.expires_at > now,
            )
        )
        return result.first()

    async def get_by_hash(self, token_hash: str) -> VerificationToken | None:
        result = await self.session.scalars(
            select(VerificationToken).where(VerificationToken.token_hash == token_hash)
        )
        return result.first()

    async def delete_expired_before(self, cutoff: datetime) -> int:
        result = await self.session.execute(
            delete(VerificationToken).where(VerificationToken.expires_at < cutoff)
        )
        return result.rowcount or 0
