from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.dtos.recognized_card_dto import RecognizedCardDto


@dataclass(frozen=True)
class RecognitionResponseDto:
    cards_detected: int
    cards_recognized: int
    processing_time_ms: int
    cards: list[RecognizedCardDto]
    metrics: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "cards_detected": int(self.cards_detected),
            "cards_recognized": int(self.cards_recognized),
            "processing_time_ms": int(self.processing_time_ms),
            "cards": [card.to_dict() for card in self.cards],
        }
        if self.metrics is not None:
            payload["metrics"] = {
                key: int(value) for key, value in self.metrics.items()
            }
        return payload
