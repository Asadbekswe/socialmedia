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


async def test_pagination_returns_correct_page_and_total(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _verified_token(client, db_session, "will", "will@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(7):
        await client.post("/api/v1/posts", json={"content": f"post {i}"}, headers=headers)

    page1 = await client.get("/api/v1/posts?size=3&page=1")
    page2 = await client.get("/api/v1/posts?size=3&page=2")
    page3 = await client.get("/api/v1/posts?size=3&page=3")

    assert page1.json()["total"] == 7
    assert len(page1.json()["items"]) == 3
    assert len(page2.json()["items"]) == 3
    assert len(page3.json()["items"]) == 1
    assert page1.json()["has_next"] is True
    assert page3.json()["has_next"] is False

    ids_page1 = {item["id"] for item in page1.json()["items"]}
    ids_page2 = {item["id"] for item in page2.json()["items"]}
    assert ids_page1.isdisjoint(ids_page2)


async def test_search_matches_expected_posts_only(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "xena", "xena@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/v1/posts", json={"content": "I love pizza"}, headers=headers)
    await client.post("/api/v1/posts", json={"content": "I love pasta"}, headers=headers)
    await client.post("/api/v1/posts", json={"content": "nothing related"}, headers=headers)

    resp = await client.get("/api/v1/posts?q=pizza")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["content"] == "I love pizza"

    resp_case_insensitive = await client.get("/api/v1/posts?q=PIZZA")
    assert resp_case_insensitive.json()["total"] == 1


async def test_invalid_page_size_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/posts?size=1000")
    assert resp.status_code == 422

    resp2 = await client.get("/api/v1/posts?size=0")
    assert resp2.status_code == 422
