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
        json={
            "username": username,
            "email": email,
            "full_name": f"{username.title()} Example",
            "password": "supersecret",
        },
    )
    await db_session.execute(update(User).where(User.email == email).values(is_verified=True))
    await db_session.commit()
    resp = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "supersecret"}
    )
    return resp.json()["access_token"]


async def _unverified_token(client: AsyncClient, username: str, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": f"{username.title()} Example",
            "password": "supersecret",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "supersecret"}
    )
    return resp.json()["access_token"]


async def test_double_like_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    author_token = await _verified_token(client, db_session, "mia", "mia@example.com")
    liker_token = await _verified_token(client, db_session, "milo", "milo@example.com")
    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "like me please", "content": "like me"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    post_id = create_resp.json()["id"]
    headers = {"Authorization": f"Bearer {liker_token}"}

    first = await client.post(f"/api/v1/posts/{post_id}/like", headers=headers)
    second = await client.post(f"/api/v1/posts/{post_id}/like", headers=headers)

    assert first.status_code == 200 and first.json() == {"liked": True, "like_count": 1}
    assert second.status_code == 200 and second.json() == {"liked": True, "like_count": 1}


async def test_unlike_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    author_token = await _verified_token(client, db_session, "noah", "noah@example.com")
    liker_token = await _verified_token(client, db_session, "nora", "nora@example.com")
    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "unlike me please", "content": "unlike me"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    post_id = create_resp.json()["id"]
    headers = {"Authorization": f"Bearer {liker_token}"}

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


async def test_cannot_like_own_post(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "quill", "quill@example.com")
    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "my own post", "content": "content"},
        headers={"Authorization": f"Bearer {token}"},
    )
    post_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400


async def test_unverified_user_can_like_a_post(client: AsyncClient, db_session: AsyncSession):
    author_token = await _verified_token(client, db_session, "rex", "rex@example.com")
    unverified_token = await _unverified_token(client, "sara", "sara@example.com")
    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "likeable by anyone", "content": "content"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    post_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {unverified_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"liked": True, "like_count": 1}
