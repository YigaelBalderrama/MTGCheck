from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.utils.image_utils import preprocess_name_region
from app.utils.text_utils import normalize_card_name


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float


class OcrService:
    def __init__(
        self,
        languages: list[str] | None = None,
        gpu: bool = False,
        preload: bool = False,
    ) -> None:
        self.languages = languages or ["en"]
        self.gpu = gpu
        self._reader: Any | None = None
        if preload:
            self._get_reader()

    def extract_text(self, image: np.ndarray) -> OcrResult:
        reader = self._get_reader()
        raw_results = reader.readtext(
            image,
            detail=1,
            paragraph=False,
            decoder="greedy",
            batch_size=1,
        )
        return self._best_result(raw_results)

    def extract_batch(self, images: list[np.ndarray]) -> list[OcrResult]:
        if not images:
            return []

        reader = self._get_reader()
        if hasattr(reader, "readtext_batched"):
            return self._extract_batch_grouped_by_shape(reader, images)

        return [self.extract_text(image) for image in images]

    def _extract_batch_grouped_by_shape(
        self, reader: Any, images: list[np.ndarray]
    ) -> list[OcrResult]:
        grouped_indices: dict[tuple[int, ...], list[int]] = defaultdict(list)
        for index, image in enumerate(images):
            grouped_indices[tuple(image.shape)].append(index)

        results = [OcrResult(text="", confidence=0.0) for _ in images]
        for indices in grouped_indices.values():
            batch_images = [images[index] for index in indices]
            try:
                raw_batches = reader.readtext_batched(
                    batch_images,
                    detail=1,
                    paragraph=False,
                    decoder="greedy",
                    batch_size=min(len(batch_images), 16),
                )
            except ValueError:
                raw_batches = [
                    reader.readtext(
                        image,
                        detail=1,
                        paragraph=False,
                        decoder="greedy",
                        batch_size=1,
                    )
                    for image in batch_images
                ]

            for original_index, raw_results in zip(indices, raw_batches, strict=True):
                results[original_index] = self._best_result(raw_results)

        return results

    def extract_name(self, card_image: np.ndarray) -> OcrResult:
        region = preprocess_name_region(card_image)
        return self.extract_text(region)

    def _best_result(self, raw_results: list) -> OcrResult:
        if not raw_results:
            return OcrResult(text="", confidence=0.0)

        best = max(raw_results, key=lambda item: float(item[2]))
        text = str(best[1]).strip()
        confidence = max(0.0, min(1.0, float(best[2])))
        return OcrResult(text=text, confidence=confidence)

    def score_text_coherence(self, text: str) -> float:
        normalized = normalize_card_name(text)
        if not normalized:
            return 0.0
        letters = sum(character.isalpha() for character in normalized)
        return letters / max(len(normalized), 1)

    def _get_reader(self) -> Any:
        if self._reader is None:
            import easyocr

            self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
        return self._reader
