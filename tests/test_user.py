import pytest


class TestGetCurrentUser:
    def test_get_current_user_success(self, client, auth_headers, test_user):
        """Test getting current user info."""
        response = client.get("/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
        assert "hashed_password" not in data

    def test_get_current_user_unauthenticated(self, client):
        """Test getting user info without authentication."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting user info with invalid token."""
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestDeleteUser:
    def test_delete_user_success(self, client, auth_headers, test_user, db_session):
        """Test successful user deletion."""
        response = client.delete("/users/me", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify user is deleted from database
        from main import get_user_by_email
        user = get_user_by_email(db_session, test_user.email)
        assert user is None

    def test_delete_user_unauthenticated(self, client):
        """Test deleting user without authentication."""
        response = client.delete("/users/me")
        assert response.status_code == 401

    def test_delete_user_cascades_quotes(self, client, auth_headers, test_user, db_session):
        """Test that deleting user also deletes their stock quotes."""
        import models
        
        # Create a stock quote for the user
        quote = models.StockQuote(
            user_id=test_user.id,
            symbol="AAPL",
            price=150.00,
            change=2.50,
            change_percent=1.69
        )
        db_session.add(quote)
        db_session.commit()
        
        # Delete the user
        response = client.delete("/users/me", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify quotes are deleted
        quotes = db_session.query(models.StockQuote).filter(
            models.StockQuote.user_id == test_user.id
        ).all()
        assert len(quotes) == 0

    def test_cannot_use_token_after_deletion(self, client, auth_headers):
        """Test that token is invalid after user deletion."""
        # Delete user
        response = client.delete("/users/me", headers=auth_headers)
        assert response.status_code == 204
        
        # Try to use the same token
        response = client.get("/users/me", headers=auth_headers)
        assert response.status_code == 401