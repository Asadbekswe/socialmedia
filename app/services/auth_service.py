from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.exceptions.base import ConflictException, UnauthorizedException
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.verification_service import VerificationService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.verification = VerificationService(session)

    async def register(self, *, username: str, email: str, full_name: str, password: str) -> User:
        if await self.users.get_by_email(email) is not None:
            raise ConflictException("Email already registered")
        if await self.users.get_by_username(username) is not None:
            raise ConflictException("Username already taken")

        user = await self.users.create(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
        )
        await self.session.flush()
        await self.verification.issue_and_send(user)
        return user

    async def authenticate(self, *, identifier: str, password: str) -> str:
        user = await self.users.get_by_email(identifier)
        if user is None:
            user = await self.users.get_by_username(identifier)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedException("Invalid email or password")
        return create_access_token(subject=user.id)
