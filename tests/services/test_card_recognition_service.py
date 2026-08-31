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
from app.utils.text_utils import normalize_card_name


class StubDetectionService:
    def detect_cards(self, image):
        return [
            DetectedCard(
                polygon=np.array(
                    [[10, 10], [210, 10], [210, 290], [10, 290]],
                    dtype=np.float32,
                ),
                area=56000,
            )
        ]


class StubPerspectiveService:
    def order_points(self, points):
        return points

    def warp_card(self, image, points):
        return np.zeros((880, 630, 3), dtype=np.uint8)

    def orientation_candidates(self, image):
        return [image]


class StubOcrService:
    def extract_name(self, image):
        return OcrResult("Sol Ring", 0.95)

    def score_text_coherence(self, text):
        return 1.0


@dataclass
class StubMatchingService:
    confidence: float = 0.96

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
        return MatchResult(card=card, confidence=self.confidence)


def test_card_recognition_service_builds_complete_response():
    service = CardRecognitionService(
        detection_service=StubDetectionService(),
        perspective_service=StubPerspectiveService(),
        ocr_service=StubOcrService(),
        matching_service=StubMatchingService(),
        allowed_mime_types={"image/jpeg"},
        allowed_image_formats={"JPEG"},
        max_size_bytes=1024 * 1024,
        confidence_threshold=0.72,
    )

    image = Image.new("RGB", (300, 400), (20, 120, 20))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    response = service.recognize(buffer.getvalue(), "image/jpeg")

    assert isinstance(response, RecognitionResponseDto)
    assert response.cards_detected == 1
    assert response.cards_recognized == 1
    assert response.cards[0].name == "Sol Ring"
    assert response.cards[0].polygon[0].x == 10


def test_card_recognition_service_marks_low_confidence_as_unrecognized():
    service = CardRecognitionService(
        detection_service=StubDetectionService(),
        perspective_service=StubPerspectiveService(),
        ocr_service=StubOcrService(),
        matching_service=StubMatchingService(confidence=0.41),
        allowed_mime_types={"image/jpeg"},
        allowed_image_formats={"JPEG"},
        max_size_bytes=1024 * 1024,
        confidence_threshold=0.72,
    )

    image = Image.new("RGB", (300, 400), (20, 120, 20))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")

    response = service.recognize(buffer.getvalue(), "image/jpeg")

    assert response.cards_detected == 1
    assert response.cards_recognized == 0
    assert response.cards[0].recognized is False
    assert response.cards[0].name is None
