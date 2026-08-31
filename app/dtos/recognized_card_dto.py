from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PointDto:
    x: int
    y: int

    def to_dict(self) -> dict[str, int]:
        return {"x": int(self.x), "y": int(self.y)}


@dataclass(frozen=True)
class RecognizedCardDto:
    index: int
    recognized: bool
    detected_text: str
    name: str | None
    printed_name: str | None
    oracle_name: str | None
    language: str | None
    confidence: float
    ocr_confidence: float
    name_match_confidence: float
    detection_confidence: float
    scryfall_id: str | None
    set_name: str | None
    set_code: str | None
    collector_number: str | None
    image_url: str | None
    scryfall_url: str | None
    prices: dict[str, Any] | None
    polygon: list[PointDto]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": int(self.index),
            "recognized": bool(self.recognized),
            "detected_text": self.detected_text,
            "name": self.name,
            "printed_name": self.printed_name,
            "oracle_name": self.oracle_name,
            "language": self.language,
            "confidence": round(float(self.confidence), 4),
            "ocr_confidence": round(float(self.ocr_confidence), 4),
            "name_match_confidence": round(float(self.name_match_confidence), 4),
            "detection_confidence": round(float(self.detection_confidence), 4),
            "scryfall_id": self.scryfall_id,
            "set_name": self.set_name,
            "set_code": self.set_code,
            "collector_number": self.collector_number,
            "image_url": self.image_url,
            "scryfall_url": self.scryfall_url,
            "prices": self.prices,
            "polygon": [point.to_dict() for point in self.polygon],
        }
