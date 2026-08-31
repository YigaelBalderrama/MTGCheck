from __future__ import annotations

from io import BytesIO

from tests.conftest import make_image_bytes


def test_internal_error_returns_json_even_in_debug(monkeypatch):
    class BrokenRecognitionService:
        def recognize(self, image_bytes: bytes, content_type: str | None):
            raise ValueError("boom")

    monkeypatch.setattr(
        "app.create_card_recognition_service",
        lambda config: BrokenRecognitionService(),
    )
    from app import create_app

    flask_app = create_app("development")
    client = flask_app.test_client()

    response = client.post(
        "/api/cards/recognize",
        data={"image": (BytesIO(make_image_bytes("JPEG")), "cards.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.mimetype == "application/json"
    assert response.get_json()["error"]["code"] == "RECOGNITION_ERROR"
