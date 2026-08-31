from __future__ import annotations

import numpy as np

from app.dtos.recognition_response_dto import RecognitionResponseDto
from app.dtos.recognized_card_dto import PointDto, RecognizedCardDto


def test_response_dto_converts_numpy_scalars_to_json_safe_values():
    response = RecognitionResponseDto(
        cards_detected=np.int64(1),
        cards_recognized=np.int64(0),
        processing_time_ms=np.int64(12),
        metrics={"ocr_ms": np.int64(7)},
        cards=[
            RecognizedCardDto(
                index=np.int64(1),
                recognized=np.bool_(False),
                detected_text="Cut [Hl",
                name=None,
                printed_name=None,
                oracle_name=None,
                language=None,
                confidence=np.float64(0.4085),
                ocr_confidence=np.float64(0.0213),
                name_match_confidence=np.float64(0.45),
                detection_confidence=np.float64(0.8925),
                scryfall_id=None,
                set_name=None,
                set_code=None,
                collector_number=None,
                image_url=None,
                scryfall_url=None,
                prices=None,
                polygon=[PointDto(np.int64(10), np.int64(20))],
            )
        ],
    )

    payload = response.to_dict()

    assert payload["cards_detected"] == 1
    assert payload["cards"][0]["recognized"] is False
    assert payload["cards"][0]["confidence"] == 0.4085
    assert payload["cards"][0]["polygon"][0] == {"x": 10, "y": 20}
