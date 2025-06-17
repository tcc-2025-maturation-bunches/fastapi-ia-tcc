from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4


class Image:

    def __init__(
        self,
        image_url: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        image_id: Optional[str] = None,
        upload_timestamp: Optional[datetime] = None,
    ):
        self.image_id = image_id or f"img-{uuid4()}"
        self.image_url = image_url
        self.user_id = user_id
        self.metadata = metadata or {}
        self.upload_timestamp = upload_timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "image_url": self.image_url,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "upload_timestamp": self.upload_timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Image":
        upload_timestamp = data.get("upload_timestamp")
        if upload_timestamp and isinstance(upload_timestamp, str):
            upload_timestamp = datetime.fromisoformat(upload_timestamp)

        return cls(
            image_url=data["image_url"],
            user_id=data["user_id"],
            metadata=data.get("metadata", {}),
            image_id=data.get("image_id"),
            upload_timestamp=upload_timestamp,
        )
