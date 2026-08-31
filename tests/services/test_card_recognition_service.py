from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image

from app.dtos.recognition_response_dto import RecognitionResponseDto
from app.models.card import Card
from app.services.card_detection_service import DetectedCard
from app.services.card_matching_service import MatchResult
from app.services.card_recognition_service import CardRecognitionService
from app.services.ocr_service import OcrResult
from app.services.title_region_service import TitleRegion
from app.utils.text_utils import normalize_card_name


class StubDetectionService:
    def __init__(self, count: int = 1) -> None:
        self.count = count

    def detect_cards(self, image):
        return [
            DetectedCard(
                polygon=np.array(
                    [[10, 10], [210, 10], [210, 290], [10, 290]],
                    dtype=np.float32,
                ),
                area=56000,
            )
            for _ in range(self.count)
        ]


class StubPerspectiveService:
    def order_points(self, points):
        return points

    def warp_card(self, image, points):
        return np.zeros((880, 630, 3), dtype=np.uint8)

    def orientation_candidates(self, image):
        return [image]


class StubTitleRegionService:
    def extract_fast_region(self, card_image):
        return TitleRegion(image=np.zeros((64, 360), dtype=np.uint8), variant="fast")

    def extract_recovery_regions(self, card_image):
        return [TitleRegion(image=np.zeros((64, 360), dtype=np.uint8), variant="test")]


class StubOcrService:
    def __init__(self) -> None:
        self.calls = 0

    def extract_batch(self, images):
        self.calls += 1
        return [OcrResult("Sol Ring", 0.95) for _ in images]

    def extract_name(self, image):
        return OcrResult("Sol Ring", 0.95)

    def score_text_coherence(self, text):
        return 1.0


@dataclass
class StubMatchingService:
    name_match_confidence: float = 1.0

    def match(self, detected_text: str, ocr_confidence: float):
        card = Card(
            scryfall_id="scryfall-id",
            name="Sol Ring",
            normalized_name=normalize_card_name("Sol Ring"),
            set_name="Commander Masters",
            set_code="cmm",
            collector_number="396",
            image_url="https://example.test/card.jpg",
            scryfall_url="https://scryfall.com/card/test",
            prices={"usd": "1.50", "eur": "1.20"},
        )
        return MatchResult(
            card=card,
            final_confidence=self.name_match_confidence,
            name_match_confidence=self.name_match_confidence,
        )


def test_card_recognition_service_builds_complete_response():
    service = CardRecognitionService(
        detection_service=StubDetectionService(),
        perspective_service=StubPerspectiveService(),
        title_region_service=StubTitleRegionService(),
        ocr_service=StubOcrService(),
        matching_service=StubMatchingService(),
        allowed_mime_types={"image/jpeg"},
        allowed_image_formats={"JPEG"},
        max_size_bytes=1024 * 1024,
        confidence_threshold=0.72,
        recovery_confidence_threshold=0.55,
        include_diagnostic_metrics=True,
        cache_enabled=False,
        cache_ttl_seconds=60,
        cache_max_items=8,
    )

    image = Image.new("RGB", (300, 400), (20, 120, 20))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    response = service.recognize(buffer.getvalue(), "image/jpeg")

    assert isinstance(response, RecognitionResponseDto)
    assert response.cards_detected == 1
    assert response.cards_recognized == 1
    assert response.cards[0].name == "Sol Ring"
    assert response.cards[0].oracle_name == "Sol Ring"
    assert response.metrics is not None
    assert response.cards[0].polygon[0].x == 10


def test_card_recognition_service_marks_low_confidence_as_unrecognized():
    service = CardRecognitionService(
        detection_service=StubDetectionService(),
        perspective_service=StubPerspectiveService(),
        title_region_service=StubTitleRegionService(),
        ocr_service=StubOcrService(),
        matching_service=StubMatchingService(name_match_confidence=0.2),
        allowed_mime_types={"image/jpeg"},
        allowed_image_formats={"JPEG"},
        max_size_bytes=1024 * 1024,
        confidence_threshold=0.72,
        recovery_confidence_threshold=0.55,
        include_diagnostic_metrics=False,
        cache_enabled=False,
        cache_ttl_seconds=60,
        cache_max_items=8,
    )

    image = Image.new("RGB", (300, 400), (20, 120, 20))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    response = service.recognize(buffer.getvalue(), "image/jpeg")

    assert response.cards_detected == 1
    assert response.cards_recognized == 0
    assert response.cards[0].recognized is False
    assert response.cards[0].name is None


def test_card_recognition_service_uses_batch_ocr_for_multiple_cards():
    ocr_service = StubOcrService()
    service = CardRecognitionService(
        detection_service=StubDetectionService(count=3),
        perspective_service=StubPerspectiveService(),
        title_region_service=StubTitleRegionService(),
        ocr_service=ocr_service,
        matching_service=StubMatchingService(),
        allowed_mime_types={"image/jpeg"},
        allowed_image_formats={"JPEG"},
        max_size_bytes=1024 * 1024,
        confidence_threshold=0.72,
        recovery_confidence_threshold=0.55,
        include_diagnostic_metrics=False,
        cache_enabled=False,
        cache_ttl_seconds=60,
        cache_max_items=8,
    )

    image = Image.new("RGB", (300, 400), (20, 120, 20))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    response = service.recognize(buffer.getvalue(), "image/jpeg")

    assert response.cards_detected == 3
    assert ocr_service.calls == 1


def test_card_recognition_service_caches_by_image_hash():
    ocr_service = StubOcrService()
    service = CardRecognitionService(
        detection_service=StubDetectionService(count=1),
        perspective_service=StubPerspectiveService(),
        title_region_service=StubTitleRegionService(),
        ocr_service=ocr_service,
        matching_service=StubMatchingService(),
        allowed_mime_types={"image/jpeg"},
        allowed_image_formats={"JPEG"},
        max_size_bytes=1024 * 1024,
        confidence_threshold=0.72,
        recovery_confidence_threshold=0.55,
        include_diagnostic_metrics=False,
        cache_enabled=True,
        cache_ttl_seconds=60,
        cache_max_items=8,
    )

    image = Image.new("RGB", (300, 400), (20, 120, 20))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    first = service.recognize(buffer.getvalue(), "image/jpeg")
    second = service.recognize(buffer.getvalue(), "image/jpeg")

    assert first == second
    assert ocr_service.calls == 1
