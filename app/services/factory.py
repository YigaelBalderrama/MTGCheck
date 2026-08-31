from __future__ import annotations

from flask.config import Config
import cv2

from app.repositories.card_repository import CardRepository
from app.services.card_detection_service import CardDetectionService
from app.services.card_matching_service import CardMatchingService
from app.services.card_recognition_service import CardRecognitionService
from app.services.ocr_service import OcrService
from app.services.perspective_service import PerspectiveService


def create_card_recognition_service(config: Config) -> CardRecognitionService:
    if config["OPENCV_NUM_THREADS"] >= 0:
        cv2.setNumThreads(config["OPENCV_NUM_THREADS"])

    repository = CardRepository()
    repository.load_index()
    matching_service = CardMatchingService(
        repository=repository,
        threshold=config["RECOGNITION_CONFIDENCE_THRESHOLD"],
    )

    return CardRecognitionService(
        detection_service=CardDetectionService(
            max_cards=config["MAX_CARDS_PER_IMAGE"],
            target_max_dimension=config["DETECTION_TARGET_MAX_DIMENSION"],
        ),
        perspective_service=PerspectiveService(
            output_width=config["CARD_WARP_WIDTH"],
            output_height=config["CARD_WARP_HEIGHT"],
        ),
        ocr_service=OcrService(
            languages=config["OCR_LANGUAGES"],
            gpu=config["OCR_GPU"],
            preload=config["OCR_PRELOAD"],
        ),
        matching_service=matching_service,
        allowed_mime_types=config["ALLOWED_IMAGE_MIME_TYPES"],
        allowed_image_formats=config["ALLOWED_IMAGE_FORMATS"],
        max_size_bytes=config["MAX_CONTENT_LENGTH"],
        confidence_threshold=config["RECOGNITION_CONFIDENCE_THRESHOLD"],
        recovery_confidence_threshold=config["RECOVERY_CONFIDENCE_THRESHOLD"],
        include_diagnostic_metrics=config["ENABLE_DIAGNOSTIC_METRICS"],
        cache_enabled=config["ENABLE_RECOGNITION_CACHE"],
        cache_ttl_seconds=config["RECOGNITION_CACHE_TTL_SECONDS"],
        cache_max_items=config["RECOGNITION_CACHE_MAX_ITEMS"],
    )
