from __future__ import annotations

from io import BytesIO

from tests.conftest import make_image_bytes


def test_recognize_cards_with_valid_image(client, sample_jpeg_bytes):
    response = client.post(
        "/api/cards/recognize",
        data={"image": (BytesIO(sample_jpeg_bytes), "cards.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["cards_detected"] == 1
    assert payload["cards_recognized"] == 1
    assert payload["cards"][0]["name"] == "Sol Ring"


def test_recognize_cards_without_image(client):
    response = client.post(
        "/api/cards/recognize",
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "MISSING_IMAGE"


def test_recognize_cards_rejects_invalid_image_type():
    from app import create_app

    app = create_app("testing")
    client = app.test_client()
    response = client.post(
        "/api/cards/recognize",
        data={"image": (BytesIO(b"not an image"), "cards.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"


def test_recognize_cards_rejects_too_large_image(app_with_fake_service):
    app_with_fake_service.config["MAX_CONTENT_LENGTH"] = 10
    client = app_with_fake_service.test_client()

    response = client.post(
        "/api/cards/recognize",
        data={"image": (BytesIO(make_image_bytes("JPEG")), "cards.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_response_json_contains_complete_card_shape(client, sample_jpeg_bytes):
    response = client.post(
        "/api/cards/recognize",
        data={"image": (BytesIO(sample_jpeg_bytes), "cards.jpg")},
        content_type="multipart/form-data",
    )

    payload = response.get_json()
    card = payload["cards"][0]
    expected_keys = {
        "index",
        "recognized",
        "detected_text",
        "name",
        "confidence",
        "scryfall_id",
        "set_name",
        "set_code",
        "collector_number",
        "image_url",
        "scryfall_url",
        "prices",
        "polygon",
    }
    assert expected_keys == set(card.keys())
