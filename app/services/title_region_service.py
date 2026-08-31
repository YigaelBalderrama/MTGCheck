from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class TitleRegion:
    image: np.ndarray
    variant: str


class TitleRegionService:
    def extract_fast_region(self, card_image: np.ndarray) -> TitleRegion:
        return TitleRegion(
            image=self._prepare_region(card_image, top=0.035, bottom=0.155),
            variant="fast",
        )

    def extract_recovery_regions(self, card_image: np.ndarray) -> list[TitleRegion]:
        base = self._prepare_region(card_image, top=0.025, bottom=0.185)
        adaptive = cv2.adaptiveThreshold(
            base,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            6,
        )
        return [
            TitleRegion(image=adaptive, variant="adaptive"),
            TitleRegion(image=cv2.bitwise_not(base), variant="inverted"),
        ]

    def _prepare_region(
        self, card_image: np.ndarray, top: float, bottom: float
    ) -> np.ndarray:
        height, width = card_image.shape[:2]
        y1 = max(0, int(height * top))
        y2 = min(height, int(height * bottom))
        x1 = max(0, int(width * 0.055))
        x2 = min(width, int(width * 0.79))
        region = card_image[y1:y2, x1:x2]

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced = cv2.resize(
            enhanced, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
        )
        return cv2.GaussianBlur(enhanced, (3, 3), 0)
