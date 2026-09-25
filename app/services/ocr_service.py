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
        model_storage_directory: str | None = None,
        engine: str = "easyocr",
    ) -> None:
        self.languages = languages or ["en"]
        self.gpu = gpu
        self.model_storage_directory = model_storage_directory
        self.engine = engine.lower()
        self._reader: Any | None = None
        if preload:
            self._get_reader()

    def extract_text(self, image: np.ndarray) -> OcrResult:
        if self.engine == "tesseract":
            return self._extract_tesseract_text(image)

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

        if self.engine == "tesseract":
            return [self._extract_tesseract_text(image) for image in images]

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

    def _extract_tesseract_text(self, image: np.ndarray) -> OcrResult:
        import pytesseract

        payload = pytesseract.image_to_data(
            image,
            config="--psm 7",
            lang=self._tesseract_language(),
            output_type=pytesseract.Output.DICT,
        )
        words: list[str] = []
        confidences: list[float] = []
        for text, raw_confidence in zip(
            payload.get("text", []),
            payload.get("conf", []),
            strict=False,
        ):
            stripped = str(text).strip()
            if not stripped:
                continue
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                confidence = -1.0
            if confidence < 0:
                continue
            words.append(stripped)
            confidences.append(confidence / 100.0)

        if not words:
            return OcrResult(text="", confidence=0.0)

        return OcrResult(
            text=" ".join(words),
            confidence=max(0.0, min(1.0, sum(confidences) / len(confidences))),
        )

    def _tesseract_language(self) -> str:
        language_map = {
            "en": "eng",
            "es": "spa",
        }
        return "+".join(language_map.get(language, language) for language in self.languages)

    def _get_reader(self) -> Any:
        if self.engine != "easyocr":
            return None

        if self._reader is None:
            import easyocr

            reader_kwargs = {"gpu": self.gpu}
            if self.model_storage_directory:
                reader_kwargs["model_storage_directory"] = self.model_storage_directory

            self._reader = easyocr.Reader(self.languages, **reader_kwargs)
        return self._reader
