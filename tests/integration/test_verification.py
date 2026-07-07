from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.models.verification_token import TokenPurpose, VerificationToken
from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.asyncio


async def _register_and_get_raw_token(client: AsyncClient, db_session: AsyncSession) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"username": "eve", "email": "eve@example.com", "password": "supersecret"},
    )
    user = await UserRepository(db_session).get_by_email("eve@example.com")

    raw_token = "test-raw-token-value"
    db_session.add(
        VerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose=TokenPurpose.EMAIL_VERIFICATION,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    await db_session.commit()
    return raw_token


async def test_verify_with_valid_token_marks_user_verified(
    client: AsyncClient, db_session: AsyncSession
):
    raw_token = await _register_and_get_raw_token(client, db_session)

    resp = await client.get(f"/api/v1/auth/verify-email?token={raw_token}")
    assert resp.status_code == 200

    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "eve@example.com", "password": "supersecret"}
    )
    token = login_resp.json()["access_token"]
    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_verified"] is True


async def test_verify_with_expired_token_rejected(client: AsyncClient, db_session: AsyncSession):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "frank", "email": "frank@example.com", "password": "supersecret"},
    )
    user = await UserRepository(db_session).get_by_email("frank@example.com")
    raw_token = "expired-token-value"
    db_session.add(
        VerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose=TokenPurpose.EMAIL_VERIFICATION,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/auth/verify-email?token={raw_token}")
    assert resp.status_code == 400


async def test_verify_with_reused_token_rejected(client: AsyncClient, db_session: AsyncSession):
    raw_token = await _register_and_get_raw_token(client, db_session)

    first = await client.get(f"/api/v1/auth/verify-email?token={raw_token}")
    assert first.status_code == 200

    second = await client.get(f"/api/v1/auth/verify-email?token={raw_token}")
    assert second.status_code == 400


async def test_verify_with_garbage_token_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/auth/verify-email?token=not-a-real-token")
    assert resp.status_code == 400


async def test_resend_on_already_verified_user_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    raw_token = await _register_and_get_raw_token(client, db_session)
    await client.get(f"/api/v1/auth/verify-email?token={raw_token}")

    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "eve@example.com", "password": "supersecret"}
    )
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/resend-verification", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 409
