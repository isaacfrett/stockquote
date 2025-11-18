from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
import os
import requests

from database import get_db, engine
import models as models
import schemas as schemas

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Stock Quote API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://stockquote-ui-1.onrender.com", "https://api.massive.com"],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
)

SECRET_KEY = os.getenv("SECRET_KEY", '')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_email(db: Session, email: str):
    """Get user by email."""
    return db.query(models.User).filter(models.User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate user and return user object if valid."""
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Stock Quote API is running"}


@app.post("/signup", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""

    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@app.post("/token", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint - validates user credentials and returns JWT token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/logout")
async def logout(current_user: models.User = Depends(get_current_user)):
    """Logout endpoint (client should discard token)."""
    return {"message": "Successfully logged out"}


@app.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete the current user's account."""
    db.delete(current_user)
    db.commit()
    return None


@app.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@app.post("/stock-quote", response_model=schemas.StockQuoteResponse)
async def get_stock_quote(
    quote_request: schemas.StockQuoteRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get stock quote information (requires authentication)."""
    symbol = quote_request.symbol.upper()
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML)"
    }
    API_KEY = os.getenv("MASSIVE")
    url = f"https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}?apiKey={API_KEY}"
    response = requests.get(url=url, headers=headers)
    
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Ticker not found")

    ticker = response.json()["ticker"]
    
    db_quote = models.StockQuote(
        user_id=current_user.id,
        symbol=symbol,
        price=ticker["min"]["c"],
        change=ticker["todaysChange"],
        change_percent=ticker["todaysChangePerc"]
    )
    db.add(db_quote)
    db.commit()
    db.refresh(db_quote)
    
    return db_quote


@app.get("/stock-quotes/history", response_model=list[schemas.StockQuoteResponse])
async def get_quote_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's stock quote search history."""
    quotes = db.query(models.StockQuote).filter(
        models.StockQuote.user_id == current_user.id
    ).order_by(models.StockQuote.created_at.desc()).limit(50).all()
    
    return quotes