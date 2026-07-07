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
            "full_name": "Test User",
            "password": "supersecret",
        },
    )
    await db_session.execute(update(User).where(User.email == email).values(is_verified=True))
    await db_session.commit()
    resp = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "supersecret"}
    )
    return resp.json()["access_token"]


async def test_update_own_full_name(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "kara", "kara@example.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"full_name": "Kara Updated Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Kara Updated Name"


async def test_update_username_to_one_already_taken_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    await _verified_token(client, db_session, "leo", "leo@example.com")
    token = await _verified_token(client, db_session, "mira", "mira@example.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"username": "leo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


async def test_update_full_name_rejects_invalid_characters(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _verified_token(client, db_session, "nina", "nina@example.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"full_name": "Nina123!!!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_all_listing_shape_and_pagination(client: AsyncClient, db_session: AsyncSession):
    alice_token = await _verified_token(client, db_session, "opal2", "opal2@example.com")
    bob_token = await _verified_token(client, db_session, "quill2", "quill2@example.com")

    post_resp = await client.post(
        "/api/v1/posts",
        json={"title": "hello there", "content": "content"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    post_id = post_resp.json()["id"]
    await client.post(
        f"/api/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {bob_token}"}
    )

    resp = await client.get("/api/v1/all?size=100")
    assert resp.status_code == 200
    body = resp.json()

    by_username = {u["username"]: u for u in body["items"]}
    assert "opal2" in by_username
    assert "quill2" in by_username

    alice_posts = by_username["opal2"]["posts"]
    assert len(alice_posts) == 1
    assert alice_posts[0]["title"] == "hello there"
    assert len(alice_posts[0]["likes"]) == 1  # bob's user id

    assert by_username["quill2"]["posts"] == []
