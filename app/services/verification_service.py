from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_raw_token, hash_token
from app.exceptions.base import BadRequestException, ConflictException, NotFoundException
from app.models.user import User
from app.models.verification_token import TokenPurpose
from app.repositories.user_repository import UserRepository
from app.repositories.verification_token_repository import VerificationTokenRepository
from app.tasks.email_tasks import send_verification_email

TOKEN_TTL = timedelta(hours=24)


class VerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = VerificationTokenRepository(session)

    async def issue_and_send(self, user: User) -> None:
        raw_token = generate_raw_token()
        await self.tokens.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose=TokenPurpose.EMAIL_VERIFICATION,
            expires_at=datetime.now(UTC) + TOKEN_TTL,
        )
        send_verification_email.delay(email=user.email, username=user.username, raw_token=raw_token)

    async def resend(self, user: User) -> None:
        if user.is_verified:
            raise ConflictException("Email already verified")
        await self.issue_and_send(user)

    async def verify(self, raw_token: str) -> User:
        token_hash = hash_token(raw_token)
        now = datetime.now(UTC)

        token = await self.tokens.get_valid_by_hash(
            token_hash, purpose=TokenPurpose.EMAIL_VERIFICATION, now=now
        )
        if token is None:
            existing = await self.tokens.get_by_hash(token_hash)
            if existing is not None and existing.used_at is not None:
                raise BadRequestException("Token already used")
            raise BadRequestException("Invalid or expired token")

        user = await self.users.get_by_id(token.user_id)
        if user is None:
            raise NotFoundException("User not found")

        user.is_verified = True
        token.used_at = now
        await self.session.flush()
        return user
