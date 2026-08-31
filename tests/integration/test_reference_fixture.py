from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.utils.text_utils import normalize_card_name

EXPECTED_REFERENCE_NAMES = {
    normalize_card_name(name)
    for name in [
        "Massacre Girl",
        "Incinerar",
        "Mutilate",
        "La crueldad de Gix",
        "Empantanar",
        "Difundeplagas",
        "Fleshbag Marauder",
        "Discípulo del demonio",
        "Merodeador maldito",
        "Epic Downfall",
        "Bitter Triumph",
        "Cut Down",
        "Pharika's Libation",
        "Feed the Swarm",
    ]
}


def test_reference_photo_detects_and_recognizes_expected_cards():
    fixture = Path("tests/fixtures/multi_cards_reference.png")
    if not fixture.exists():
        pytest.skip(
            "Fixture no encontrada: adjunta la imagen y guardala como "
            "tests/fixtures/multi_cards_reference.png"
        )

    app = create_app("testing")
    with app.app_context():
        card_count = db.session.execute(text("SELECT COUNT(*) FROM cards")).scalar()
        if not card_count:
            pytest.skip("Catalogo local vacio; importa all_cards antes de esta prueba.")

    with fixture.open("rb") as image_file:
        response = app.test_client().post(
            "/api/cards/recognize",
            data={"image": (image_file, "multi_cards_reference.png")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["cards_detected"] == 14
    assert payload["cards_recognized"] >= 13

    recognized_names = {
        normalize_card_name(card.get("printed_name") or card.get("name"))
        for card in payload["cards"]
        if card["recognized"]
    }
    assert len(EXPECTED_REFERENCE_NAMES.intersection(recognized_names)) >= 13
