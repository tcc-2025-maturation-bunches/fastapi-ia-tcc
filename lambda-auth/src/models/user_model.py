from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    id: str
    username: str
    name: str
    email: str
    password: str
    user_type: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    user_type: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    email: str
    user_type: str
