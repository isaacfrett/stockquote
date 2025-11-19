import pytest
from faker import Faker

fake = Faker()


class TestSignup:
    def test_signup_success(self, client):
        """Test successful user signup."""
        email = fake.email()
        response = client.post(
            "/signup",
            json={"email": email, "password": "password123"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert "id" in data
        assert "hashed_password" not in data

    def test_signup_duplicate_email(self, client, test_user):
        """Test signup with existing email fails."""
        response = client.post(
            "/signup",
            json={"email": test_user.email, "password": "password123"}
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_invalid_email(self, client):
        """Test signup with invalid email format."""
        response = client.post(
            "/signup",
            json={"email": "not-an-email", "password": "password123"}
        )
        assert response.status_code == 422

    def test_signup_weak_password(self, client):
        """Test that short passwords are accepted (validation on frontend)."""
        email = fake.email()
        response = client.post(
            "/signup",
            json={"email": email, "password": "123"}
        )
        # Backend doesn't enforce password strength, that's frontend
        assert response.status_code == 201


class TestLogin:
    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/token",
            data={"username": test_user.email, "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with incorrect password."""
        response = client.post(
            "/token",
            data={"username": test_user.email, "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post(
            "/token",
            data={"username": "nonexistent@example.com", "password": "password123"}
        )
        assert response.status_code == 401

    def test_login_missing_credentials(self, client):
        """Test login without credentials."""
        response = client.post("/token", data={})
        assert response.status_code == 422


class TestLogout:
    def test_logout_authenticated(self, client, auth_headers):
        """Test logout with valid token."""
        response = client.post("/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    def test_logout_unauthenticated(self, client):
        """Test logout without token fails."""
        response = client.post("/logout")
        assert response.status_code == 401

    def test_logout_invalid_token(self, client):
        """Test logout with invalid token."""
        response = client.post(
            "/logout",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401