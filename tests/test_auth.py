from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


""" def test_register_user():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    assert response.status_code in (201, 409) """


def test_users_me_requires_auth():
    response = client.get(
        "/api/v1/users/me"
    )

    assert response.status_code == 401