from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class DeviceCapabilities(BaseModel):

    camera_resolution: Optional[str] = "1280x720"
    auto_capture: bool = True
    local_storage: bool = True
    processing_power: Optional[str] = "low"
    platform: Optional[str] = None
    python_version: Optional[str] = None
    opencv_version: Optional[str] = None


class DeviceConfig(BaseModel):
    auto_upload: bool = True
    store_local: bool = True
    image_quality: int = Field(85, ge=50, le=100)
    image_width: int = Field(1280, ge=320, le=1920)
    image_height: int = Field(720, ge=240, le=1080)
    max_retries: int = Field(3, ge=1, le=10)
    retry_delay: int = Field(10, ge=5, le=60)
    heartbeat_interval: int = Field(60, ge=30, le=300)
    timeout: int = Field(30, ge=10, le=120)


class DeviceStats(BaseModel):
    total_captures: int = 0
    successful_captures: int = 0
    failed_captures: int = 0
    last_capture_at: Optional[str] = None
    uptime_hours: float = 0.0
    average_processing_time_ms: int = 0


class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    device_name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    capabilities: Optional[DeviceCapabilities] = None
    status: str = Field("online", pattern="^(online|offline|pending|maintenance)$")
    last_seen: Optional[datetime] = None


class DeviceStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(online|offline|maintenance|error)$")
    last_seen: Optional[datetime] = None
    additional_data: Optional[Dict[str, Any]] = None


class DeviceConfigUpdate(BaseModel):
    capture_interval: Optional[int] = Field(None, ge=30, le=3600)
    image_quality: Optional[int] = Field(None, ge=50, le=100)
    auto_upload: Optional[bool] = None
    store_local: Optional[bool] = None
    heartbeat_interval: Optional[int] = Field(None, ge=30, le=300)


class DeviceResponse(BaseModel):
    device_id: str
    device_name: str
    location: str
    capabilities: Dict[str, Any] = {}
    status: str
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime] = None
    capture_interval: int
    stats: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    is_online: bool


class ImageUploadProcessRequest(BaseModel):
    image_url: HttpUrl
    filename: str
    user_id: str
    metadata: Dict[str, Any] = {}
    maturation_threshold: Optional[float] = Field(0.6, ge=0.1, le=1.0)


class ProcessingJobResponse(BaseModel):
    request_id: str
    image_url: str
    status: str
    device_id: Optional[str] = None
    submitted_at: datetime
    estimated_completion: Optional[datetime] = None


class DeviceListFilter(BaseModel):
    status: Optional[str] = Field(None, pattern="^(online|offline|pending|maintenance|error)$")
    location: Optional[str] = None
    device_type: Optional[str] = None
    last_seen_hours: Optional[int] = Field(None, ge=1, le=168)


class DeviceStatsResponse(BaseModel):
    device_id: str
    device_name: str
    period_days: int
    stats: Dict[str, Any]
    captures_by_day: List[Dict[str, Any]] = []
    success_rate: float
    average_interval: float
    uptime_percentage: float


class DeviceCaptureHistory(BaseModel):
    capture_id: str
    device_id: str
    image_url: str
    captured_at: datetime
    processing_status: str
    processing_time_ms: Optional[int] = None
    results_count: int = 0
    confidence_avg: Optional[float] = None


class GlobalConfigRequest(BaseModel):
    heartbeat_timeout: int = Field(120, ge=30, le=600)
    check_interval: int = Field(60, ge=10, le=300)
    processing_timeout: int = Field(30, ge=10, le=120)
    min_capture_interval: int = Field(30, ge=10, le=300)
    image_quality: int = Field(85, ge=50, le=100)
    max_resolution: str = Field("1280x720", pattern="^(1920x1080|1280x720|640x480)$")
    min_detection_confidence: float = Field(0.6, ge=0.1, le=1.0)
    min_maturation_confidence: float = Field(0.7, ge=0.1, le=1.0)


class DeviceSetupResponse(BaseModel):
    device_id: str
    config_script: str
    install_commands: List[str]
    environment_vars: Dict[str, str]
    next_steps: List[str]


class DeviceDashboardResponse(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    maintenance_devices: int
    total_captures_today: int
    total_captures_week: int
    processing_queue: int
    average_success_rate: float
    devices_by_location: Dict[str, int]
    recent_activities: List[Dict[str, Any]]


class DeviceActivityResponse(BaseModel):
    activity_id: str
    device_id: str
    device_name: str
    action: str
    description: str
    timestamp: datetime
    status: str
    metadata: Dict[str, Any] = {}


class DeviceAlertRequest(BaseModel):
    device_id: str
    alert_type: str = Field(..., pattern="^(offline|error|maintenance|low_disk|high_temp)$")
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    message: str
    metadata: Optional[Dict[str, Any]] = None


class DeviceMaintenanceRequest(BaseModel):
    device_id: str
    maintenance_type: str = Field(..., pattern="^(scheduled|emergency|preventive|corrective)$")
    description: str
    scheduled_for: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=5, le=1440)


class BulkDeviceAction(BaseModel):
    device_ids: List[str] = Field(..., min_length=1, max_length=50)
    action: str = Field(..., pattern="^(update_config|restart|maintenance|delete)$")
    parameters: Optional[Dict[str, Any]] = None
