import pytest
from faker import Faker

fake = Faker()


class TestUserFlow:
    def test_complete_user_flow(self, client):
        """Test complete user flow: signup -> login -> quote -> history -> delete."""
        email = fake.email()
        password = "testpassword123"
        
        response = client.post(
            "/signup",
            json={"email": email, "password": password}
        )
        assert response.status_code == 201
        
        response = client.post(
            "/token",
            data={"username": email, "password": password}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == email
        
        response = client.post(
            "/stock-quote",
            headers=headers,
            json={"symbol": "AAPL"}
        )
        assert response.status_code == 200
        
        response = client.get("/stock-quotes/history", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        
        response = client.post("/logout", headers=headers)
        assert response.status_code == 200
        
        response = client.delete("/users/me", headers=headers)
        assert response.status_code == 204
        
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 401

    def test_unauthorized_access_to_protected_routes(self, client):
        """Test that all protected routes require authentication."""
        protected_routes = [
            ("GET", "/users/me"),
            ("DELETE", "/users/me"),
            ("POST", "/logout"),
            ("POST", "/stock-quote"),
            ("GET", "/stock-quotes/history"),
        ]
        
        for method, route in protected_routes:
            if method == "GET":
                response = client.get(route)
            elif method == "POST":
                response = client.post(route, json={})
            elif method == "DELETE":
                response = client.delete(route)
            
            assert response.status_code == 401, f"{method} {route} should require auth"