import os
from functools import lru_cache


class Settings:
    def __init__(self):
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

        self.SERVICE_NAME = "results-query-lambda"
        self.SERVICE_VERSION = "1.0.0"

        self.DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", f"fruit-detection-{self.ENVIRONMENT}-results")
        self.S3_RESULTS_BUCKET = os.getenv("S3_RESULTS_BUCKET", f"fruit-detection-{self.ENVIRONMENT}-results")

        self.MAX_QUERY_LIMIT = int(os.getenv("MAX_QUERY_LIMIT", "200"))
        self.DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))

        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
        self.CORS_METHODS = ["GET", "OPTIONS"]
        self.CORS_HEADERS = ["*"]

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["prod", "production"]

    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["dev", "development", "local"]

    def get_s3_url(self, bucket: str, key: str) -> str:
        return f"https://{bucket}.s3.{self.AWS_REGION}.amazonaws.com/{key}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
