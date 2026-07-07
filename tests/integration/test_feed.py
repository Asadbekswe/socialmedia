import pytest
from httpx import AsyncClient
from sqlalchemy import event, update
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


async def test_feed_only_shows_followed_users_posts(client: AsyncClient, db_session: AsyncSession):
    viewer_token = await _verified_token(client, db_session, "peter", "peter@example.com")
    followed_token = await _verified_token(client, db_session, "quinn", "quinn@example.com")
    stranger_token = await _verified_token(client, db_session, "ruth", "ruth@example.com")

    await client.post(
        "/api/v1/users/quinn/follow", headers={"Authorization": f"Bearer {viewer_token}"}
    )

    await client.post(
        "/api/v1/posts",
        json={"content": "from quinn, should appear"},
        headers={"Authorization": f"Bearer {followed_token}"},
    )
    await client.post(
        "/api/v1/posts",
        json={"content": "from ruth, should NOT appear"},
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    await client.post(
        "/api/v1/posts",
        json={"content": "from peter himself, should NOT appear"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    resp = await client.get("/api/v1/feed", headers={"Authorization": f"Bearer {viewer_token}"})
    assert resp.status_code == 200
    body = resp.json()
    contents = [item["content"] for item in body["items"]]
    assert contents == ["from quinn, should appear"]
    assert body["total"] == 1


async def test_feed_empty_when_following_nobody(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "sam", "sam@example.com")
    resp = await client.get("/api/v1/feed", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0, "page": 1, "size": 20, "has_next": False}


async def test_self_follow_rejected(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "tara", "tara@example.com")
    resp = await client.post(
        "/api/v1/users/tara/follow", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400


async def _feed_query_count(client: AsyncClient, db_session: AsyncSession, token: str) -> int:
    query_count = 0

    def _count(*args, **kwargs):
        nonlocal query_count
        query_count += 1

    engine = db_session.get_bind()  # AsyncSession.get_bind() returns the sync Engine
    event.listen(engine, "before_cursor_execute", _count)
    try:
        resp = await client.get("/api/v1/feed", headers={"Authorization": f"Bearer {token}"})
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert resp.status_code == 200
    return query_count, resp.json()


async def test_feed_query_count_is_constant_regardless_of_page_size(
    client: AsyncClient, db_session: AsyncSession
):
    viewer_token = await _verified_token(client, db_session, "uma", "uma@example.com")
    author_token = await _verified_token(client, db_session, "vic", "vic@example.com")
    await client.post(
        "/api/v1/users/vic/follow", headers={"Authorization": f"Bearer {viewer_token}"}
    )

    async def _add_posts(n: int) -> None:
        for i in range(n):
            await client.post(
                "/api/v1/posts",
                json={"content": f"post number {i}"},
                headers={"Authorization": f"Bearer {author_token}"},
            )

    await _add_posts(2)
    small_count, small_body = await _feed_query_count(client, db_session, viewer_token)
    assert len(small_body["items"]) == 2

    await _add_posts(18)  # 20 posts total now, still same page size (default 20)
    large_count, large_body = await _feed_query_count(client, db_session, viewer_token)
    assert len(large_body["items"]) == 20

    # Same number of SQL statements whether the page holds 2 posts or 20 -
    # proves the feed query is O(1) in query count, not O(n) (the N+1 problem
    # from Phase 15 of the design doc).
    assert small_count == large_count
