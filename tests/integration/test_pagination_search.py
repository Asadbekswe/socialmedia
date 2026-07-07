from datetime import UTC, datetime, timedelta

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


async def test_pagination_returns_correct_page_and_total(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _verified_token(client, db_session, "will", "will@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(7):
        await client.post(
            "/api/v1/posts",
            json={"title": f"post number {i}", "content": f"post {i}"},
            headers=headers,
        )

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


async def test_search_matches_title_and_content(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "xena", "xena@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/posts",
        json={"title": "I love pizza", "content": "toppings are great"},
        headers=headers,
    )
    await client.post(
        "/api/v1/posts", json={"title": "food thoughts", "content": "I love pasta"}, headers=headers
    )
    await client.post(
        "/api/v1/posts",
        json={"title": "nothing related", "content": "nothing at all"},
        headers=headers,
    )

    by_title = await client.get("/api/v1/posts?q=pizza")
    assert by_title.json()["total"] == 1
    assert by_title.json()["items"][0]["title"] == "I love pizza"

    by_content = await client.get("/api/v1/posts?q=pasta")
    assert by_content.json()["total"] == 1
    assert by_content.json()["items"][0]["content"] == "I love pasta"

    case_insensitive = await client.get("/api/v1/posts?q=PIZZA")
    assert case_insensitive.json()["total"] == 1


async def test_date_range_filter(client: AsyncClient, db_session: AsyncSession):
    token = await _verified_token(client, db_session, "yara", "yara@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/posts", json={"title": "a fresh post", "content": "content"}, headers=headers
    )

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    resp_future = await client.get("/api/v1/posts", params={"date_from": future})
    assert resp_future.json()["total"] == 0

    resp_past = await client.get("/api/v1/posts", params={"date_from": past})
    assert resp_past.json()["total"] == 1

    resp_before_now = await client.get("/api/v1/posts", params={"date_to": past})
    assert resp_before_now.json()["total"] == 0


async def test_invalid_page_size_rejected(client: AsyncClient):
    resp = await client.get("/api/v1/posts?size=1000")
    assert resp.status_code == 422

    resp2 = await client.get("/api/v1/posts?size=0")
    assert resp2.status_code == 422
