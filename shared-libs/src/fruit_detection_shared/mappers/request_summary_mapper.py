from datetime import datetime, timezone
from typing import Any, Dict

from fruit_detection_shared.domain.entities.combined_result import CombinedResult


class RequestSummaryMapper:
    @staticmethod
    def to_dynamo_item(
        user_id: str,
        request_id: str,
        initial_metadata: Dict[str, Any],
        combined_result: CombinedResult,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        detection_data = combined_result.detection
        detection_result_dict = detection_data.model_dump(exclude_none=True) if detection_data else {}

        known_metadata_keys = {
            "image_id",
            "user_id",
            "location",
            "processing_type",
            "notes",
            "maturation_threshold",
            "device_id",
        }

        structured_metadata = {
            "location": initial_metadata.get("location"),
            "processing_type": initial_metadata.get("processing_type"),
            "notes": initial_metadata.get("notes"),
            "maturation_threshold": initial_metadata.get("maturation_threshold"),
            "device_id": initial_metadata.get("device_id"),
        }

        additional_metadata = {
            k: v for k, v in initial_metadata.items() if k not in known_metadata_keys and k not in ["image_url"]
        }

        structured_metadata = {k: v for k, v in structured_metadata.items() if v is not None}

        item = {
            "pk": f"USER#{user_id}",
            "sk": f"REQUEST#{now}#{request_id}",
            "request_id": request_id,
            "image_id": initial_metadata.get("image_id"),
            "user_id": user_id,
            "device_id": initial_metadata.get("device_id"),
            "status": combined_result.status,
            "created_at": now,
            "updated_at": now,
            "entity_type": "COMBINED_RESULT",
            "image_url": initial_metadata.get("image_url"),
            "image_result_url": combined_result.image_result_url,
            "processing_time_ms": combined_result.processing_time_ms,
            "initial_metadata": structured_metadata,
            "additional_metadata": additional_metadata if additional_metadata else None,
            "detection_result": detection_result_dict,
            "processing_metadata": (
                combined_result.processing_metadata.model_dump(exclude_none=True)
                if combined_result.processing_metadata
                else None
            ),
            "error_info": None,
        }

        item = {k: v for k, v in item.items() if v is not None}

        if combined_result.status in ("error", "partial_error"):
            item["error_info"] = {
                "error_code": combined_result.error_code,
                "error_message": combined_result.error_message,
                "error_details": combined_result.error_details,
            }

        return item
