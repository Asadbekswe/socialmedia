import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _verified_token(
    client: AsyncClient, db_session: AsyncSession, username: str, email: str
) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "supersecret"},
    )
    await db_session.execute(update(User).where(User.email == email).values(is_verified=True))
    await db_session.commit()
    resp = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "supersecret"}
    )
    return resp.json()["access_token"]


async def test_double_like_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "mia", "mia@example.com")
    create_resp = await client.post(
        "/api/v1/posts", json={"content": "like me"}, headers={"Authorization": f"Bearer {token}"}
    )
    post_id = create_resp.json()["id"]
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post(f"/api/v1/posts/{post_id}/like", headers=headers)
    second = await client.post(f"/api/v1/posts/{post_id}/like", headers=headers)

    assert first.status_code == 200 and first.json() == {"liked": True, "like_count": 1}
    assert second.status_code == 200 and second.json() == {"liked": True, "like_count": 1}


async def test_unlike_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "noah", "noah@example.com")
    create_resp = await client.post(
        "/api/v1/posts", json={"content": "unlike me"}, headers={"Authorization": f"Bearer {token}"}
    )
    post_id = create_resp.json()["id"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(f"/api/v1/posts/{post_id}/like", headers=headers)
    first_unlike = await client.delete(f"/api/v1/posts/{post_id}/like", headers=headers)
    second_unlike = await client.delete(f"/api/v1/posts/{post_id}/like", headers=headers)

    assert first_unlike.json() == {"liked": False, "like_count": 0}
    assert second_unlike.json() == {"liked": False, "like_count": 0}


async def test_like_nonexistent_post_returns_404(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "olive", "olive@example.com")
    resp = await client.post(
        "/api/v1/posts/00000000-0000-0000-0000-000000000000/like",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
