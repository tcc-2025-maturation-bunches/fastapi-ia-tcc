import os
from typing import List
from functools import lru_cache


class Settings:
    
    def __init__(self):
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        
        self.SERVICE_NAME = "request-handler-lambda"
        self.SERVICE_VERSION = "1.0.0"
        
        self.SQS_QUEUE_URL = os.getenv(
            "SQS_QUEUE_URL",
            f"https://sqs.{self.AWS_REGION}.amazonaws.com/account-id/fruit-detection-{self.ENVIRONMENT}-processing"
        )
        self.SQS_MESSAGE_GROUP_ID = "fruit-detection-processing"
        self.SQS_BATCH_SIZE = int(os.getenv("SQS_BATCH_SIZE", "10"))
        
        self.DYNAMODB_TABLE_NAME = os.getenv(
            "DYNAMODB_TABLE_NAME",
            f"fruit-detection-{self.ENVIRONMENT}-results"
        )
        self.DYNAMODB_TTL_DAYS = int(os.getenv("DYNAMODB_TTL_DAYS", "30"))
        
        self.S3_IMAGES_BUCKET = os.getenv(
            "S3_IMAGES_BUCKET",
            f"fruit-detection-{self.ENVIRONMENT}-images"
        )
        self.S3_RESULTS_BUCKET = os.getenv(
            "S3_RESULTS_BUCKET",
            f"fruit-detection-{self.ENVIRONMENT}-results"
        )
        
        self.PRESIGNED_URL_EXPIRY_MINUTES = int(os.getenv("PRESIGNED_URL_EXPIRY_MINUTES", "15"))
        self.MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
        self.ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]
        
        self.MIN_DETECTION_CONFIDENCE = float(os.getenv("MIN_DETECTION_CONFIDENCE", "0.6"))
        self.MIN_MATURATION_CONFIDENCE = float(os.getenv("MIN_MATURATION_CONFIDENCE", "0.7"))
        self.PROCESSING_TIMEOUT_SECONDS = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "300"))
        
        self.API_KEY_HEADER = "X-API-Key"
        self.RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
        
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
        self.CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.CORS_HEADERS = ["*"]
        
    def get_required_metadata_fields(self) -> List[str]:
        return ["user_id", "image_id", "location"]
    
    def get_sqs_message_attributes(self) -> dict:
        return {
            "service": {
                "StringValue": self.SERVICE_NAME,
                "DataType": "String"
            },
            "environment": {
                "StringValue": self.ENVIRONMENT,
                "DataType": "String"
            }
        }
    
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["prod", "production"]
    
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["dev", "development", "local"]
    
    def get_s3_url(self, bucket: str, key: str) -> str:
        return f"https://{bucket}.s3.{self.AWS_REGION}.amazonaws.com/{key}"
    
    def validate_image_type(self, content_type: str) -> bool:
        return content_type in self.ALLOWED_IMAGE_TYPES
    
    def validate_file_size(self, size_bytes: int) -> bool:
        max_size_bytes = self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        return size_bytes <= max_size_bytes


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()