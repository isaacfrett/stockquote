from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class StockQuoteRequest(BaseModel):
    symbol: str


class StockQuoteResponse(BaseModel):
    id: int
    symbol: str
    price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True