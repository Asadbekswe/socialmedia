import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _register_and_verify(
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

    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "supersecret"}
    )
    return login_resp.json()["access_token"]


async def test_verified_user_can_create_post(client: AsyncClient, db_session: AsyncSession):
    token = await _register_and_verify(client, db_session, "grace", "grace@example.com")

    resp = await client.post(
        "/api/v1/posts",
        json={"title": "hello world", "content": "i love rust"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "hello world"
    assert body["content"] == "i love rust"
    assert body["author"]["username"] == "grace"
    assert body["like_count"] == 0
    assert body["liked_by_me"] is False


async def test_unverified_user_cannot_create_post(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "henry",
            "email": "henry@example.com",
            "full_name": "Henry Example",
            "password": "supersecret",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login", data={"username": "henry@example.com", "password": "supersecret"}
    )
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/posts",
        json={"title": "should not work", "content": "should not work"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_oversized_content_rejected(client: AsyncClient, db_session: AsyncSession):
    token = await _register_and_verify(client, db_session, "iris", "iris@example.com")

    resp = await client.post(
        "/api/v1/posts",
        json={"title": "valid title", "content": "x" * 10001},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_undersized_title_rejected(client: AsyncClient, db_session: AsyncSession):
    token = await _register_and_verify(client, db_session, "ivan", "ivan@example.com")

    resp = await client.post(
        "/api/v1/posts",
        json={"title": "hi", "content": "title is too short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_owner_can_delete_own_post(client: AsyncClient, db_session: AsyncSession):
    token = await _register_and_verify(client, db_session, "jack", "jack@example.com")
    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "delete me please", "content": "delete me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    post_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/posts/{post_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/posts/{post_id}")
    assert get_resp.status_code == 404


async def test_non_owner_cannot_delete_post(client: AsyncClient, db_session: AsyncSession):
    owner_token = await _register_and_verify(client, db_session, "kate", "kate@example.com")
    other_token = await _register_and_verify(client, db_session, "liam", "liam@example.com")

    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "not yours to delete", "content": "not yours"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    post_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/posts/{post_id}", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert resp.status_code == 403


async def test_owner_can_update_own_post(client: AsyncClient, db_session: AsyncSession):
    token = await _register_and_verify(client, db_session, "mona", "mona@example.com")
    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "original title", "content": "original content"},
        headers={"Authorization": f"Bearer {token}"},
    )
    post_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/posts/{post_id}",
        json={"title": "updated title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "updated title"
    assert body["content"] == "original content"  # untouched field stays as-is


async def test_non_owner_cannot_update_post(client: AsyncClient, db_session: AsyncSession):
    owner_token = await _register_and_verify(client, db_session, "nate", "nate@example.com")
    other_token = await _register_and_verify(client, db_session, "opal", "opal@example.com")

    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "not yours to edit", "content": "original"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    post_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/posts/{post_id}",
        json={"title": "hijacked"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 403


async def test_post_detail_includes_comments(client: AsyncClient, db_session: AsyncSession):
    token = await _register_and_verify(client, db_session, "pearl", "pearl@example.com")
    create_resp = await client.post(
        "/api/v1/posts",
        json={"title": "a post with comments", "content": "content"},
        headers={"Authorization": f"Bearer {token}"},
    )
    post_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "first comment"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(f"/api/v1/posts/{post_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["comments"]) == 1
    assert body["comments"][0]["content"] == "first comment"
