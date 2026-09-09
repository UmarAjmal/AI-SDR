import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    payload = {
        "email": "sarah.connor@cyberdyne.com",
        "password": "SuperSecretPassword123!",
        "workspace_name": "Cyberdyne Systems"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["active_role"] == "OWNER"
    assert data["user_id"] is not None
    assert data["active_workspace_id"] is not None

    # Verify encrypted refresh cookie was set
    assert "sdr_refresh_token" in response.cookies

@pytest.mark.asyncio
async def test_duplicate_registration_fails(client: AsyncClient):
    payload = {
        "email": "duplicate@test.com",
        "password": "Password123!",
        "workspace_name": "Acme Corp"
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_user_login_success(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "john.wick@continental.com",
        "password": "BabaYagaPassword456!",
        "workspace_name": "The Continental"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login
    login_payload = {
        "email": "john.wick@continental.com",
        "password": "BabaYagaPassword456!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["active_role"] == "OWNER"

@pytest.mark.asyncio
async def test_user_login_invalid_password(client: AsyncClient):
    reg_payload = {
        "email": "walter.white@heisenberg.com",
        "password": "CorrectPassword123!",
        "workspace_name": "A1A Carwash"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "walter.white@heisenberg.com",
        "password": "WrongPassword999!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email address or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_token_refresh(client: AsyncClient):
    reg_payload = {
        "email": "refresh.user@testing.com",
        "password": "PasswordTest123!",
        "workspace_name": "Refresh Inc"
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    refresh_cookie = reg_res.cookies.get("sdr_refresh_token")
    assert refresh_cookie is not None

    # Call refresh endpoint with cookie
    client.cookies.set("sdr_refresh_token", refresh_cookie)
    refresh_res = await client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data

@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient):
    reg_payload = {
        "email": "profile.user@test.com",
        "password": "PasswordTest123!",
        "workspace_name": "Profile Inc"
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "profile.user@test.com"
