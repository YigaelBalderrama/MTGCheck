from __future__ import annotations

from app import create_app


def test_scryfall_api_mode_does_not_require_repository_index(monkeypatch):
    def fail_load_index(self, force=False):
        raise AssertionError("SQLite index should not load in scryfall_api mode")

    monkeypatch.setattr(
        "app.repositories.card_repository.CardRepository.load_index", fail_load_index
    )

    class ScryfallConfig:
        def __getitem__(self, key):
            values = {
                "OPENCV_NUM_THREADS": 0,
                "CARD_LOOKUP_MODE": "scryfall_api",
                "SCRYFALL_BASE_URL": "https://api.scryfall.com",
                "SCRYFALL_TIMEOUT_SECONDS": 1,
                "SCRYFALL_USER_AGENT": "test",
                "SCRYFALL_ACCEPT": "application/json",
                "SCRYFALL_MIN_REQUEST_INTERVAL_SECONDS": 0,
                "RECOGNITION_CONFIDENCE_THRESHOLD": 0.72,
                "MAX_CARDS_PER_IMAGE": 20,
                "DETECTION_TARGET_MAX_DIMENSION": 1600,
                "CARD_WARP_WIDTH": 448,
                "CARD_WARP_HEIGHT": 624,
                "OCR_LANGUAGES": ["en", "es"],
                "OCR_GPU": False,
                "OCR_PRELOAD": False,
                "ALLOWED_IMAGE_MIME_TYPES": {"image/jpeg"},
                "ALLOWED_IMAGE_FORMATS": {"JPEG"},
                "MAX_CONTENT_LENGTH": 1024,
                "RECOVERY_CONFIDENCE_THRESHOLD": 0.55,
                "ENABLE_DIAGNOSTIC_METRICS": False,
                "ENABLE_RECOGNITION_CACHE": False,
                "RECOGNITION_CACHE_TTL_SECONDS": 60,
                "RECOGNITION_CACHE_MAX_ITEMS": 8,
            }
            return values[key]

    from app.services.factory import create_card_recognition_service

    service = create_card_recognition_service(ScryfallConfig())

    assert service.matching_service.lookup_mode == "scryfall_api"


def test_development_app_uses_env_scryfall_api_mode():
    app = create_app("development")

    assert app.config["CARD_LOOKUP_MODE"] == "scryfall_api"
