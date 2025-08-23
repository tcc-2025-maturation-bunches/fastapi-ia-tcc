import re

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


def validate_image_id(image_id: str) -> str:
    if not image_id or len(image_id.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_id não pode estar vazio")

    if len(image_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="image_id não pode ter mais de 128 caracteres"
        )

    return image_id.strip()
