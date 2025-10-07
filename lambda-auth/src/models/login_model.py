from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
