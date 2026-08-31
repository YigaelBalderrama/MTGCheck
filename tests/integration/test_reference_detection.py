from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.services.card_detection_service import CardDetectionService
from app.utils.image_utils import pil_to_cv2


def test_reference_photo_detects_14_complete_cards():
    fixture = Path("tests/fixtures/multi_cards_reference.png")
    if not fixture.exists():
        pytest.skip("Fixture no encontrada: tests/fixtures/multi_cards_reference.png")

    image = pil_to_cv2(Image.open(fixture).convert("RGB"))
    detections = CardDetectionService(
        max_cards=20,
        target_max_dimension=1600,
    ).detect_cards(image)

    assert len(detections) == 14
