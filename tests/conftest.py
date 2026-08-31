from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app import create_app
from app.dtos.recognition_response_dto import RecognitionResponseDto
from app.dtos.recognized_card_dto import PointDto, RecognizedCardDto
from app.extensions import db


def make_image_bytes(
    image_format: str = "JPEG",
    size: tuple[int, int] = (400, 300),
    color: tuple[int, int, int] = (30, 120, 30),
) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


class FakeRecognitionService:
    def recognize(self, image_bytes: bytes, content_type: str | None):
        return RecognitionResponseDto(
            cards_detected=1,
            cards_recognized=1,
            processing_time_ms=12,
            cards=[
                RecognizedCardDto(
                    index=1,
                    recognized=True,
                    detected_text="Sol Ring",
                    name="Sol Ring",
                    confidence=0.96,
                    scryfall_id="scryfall-id",
                    set_name="Commander Masters",
                    set_code="cmm",
                    collector_number="396",
                    image_url="https://example.test/card.jpg",
                    scryfall_url="https://scryfall.com/card",
                    prices={"usd": "1.50", "eur": "1.20"},
                    polygon=[
                        PointDto(10, 10),
                        PointDto(110, 10),
                        PointDto(110, 160),
                        PointDto(10, 160),
                    ],
                )
            ],
        )


@pytest.fixture()
def app_with_fake_service(monkeypatch):
    monkeypatch.setattr(
        "app.create_card_recognition_service",
        lambda config: FakeRecognitionService(),
    )
    flask_app = create_app("testing")
    return flask_app


@pytest.fixture()
def client(app_with_fake_service):
    return app_with_fake_service.test_client()


@pytest.fixture()
def db_app():
    flask_app = create_app("testing")
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def sample_jpeg_bytes() -> bytes:
    return make_image_bytes("JPEG")
