from typing import Any, Dict


class User:
    def __init__(self, user_id: str, username: str, name: str, email: str, user_type: str):
        self.user_id = user_id
        self.username = username
        self.name = name
        self.email = email
        self.user_type = user_type

    def is_admin(self) -> bool:
        return self.user_type.lower() == "admin"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "user_type": self.user_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            name=data["name"],
            email=data["email"],
            user_type=data["user_type"],
        )
