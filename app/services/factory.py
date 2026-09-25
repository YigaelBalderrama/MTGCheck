from __future__ import annotations

import cv2
from flask.config import Config

from app.clients.scryfall_client import ScryfallClient
from app.repositories.card_repository import CardRepository
from app.services.card_detection_service import CardDetectionService
from app.services.card_matching_service import CardMatchingService
from app.services.card_recognition_service import CardRecognitionService
from app.services.ocr_service import OcrService
from app.services.perspective_service import PerspectiveService
from app.services.title_region_service import TitleRegionService


def _optional_config_value(config: Config, key: str):
    try:
        return config[key]
    except KeyError:
        return None


def create_card_recognition_service(config: Config) -> CardRecognitionService:
    if config["OPENCV_NUM_THREADS"] >= 0:
        cv2.setNumThreads(config["OPENCV_NUM_THREADS"])

    scryfall_client = ScryfallClient(
        base_url=config["SCRYFALL_BASE_URL"],
        timeout_seconds=config["SCRYFALL_TIMEOUT_SECONDS"],
        user_agent=config["SCRYFALL_USER_AGENT"],
        accept_header=config["SCRYFALL_ACCEPT"],
        min_request_interval_seconds=config["SCRYFALL_MIN_REQUEST_INTERVAL_SECONDS"],
    )
    if config["CARD_LOOKUP_MODE"] == "scryfall_api":
        matching_service = CardMatchingService(
            threshold=config["RECOGNITION_CONFIDENCE_THRESHOLD"],
            scryfall_client=scryfall_client,
            lookup_mode="scryfall_api",
        )
    else:
        repository = CardRepository()
        repository.load_index()
        matching_service = CardMatchingService(
            repository=repository,
            threshold=config["RECOGNITION_CONFIDENCE_THRESHOLD"],
            scryfall_client=scryfall_client,
            lookup_mode="sqlite",
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
        title_region_service=TitleRegionService(),
        ocr_service=OcrService(
            languages=config["OCR_LANGUAGES"],
            gpu=config["OCR_GPU"],
            preload=config["OCR_PRELOAD"],
            model_storage_directory=_optional_config_value(
                config,
                "OCR_MODEL_STORAGE_DIR",
            ),
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
