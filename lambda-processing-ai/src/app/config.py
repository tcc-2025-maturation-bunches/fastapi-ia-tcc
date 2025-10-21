import os
from functools import lru_cache


class Settings:
    def __init__(self):
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

        self.SERVICE_NAME = "processing-ai-lambda"
        self.SERVICE_VERSION = "1.0.0"

        self.SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")

        self.DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", f"fruit-detection-{self.ENVIRONMENT}-results")
        self.DYNAMODB_TTL_DAYS = int(os.getenv("DYNAMODB_TTL_DAYS", "30"))

        self.S3_IMAGES_BUCKET = os.getenv("S3_IMAGES_BUCKET", f"fruit-detection-{self.ENVIRONMENT}-images")
        self.S3_RESULTS_BUCKET = os.getenv("S3_RESULTS_BUCKET", f"fruit-detection-{self.ENVIRONMENT}-results")

        ec2_endpoint = os.getenv("EC2_IA_ENDPOINT", "http://localhost:8001")
        if not ec2_endpoint or ec2_endpoint.strip() == "":
            raise ValueError("EC2_IA_ENDPOINT é obrigatório e não pode estar vazio")
        self.EC2_IA_ENDPOINT = ec2_endpoint

        self.REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))

        self.SNS_DEVICE_MANAGEMENT_TOPIC = os.getenv(
            "SNS_DEVICE_MANAGEMENT_TOPIC",
            f"arn:aws:sns:{self.AWS_REGION}:account-id:device-management-notifications-{self.ENVIRONMENT}",
        )

        self.MIN_DETECTION_CONFIDENCE = float(os.getenv("MIN_DETECTION_CONFIDENCE", "0.6"))
        self.MIN_MATURATION_CONFIDENCE = float(os.getenv("MIN_MATURATION_CONFIDENCE", "0.7"))

        self.MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
        self.RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "5"))

    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ["prod", "production"]

    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["dev", "development", "local"]

    def get_s3_url(self, bucket: str, key: str) -> str:
        return f"https://{bucket}.s3.{self.AWS_REGION}.amazonaws.com/{key}"

    def validate(self) -> None:
        errors = []

        if not self.EC2_IA_ENDPOINT:
            errors.append("EC2_IA_ENDPOINT não pode estar vazio")

        if not self.DYNAMODB_TABLE_NAME:
            errors.append("DYNAMODB_TABLE_NAME não pode estar vazio")

        if self.REQUEST_TIMEOUT <= 0:
            errors.append("REQUEST_TIMEOUT deve ser maior que 0")

        if not (0.0 <= self.MIN_DETECTION_CONFIDENCE <= 1.0):
            errors.append("MIN_DETECTION_CONFIDENCE deve estar entre 0.0 e 1.0")

        if not (0.0 <= self.MIN_MATURATION_CONFIDENCE <= 1.0):
            errors.append("MIN_MATURATION_CONFIDENCE deve estar entre 0.0 e 1.0")

        if errors:
            raise ValueError(f"Erros de configuração: {'; '.join(errors)}")


@lru_cache()
def get_settings() -> Settings:
    settings_instance = Settings()
    settings_instance.validate()
    return settings_instance


settings = get_settings()
