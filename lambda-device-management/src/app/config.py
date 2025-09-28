import os
from functools import lru_cache


class Settings:
    def __init__(self):
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

        self.SERVICE_NAME = "device-management-lambda"
        self.SERVICE_VERSION = "1.0.0"

        self.DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", f"fruit-detection-{self.ENVIRONMENT}-results")
        self.DYNAMODB_TTL_DAYS = int(os.getenv("DYNAMODB_TTL_DAYS", "30"))

        self.SNS_PROCESSING_COMPLETE_TOPIC = os.getenv(
            "SNS_PROCESSING_COMPLETE_TOPIC", f"arn:aws:sns:{self.AWS_REGION}:account-id:processing-complete-topic"
        )

        self.HEARTBEAT_TIMEOUT_MINUTES = int(os.getenv("HEARTBEAT_TIMEOUT_MINUTES", "5"))
        self.OFFLINE_CHECK_INTERVAL_MINUTES = int(os.getenv("OFFLINE_CHECK_INTERVAL_MINUTES", "10"))

        self.DEFAULT_CAPTURE_INTERVAL = int(os.getenv("DEFAULT_CAPTURE_INTERVAL", "300"))
        self.DEFAULT_IMAGE_QUALITY = int(os.getenv("DEFAULT_IMAGE_QUALITY", "85"))
        self.DEFAULT_HEARTBEAT_INTERVAL = int(os.getenv("DEFAULT_HEARTBEAT_INTERVAL", "60"))

    def get_default_device_config(self) -> dict:
        return {
            "auto_upload": True,
            "store_local": True,
            "image_quality": self.DEFAULT_IMAGE_QUALITY,
            "image_width": 1280,
            "image_height": 720,
            "max_retries": 3,
            "retry_delay": 10,
            "heartbeat_interval": self.DEFAULT_HEARTBEAT_INTERVAL,
            "timeout": 30,
            "capture_interval": self.DEFAULT_CAPTURE_INTERVAL,
        }

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["prod", "production"]

    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["dev", "development", "local"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
