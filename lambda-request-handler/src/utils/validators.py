import re
from typing import Any, Dict

from fastapi import HTTPException, status


def validate_user_id(user_id: str) -> str:
    if not user_id or len(user_id.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id não pode estar vazio")

    if len(user_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user_id não pode ter mais de 128 caracteres"
        )

    if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id deve conter apenas caracteres alfanuméricos, hífens e underscores",
        )

    return user_id.strip()


def validate_request_id(request_id: str) -> str:
    if not request_id or len(request_id.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="request_id não pode estar vazio")

    if len(request_id) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="request_id não pode ter mais de 64 caracteres"
        )

    if not re.match(r"^req-[a-zA-Z0-9]{8,}$", request_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="request_id deve ter o formato 'req-xxxxxxxxxx'"
        )

    return request_id.strip()


def validate_image_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = ["user_id", "image_id", "location"]

    for field in required_fields:
        if field not in metadata:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campo obrigatório ausente: {field}")

        if not isinstance(metadata[field], str) or len(metadata[field].strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Campo {field} deve ser uma string não vazia"
            )

    metadata["user_id"] = validate_user_id(metadata["user_id"])

    if len(metadata["image_id"]) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="image_id não pode ter mais de 128 caracteres"
        )

    if len(metadata["location"]) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="location não pode ter mais de 255 caracteres"
        )
    if "notes" in metadata and metadata["notes"]:
        if len(str(metadata["notes"])) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="notes não pode ter mais de 1000 caracteres"
            )

    return metadata
