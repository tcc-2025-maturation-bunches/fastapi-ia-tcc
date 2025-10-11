import os
from functools import lru_cache


class Settings:
    def __init__(self):
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

        self.DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", f"fruit-detection-{self.ENVIRONMENT}-users")

        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-in-production")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
        self.CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.CORS_HEADERS = ["*"]

        self.SERVICE_NAME = "auth-lambda"
        self.SERVICE_VERSION = "1.0.0"

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["prod", "production"]

    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["dev", "development", "local"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
