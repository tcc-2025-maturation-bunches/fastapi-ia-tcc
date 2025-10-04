from datetime import timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel

from src.app.config import settings

# Mock database
users_db: Dict[str, Dict[str, str]] = {
    "admin": {"password": "admin123", "user_type": "admin"},
    "user1": {"password": "user123", "user_type": "user"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SettingsJWT(BaseModel):
    authjwt_secret_key: str = settings.JWT_SECRET_KEY
    authjwt_access_token_expires: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds


@AuthJWT.load_config
def get_config():
    return SettingsJWT()


auth_router = APIRouter()


@auth_router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, Authorize: AuthJWT = Depends()):
    user = users_db.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    access_token = Authorize.create_access_token(
        subject=data.username,
        user_claims={"user_type": user["user_type"]},
        expires_time=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@auth_router.get("/verify")
def verify_token(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except AuthJWTException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    claims = Authorize.get_raw_jwt()
    return {"user": Authorize.get_jwt_subject(), "claims": claims}
