from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import MessageOut, TokenOut
from app.schemas.user import UserOut, UserRegisterIn
from app.services.auth_service import AuthService
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterIn, db: AsyncSession = Depends(get_db)) -> UserOut:
    service = AuthService(db)
    user = await service.register(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenOut)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
    service = AuthService(db)
    access_token = await service.authenticate(email=form_data.username, password=form_data.password)
    return TokenOut(access_token=access_token)


@router.get("/verify-email", response_model=MessageOut)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)) -> MessageOut:
    await VerificationService(db).verify(token)
    return MessageOut(message="verified")


@router.post(
    "/resend-verification",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    await VerificationService(db).resend(current_user)
    return MessageOut(message="sent")
