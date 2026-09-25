from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))


def _database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if not configured_url:
        return f"sqlite:///{DATA_DIR / 'cards_cache.sqlite'}"

    sqlite_prefix = "sqlite:///"
    if not configured_url.startswith(sqlite_prefix):
        return configured_url

    sqlite_path = configured_url.removeprefix(sqlite_prefix)
    if sqlite_path == ":memory:":
        return configured_url

    path = Path(sqlite_path)
    if path.is_absolute():
        return configured_url

    return f"sqlite:///{BASE_DIR / path}"


class BaseConfig:
    ENV = "development"
    TESTING = False
    DEBUG = False

    DATA_DIR = DATA_DIR
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CARD_LOOKUP_MODE = os.getenv("CARD_LOOKUP_MODE", "sqlite").lower()

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_IMAGE_SIZE_MB", "12")) * 1024 * 1024
    ALLOWED_IMAGE_MIME_TYPES: ClassVar[set[str]] = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    ALLOWED_IMAGE_FORMATS: ClassVar[set[str]] = {"JPEG", "PNG", "WEBP"}

    RECOGNITION_CONFIDENCE_THRESHOLD = float(
        os.getenv("RECOGNITION_CONFIDENCE_THRESHOLD", "0.72")
    )
    RECOVERY_CONFIDENCE_THRESHOLD = float(
        os.getenv("RECOVERY_CONFIDENCE_THRESHOLD", "0.55")
    )
    MAX_CARDS_PER_IMAGE = int(os.getenv("MAX_CARDS_PER_IMAGE", "20"))
    DETECTION_TARGET_MAX_DIMENSION = int(
        os.getenv("DETECTION_TARGET_MAX_DIMENSION", "1600")
    )
    CARD_WARP_WIDTH = int(os.getenv("CARD_WARP_WIDTH", "448"))
    CARD_WARP_HEIGHT = int(os.getenv("CARD_WARP_HEIGHT", "624"))
    ENABLE_DIAGNOSTIC_METRICS = (
        os.getenv("ENABLE_DIAGNOSTIC_METRICS", "false").lower() == "true"
    )
    ENABLE_RECOGNITION_CACHE = (
        os.getenv("ENABLE_RECOGNITION_CACHE", "true").lower() == "true"
    )
    RECOGNITION_CACHE_TTL_SECONDS = int(
        os.getenv("RECOGNITION_CACHE_TTL_SECONDS", "900")
    )
    RECOGNITION_CACHE_MAX_ITEMS = int(os.getenv("RECOGNITION_CACHE_MAX_ITEMS", "128"))
    OPENCV_NUM_THREADS = int(os.getenv("OPENCV_NUM_THREADS", "0"))

    OCR_ENGINE = os.getenv("OCR_ENGINE", "easyocr")
    OCR_LANGUAGES: ClassVar[list[str]] = [
        language.strip()
        for language in os.getenv("OCR_LANGUAGES", "en").split(",")
        if language.strip()
    ]
    OCR_GPU = os.getenv("OCR_GPU", "false").lower() == "true"
    OCR_PRELOAD = os.getenv("OCR_PRELOAD", "false").lower() == "true"
    OCR_MODEL_STORAGE_DIR = os.getenv("OCR_MODEL_STORAGE_DIR")

    SCRYFALL_BASE_URL = os.getenv("SCRYFALL_BASE_URL", "https://api.scryfall.com")
    SCRYFALL_TIMEOUT_SECONDS = float(os.getenv("SCRYFALL_TIMEOUT_SECONDS", "8"))
    SCRYFALL_USER_AGENT = os.getenv(
        "SCRYFALL_USER_AGENT",
        "MTGMultiCardRecognitionAPI/1.0 (contact: local-dev@example.com)",
    )
    SCRYFALL_ACCEPT = "application/json;q=0.9,*/*;q=0.8"
    SCRYFALL_MIN_REQUEST_INTERVAL_SECONDS = float(
        os.getenv("SCRYFALL_MIN_REQUEST_INTERVAL_SECONDS", "0.1")
    )

    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "60 per minute")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"


class DevelopmentConfig(BaseConfig):
    ENV = "development"
    DEBUG = True


class TestingConfig(BaseConfig):
    ENV = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CARD_LOOKUP_MODE = "sqlite"
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    ENV = "production"
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None) -> type[BaseConfig]:
    selected = config_name or os.getenv("FLASK_ENV") or os.getenv("APP_ENV")
    return CONFIG_BY_NAME.get((selected or "development").lower(), DevelopmentConfig)
