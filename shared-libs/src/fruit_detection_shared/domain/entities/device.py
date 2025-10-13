from datetime import datetime, timezone
from typing import Any, Dict, Optional


class Device:

    def __init__(
        self,
        device_id: str,
        device_name: str,
        location: str,
        capabilities: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        capture_interval: int = 300,
        stats: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.location = location
        self.capabilities = capabilities or {}
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.last_seen = last_seen or datetime.now(timezone.utc)
        self.capture_interval = capture_interval
        self.stats = stats or self._init_stats()
        self.config = config or self._init_config()

    def _init_stats(self) -> Dict[str, Any]:
        return {
            "total_captures": 0,
            "successful_captures": 0,
            "failed_captures": 0,
            "last_capture_at": None,
            "uptime_hours": 0,
            "average_processing_time_ms": 0,
        }

    def _init_config(self) -> Dict[str, Any]:
        return {
            "auto_upload": True,
            "store_local": True,
            "image_quality": 85,
            "image_width": 1280,
            "image_height": 720,
            "max_retries": 3,
            "retry_delay": 10,
            "heartbeat_interval": 60,
            "timeout": 30,
        }

    def update_heartbeat(self, status: Optional[str] = None, additional_data: Optional[Dict[str, Any]] = None):
        self.last_seen = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

        if status:
            self.status = status

        if additional_data:
            if "total_captures" in additional_data:
                self.stats["total_captures"] = additional_data["total_captures"]
            if "uptime_hours" in additional_data:
                self.stats["uptime_hours"] = additional_data["uptime_hours"]

    def is_online(self, timeout_minutes: int = 5) -> bool:
        if not self.last_seen:
            return False

        time_diff = datetime.now(timezone.utc) - self.last_seen
        return time_diff.total_seconds() < (timeout_minutes * 60)

    def increment_capture_count(self, success: bool = True):
        self.stats["total_captures"] += 1
        if success:
            self.stats["successful_captures"] += 1
        else:
            self.stats["failed_captures"] += 1

        self.stats["last_capture_at"] = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc)

    def update_config(self, new_config: Dict[str, Any]):
        self.config.update(new_config)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pk": f"DEVICE#{self.device_id}",
            "sk": f"INFO#{self.device_id}",
            "entity_type": "DEVICE",
            "device_id": self.device_id,
            "device_name": self.device_name,
            "location": self.location,
            "capabilities": self.capabilities,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "capture_interval": self.capture_interval,
            "stats": self.stats,
            "config": self.config,
            "is_online": self.is_online(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        last_seen = None
        if data.get("last_seen"):
            last_seen = datetime.fromisoformat(data["last_seen"])

        return cls(
            device_id=data["device_id"],
            device_name=data["device_name"],
            location=data["location"],
            capabilities=data.get("capabilities", {}),
            status=data.get("status", "pending"),
            created_at=created_at,
            updated_at=updated_at,
            last_seen=last_seen,
            capture_interval=data.get("capture_interval", 300),
            stats=data.get("stats", {}),
            config=data.get("config", {}),
        )
