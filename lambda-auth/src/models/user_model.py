from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Model para criação de usuário (request)"""

    username: str
    name: str
    email: EmailStr
    password: str
    user_type: str = "user"


class UserUpdate(BaseModel):
    """Model para atualização de usuário (request)"""

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    user_type: Optional[str] = None


class UserResponse(BaseModel):
    """Model para resposta de usuário (response)"""

    id: str
    username: str
    name: str
    email: str
    user_type: str
    created_at: datetime
    updated_at: datetime
