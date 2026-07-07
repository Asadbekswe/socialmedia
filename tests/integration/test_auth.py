import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def register(
    client: AsyncClient,
    username="alice",
    email="alice@example.com",
    full_name="Alice Example",
    password="supersecret",
):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": full_name,
            "password": password,
        },
    )


async def login(client: AsyncClient, email="alice@example.com", password="supersecret"):
    return await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


async def test_register_succeeds(client: AsyncClient):
    resp = await register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["is_verified"] is False
    assert "hashed_password" not in body


async def test_duplicate_email_rejected(client: AsyncClient):
    await register(client, username="alice")
    resp = await register(client, username="alice2")
    assert resp.status_code == 409


async def test_duplicate_username_rejected(client: AsyncClient):
    await register(client, email="one@example.com")
    resp = await register(client, email="two@example.com")
    assert resp.status_code == 409


async def test_login_issues_valid_jwt(client: AsyncClient):
    await register(client)
    resp = await login(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"

    import jwt as pyjwt

    from app.core.config import settings

    payload = pyjwt.decode(body["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["type"] == "access"
    assert "sub" in payload and "exp" in payload


async def test_login_wrong_password_rejected(client: AsyncClient):
    await register(client)
    resp = await login(client, password="wrongpassword")
    assert resp.status_code == 401


async def test_protected_route_requires_token(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_protected_route_rejects_garbage_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_protected_route_accepts_valid_token(client: AsyncClient):
    await register(client)
    login_resp = await login(client)
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
