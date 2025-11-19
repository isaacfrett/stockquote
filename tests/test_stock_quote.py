import pytest


class TestStockQuote:
    def test_get_stock_quote_success(self, client, auth_headers):
        """Test successful stock quote retrieval."""
        response = client.post(
            "/stock-quote",
            headers=auth_headers,
            json={"symbol": "AAPL"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "price" in data
        assert "change" in data
        assert "change_percent" in data
        assert "id" in data
        assert "created_at" in data

    def test_get_stock_quote_case_insensitive(self, client, auth_headers):
        """Test that symbol is case insensitive."""
        response = client.post(
            "/stock-quote",
            headers=auth_headers,
            json={"symbol": "aapl"}
        )
        assert response.status_code == 200
        assert response.json()["symbol"] == "AAPL"

    def test_get_stock_quote_invalid_symbol(self, client, auth_headers):
        """Test requesting an invalid stock symbol."""
        response = client.post(
            "/stock-quote",
            headers=auth_headers,
            json={"symbol": "INVALID"}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_stock_quote_unauthenticated(self, client):
        """Test stock quote request without authentication."""
        response = client.post(
            "/stock-quote",
            json={"symbol": "AAPL"}
        )
        assert response.status_code == 401

    def test_get_stock_quote_saves_to_database(self, client, auth_headers, test_user, db_session):
        """Test that stock quote is saved to database."""
        import models
        
        response = client.post(
            "/stock-quote",
            headers=auth_headers,
            json={"symbol": "MSFT"}
        )
        assert response.status_code == 200
        
        # Check database
        quotes = db_session.query(models.StockQuote).filter(
            models.StockQuote.user_id == test_user.id,
            models.StockQuote.symbol == "MSFT"
        ).all()
        assert len(quotes) == 1
        assert quotes[0].symbol == "MSFT"

    def test_multiple_stock_quotes(self, client, auth_headers):
        """Test requesting multiple stock quotes."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        for symbol in symbols:
            response = client.post(
                "/stock-quote",
                headers=auth_headers,
                json={"symbol": symbol}
            )
            assert response.status_code == 200
            assert response.json()["symbol"] == symbol


class TestStockQuoteHistory:
    def test_get_quote_history_empty(self, client, auth_headers):
        """Test getting history when user has no quotes."""
        response = client.get("/stock-quotes/history", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_quote_history_with_quotes(self, client, auth_headers):
        """Test getting quote history with existing quotes."""
        # Create some quotes
        symbols = ["AAPL", "GOOGL", "MSFT"]
        for symbol in symbols:
            client.post(
                "/stock-quote",
                headers=auth_headers,
                json={"symbol": symbol}
            )
        
        # Get history
        response = client.get("/stock-quotes/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("symbol" in quote for quote in data)

    def test_get_quote_history_unauthenticated(self, client):
        """Test getting history without authentication."""
        response = client.get("/stock-quotes/history")
        assert response.status_code == 401


    def test_get_quote_history_only_own_quotes(self, client, db_session):
        """Test that users only see their own quote history."""
        from main import get_password_hash
        import models
        
        # Create two users
        user1 = models.User(
            email="user1@example.com",
            hashed_password=get_password_hash("password123")
        )
        user2 = models.User(
            email="user2@example.com",
            hashed_password=get_password_hash("password123")
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # Create quotes for user1
        quote1 = models.StockQuote(
            user_id=user1.id,
            symbol="AAPL",
            price=150.00,
            change=2.50,
            change_percent=1.69
        )
        # Create quotes for user2
        quote2 = models.StockQuote(
            user_id=user2.id,
            symbol="GOOGL",
            price=140.00,
            change=-1.50,
            change_percent=-1.06
        )
        db_session.add_all([quote1, quote2])
        db_session.commit()
        
        # Login as user1
        response = client.post(
            "/token",
            data={"username": "user1@example.com", "password": "password123"}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get history for user1
        response = client.get("/stock-quotes/history", headers=headers)
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["symbol"] == "AAPL"