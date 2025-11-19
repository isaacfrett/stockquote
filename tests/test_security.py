import pytest
from datetime import datetime, timedelta, timezone
import jwt
from main import SECRET_KEY, ALGORITHM


class TestPasswordSecurity:
    def test_passwords_are_hashed(self, client, db_session):
        """Test that passwords are hashed in database."""
        from main import get_user_by_email
        
        email = "test@example.com"
        password = "testpassword123"
        
        client.post("/signup", json={"email": email, "password": password})
        
        user = get_user_by_email(db_session, email)
        assert user.hashed_password != password
        assert len(user.hashed_password) > 50  # Hashed passwords are long

    def test_different_passwords_different_hashes(self, client, db_session):
        """Test that same password for different users has different hashes."""
        from main import get_user_by_email
        
        email1 = "user1@example.com"
        email2 = "user2@example.com"
        password = "samepassword123"
        
        client.post("/signup", json={"email": email1, "password": password})
        client.post("/signup", json={"email": email2, "password": password})
        
        user1 = get_user_by_email(db_session, email1)
        user2 = get_user_by_email(db_session, email2)
        
        # Even same passwords should have different hashes due to salt
        assert user1.hashed_password != user2.hashed_password


class TestJWTSecurity:
    def test_expired_token_rejected(self, client, test_user):
        """Test that expired tokens are rejected."""
        # Create an expired token
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        token_data = {"sub": test_user.email, "exp": expired_time}
        expired_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    def test_invalid_signature_rejected(self, client, test_user):
        """Test that tokens with invalid signature are rejected."""
        token_data = {"sub": test_user.email}
        invalid_token = jwt.encode(token_data, "wrong-secret", algorithm=ALGORITHM)
        
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401

    def test_malformed_token_rejected(self, client):
        """Test that malformed tokens are rejected."""
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer not.a.valid.token"}
        )
        assert response.status_code == 401

    def test_missing_bearer_prefix(self, client, auth_headers):
        """Test that token without Bearer prefix is rejected."""
        token = auth_headers["Authorization"].replace("Bearer ", "")
        response = client.get(
            "/users/me",
            headers={"Authorization": token}
        )
        assert response.status_code == 401