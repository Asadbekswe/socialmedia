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


async def _create_post(client: AsyncClient, token: str, title: str = "a post") -> str:
    resp = await client.post(
        "/api/v1/posts",
        json={"title": title, "content": "content"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


async def test_verified_user_can_comment_on_a_post(client: AsyncClient, db_session: AsyncSession):
    author_token = await _verified_token(client, db_session, "aaron", "aaron@example.com")
    commenter_token = await _verified_token(client, db_session, "beth", "beth@example.com")
    post_id = await _create_post(client, author_token)

    resp = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "great post!"},
        headers={"Authorization": f"Bearer {commenter_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["content"] == "great post!"
    assert body["author"]["username"] == "beth"


async def test_unverified_user_cannot_comment(client: AsyncClient, db_session: AsyncSession):
    author_token = await _verified_token(client, db_session, "carl", "carl@example.com")
    unverified_token = await _unverified_token(client, "dana", "dana@example.com")
    post_id = await _create_post(client, author_token)

    resp = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "should not work"},
        headers={"Authorization": f"Bearer {unverified_token}"},
    )
    assert resp.status_code == 403


async def test_list_comments_for_a_post(client: AsyncClient, db_session: AsyncSession):
    author_token = await _verified_token(client, db_session, "erin", "erin@example.com")
    post_id = await _create_post(client, author_token)
    await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "first"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "second"},
        headers={"Authorization": f"Bearer {author_token}"},
    )

    resp = await client.get(f"/api/v1/posts/{post_id}/comments")
    assert resp.status_code == 200
    contents = [c["content"] for c in resp.json()]
    assert contents == ["first", "second"]


async def test_author_can_delete_own_comment(client: AsyncClient, db_session: AsyncSession):
    author_token = await _verified_token(client, db_session, "finn", "finn@example.com")
    post_id = await _create_post(client, author_token)
    create_resp = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "delete me"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    comment_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/posts/{post_id}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert resp.status_code == 204


async def test_non_author_cannot_delete_comment(client: AsyncClient, db_session: AsyncSession):
    post_author_token = await _verified_token(client, db_session, "gina", "gina@example.com")
    comment_author_token = await _verified_token(client, db_session, "hugo", "hugo@example.com")
    post_id = await _create_post(client, post_author_token)
    create_resp = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "not yours"},
        headers={"Authorization": f"Bearer {comment_author_token}"},
    )
    comment_id = create_resp.json()["id"]

    # the post's own author is NOT the comment's author - only the comment's
    # author may delete it, ownership is per-comment, not inherited from the post
    resp = await client.delete(
        f"/api/v1/posts/{post_id}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {post_author_token}"},
    )
    assert resp.status_code == 403


async def test_oversized_comment_rejected(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "iggy", "iggy@example.com")
    post_id = await _create_post(client, token)

    resp = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "x" * 2001},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_comment_on_nonexistent_post_returns_404(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _verified_token(client, db_session, "jade", "jade@example.com")
    resp = await client.post(
        "/api/v1/posts/00000000-0000-0000-0000-000000000000/comments",
        json={"content": "on a ghost post"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
