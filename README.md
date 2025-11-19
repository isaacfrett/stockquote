# stockquote

A small FastAPI service that fetches stock quote snapshots from the Massive API and stores user search history in a SQL database.

## Overview

This repository provides a REST API for:

- User signup / login (JWT-based)
- Fetching a stock quote snapshot for a given symbol (via Massive API)
- Persisting stock quote lookups per user and retrieving recent search history

The API is implemented with FastAPI and SQLAlchemy and includes a pytest test-suite in `tests/`.

## Features

- FastAPI HTTP endpoints
- JWT authentication (PyJWT)
- Password hashing (pwdlib)
- SQLAlchemy models for users and stock quote history
- Tests using pytest and test fixtures

## Requirements

- Python 3.9.6 (the project uses modern typing and FastAPI features)
- See `requirements.txt` for exact pinned dependencies

## Environment variables

| Name | Description | Example |
|------|-------------|---------|
| DATABASE_URL | SQLAlchemy database URL. For local development you can use SQLite `sqlite:///./dev.db` or a Postgres URL. | `sqlite:///./dev.db` |
| MASSIVE | Massive API key used to fetch quote snapshots. |
| SECRET_KEY | Secret used to sign JWT tokens. |

Note: the code will automatically convert a `postgres://...` URL to `postgresql://...` which Render sometimes provides.

## Quickstart (local development)

1. Clone the repo and enter the directory:

```bash
git clone <your-repo-url>
cd stockquote
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Set environment variables for local development (example using SQLite and a dummy Massive key):

```bash
export DATABASE_URL="sqlite:///./dev.db"
export MASSIVE="your_massive_api_key"
export SECRET_KEY="replace-with-a-secure-random-string"
```

4. Run the app using Uvicorn (development mode):

```bash
uvicorn main:app --reload
```

By default the app will be available at http://127.0.0.1:8000 and the OpenAPI docs are at http://127.0.0.1:8000/docs.

## Running tests

Tests live in the `tests/` directory and use pytest and test fixtures. To run the full test suite:

```bash
# from project root with virtualenv activated
pytest -q
```

If your tests require a database URL, set `DATABASE_URL` to a local test database (SQLite is fine for quick runs).

## API examples

1. Create a user (signup):

```bash
curl -X POST http://127.0.0.1:8000/signup \
	-H "Content-Type: application/json" \
	-d '{"email":"me@example.com","password":"password123"}'
```

2. Get a token (login):

```bash
curl -X POST http://127.0.0.1:8000/token \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "username=me@example.com&password=password123"
```

This returns a JSON payload with `access_token`. Use it in the `Authorization` header for protected endpoints:

```bash
TOKEN="<access_token>"
curl -X POST http://127.0.0.1:8000/stock-quote \
	-H "Authorization: Bearer $TOKEN" \
	-H "Content-Type: application/json" \
	-d '{"symbol":"AAPL"}'
```

3. Get quote history:

```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/stock-quotes/history
```

## Database notes

- The project uses SQLAlchemy Core/ORM and `models.py` defines `User` and `StockQuote` models.
- For local/dev testing `sqlite:///./dev.db` is the easiest option. In production use a managed Postgres instance and set `DATABASE_URL` accordingly.

## Tests and CI

- `pytest` is used. The tests in `tests/` exercise authentication, quote fetching, history, and integration flows.
- If you add CI, run `pytest` and ensure a test database is available or configure tests to use an in-memory SQLite DB.
