import re
from typing import Any, Dict

from fastapi import HTTPException, status


def validate_device_id(device_id: str) -> str:
    if not device_id or len(device_id.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="device_id não pode estar vazio")

    if len(device_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="device_id não pode ter mais de 100 caracteres"
        )

    if not re.match(r"^[a-zA-Z0-9_-]+$", device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="device_id deve conter apenas caracteres alfanuméricos, hífens e underscores",
        )

    return device_id.strip()


def validate_device_name(device_name: str) -> str:
    if not device_name or len(device_name.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="device_name não pode estar vazio")

    if len(device_name) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="device_name não pode ter mais de 200 caracteres"
        )

    return device_name.strip()


def validate_location(location: str) -> str:
    if not location or len(location.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="location não pode estar vazio")

    if len(location) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="location não pode ter mais de 200 caracteres"
        )

    return location.strip()


def validate_device_status(status_value: str) -> str:
    valid_statuses = ["online", "offline", "pending", "maintenance", "error"]

    if status_value not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status inválido. Valores permitidos: {', '.join(valid_statuses)}",
        )

    return status_value


def validate_device_config(config: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(config, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Configuração deve ser um objeto JSON válido"
        )

    if "image_quality" in config:
        quality = config["image_quality"]
        if not isinstance(quality, int) or quality < 50 or quality > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="image_quality deve ser um número inteiro entre 50 e 100",
            )

    if "image_width" in config:
        width = config["image_width"]
        if not isinstance(width, int) or width < 320 or width > 1920:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="image_width deve ser um número inteiro entre 320 e 1920",
            )

    if "image_height" in config:
        height = config["image_height"]
        if not isinstance(height, int) or height < 240 or height > 1080:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="image_height deve ser um número inteiro entre 240 e 1080",
            )

    if "capture_interval" in config:
        interval = config["capture_interval"]
        if not isinstance(interval, int) or interval < 30 or interval > 3600:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="capture_interval deve ser um número inteiro entre 30 e 3600 segundos",
            )

    if "heartbeat_interval" in config:
        heartbeat = config["heartbeat_interval"]
        if not isinstance(heartbeat, int) or heartbeat < 30 or heartbeat > 300:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="heartbeat_interval deve ser um número inteiro entre 30 e 300 segundos",
            )

    if "max_retries" in config:
        retries = config["max_retries"]
        if not isinstance(retries, int) or retries < 1 or retries > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_retries deve ser um número inteiro entre 1 e 10",
            )

    if "retry_delay" in config:
        delay = config["retry_delay"]
        if not isinstance(delay, int) or delay < 5 or delay > 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="retry_delay deve ser um número inteiro entre 5 e 60 segundos",
            )

    if "timeout" in config:
        timeout = config["timeout"]
        if not isinstance(timeout, int) or timeout < 10 or timeout > 120:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="timeout deve ser um número inteiro entre 10 e 120 segundos",
            )

    return config


def validate_device_capabilities(capabilities: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(capabilities, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Capabilities deve ser um objeto JSON válido"
        )

    if "camera_resolution" in capabilities:
        resolution = capabilities["camera_resolution"]
        valid_resolutions = ["640x480", "1280x720", "1920x1080"]
        if resolution not in valid_resolutions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"camera_resolution inválida. Valores permitidos: {', '.join(valid_resolutions)}",
            )

    if "processing_power" in capabilities:
        power = capabilities["processing_power"]
        valid_powers = ["low", "medium", "high"]
        if power not in valid_powers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"processing_power inválido. Valores permitidos: {', '.join(valid_powers)}",
            )

    boolean_fields = ["auto_capture", "local_storage"]
    for field in boolean_fields:
        if field in capabilities and not isinstance(capabilities[field], bool):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} deve ser um valor booleano (true/false)"
            )

    return capabilities


def validate_heartbeat_data(additional_data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(additional_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="additional_data deve ser um objeto JSON válido"
        )

    numeric_fields = ["total_captures", "uptime_hours", "cpu_usage", "memory_usage", "disk_usage"]
    for field in numeric_fields:
        if field in additional_data:
            value = additional_data[field]
            if not isinstance(value, (int, float)) or value < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} deve ser um número não negativo",
                )

    percentage_fields = ["cpu_usage", "memory_usage", "disk_usage"]
    for field in percentage_fields:
        if field in additional_data:
            value = additional_data[field]
            if isinstance(value, (int, float)) and (value < 0 or value > 100):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} deve ser um valor entre 0 e 100",
                )

    return additional_data
