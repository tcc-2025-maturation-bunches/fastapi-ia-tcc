from typing import Any, Dict, Optional
from datetime import datetime, timezone


class User:
    def __init__(
            self, 
            user_id: str, 
            username: str, 
            name: str, 
            email: str, 
            user_type: str, 
            created_at: Optional[datetime] = None, 
            updated_at: Optional[datetime] = None
        ):
        self.user_id = user_id
        self.username = username
        self.name = name
        self.email = email
        self.user_type = user_type
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def is_admin(self) -> bool:
        return self.user_type.lower() == "admin"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "user_type": self.user_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            user_id=data["user_id"],
            username=data["username"],
            name=data["name"],
            email=data["email"],
            user_type=data["user_type"],
            created_at=created_at,
            updated_at=updated_at,
        )
