from datetime import datetime

from src.shared.domain.entities.image import Image


class TestImageEntity:
    def test_image_creation(self):
        image_url = "https://fruit-analysis.com/banana_maturation.jpg"
        user_id = "banana_quality_inspector"
        metadata = {
            "original_filename": "banana_batch_42.jpg",
            "content_type": "image/jpeg",
        }

        image = Image(image_url=image_url, user_id=user_id, metadata=metadata)

        assert image.image_url == image_url
        assert image.user_id == user_id
        assert image.metadata == metadata
        assert image.image_id is not None
        assert isinstance(image.upload_timestamp, datetime)

    def test_image_with_custom_id(self):
        image_url = "https://fruit-analysis.com/banana_ripeness_check.jpg"
        user_id = "plantation_quality_manager"
        custom_id = "banana-harvest-2035"

        image = Image(image_url=image_url, user_id=user_id, image_id=custom_id)

        assert image.image_id == custom_id

    def test_image_to_dict(self):
        image_url = "https://fruit-analysis.com/banana_spoilage_detection.jpg"
        user_id = "warehouse_supervisor"
        metadata = {
            "original_filename": "banana_shelf_life.jpg",
            "content_type": "image/jpeg",
        }
        custom_timestamp = datetime(2025, 5, 12, 10, 30, 0)
        custom_id = "banana-ripeness-7843"

        image = Image(
            image_url=image_url,
            user_id=user_id,
            metadata=metadata,
            image_id=custom_id,
            upload_timestamp=custom_timestamp,
        )
        image_dict = image.to_dict()

        assert image_dict["image_id"] == custom_id
        assert image_dict["image_url"] == image_url
        assert image_dict["user_id"] == user_id
        assert image_dict["metadata"] == metadata
        assert image_dict["upload_timestamp"] == custom_timestamp.isoformat()

    def test_image_from_dict(self):
        image_dict = {
            "image_id": "banana-ripeness-assessment-5421",
            "image_url": "https://fruit-analysis.com/banana_ripeness_stages.jpg",
            "user_id": "supermarket_quality_control",
            "metadata": {
                "original_filename": "banana_shipment_91.jpg",
                "content_type": "image/jpeg",
            },
            "upload_timestamp": "2025-05-12T10:30:00",
        }

        image = Image.from_dict(image_dict)

        assert image.image_id == image_dict["image_id"]
        assert image.image_url == image_dict["image_url"]
        assert image.user_id == image_dict["user_id"]
        assert image.metadata == image_dict["metadata"]
        assert image.upload_timestamp.isoformat() == image_dict["upload_timestamp"]

    def test_image_from_dict_minimal(self):
        image_dict = {
            "image_url": "https://fruit-analysis.com/banana_maturation_timeline.jpg",
            "user_id": "distribution_center_manager",
        }

        image = Image.from_dict(image_dict)

        assert image.image_url == image_dict["image_url"]
        assert image.user_id == image_dict["user_id"]
        assert isinstance(image.metadata, dict)
        assert isinstance(image.image_id, str)
        assert isinstance(image.upload_timestamp, datetime)
