from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass

import cv2
import numpy as np

from app.dtos.recognition_response_dto import RecognitionResponseDto
from app.dtos.recognized_card_dto import PointDto, RecognizedCardDto
from app.services.card_detection_service import CardDetectionService, DetectedCard
from app.services.card_matching_service import CardMatchingService, MatchResult
from app.services.ocr_service import OcrResult, OcrService
from app.services.perspective_service import PerspectiveService
from app.services.title_region_service import TitleRegionService
from app.utils.image_utils import pil_to_cv2, validate_image_bytes


@dataclass
class CardWorkItem:
    index: int
    detection: DetectedCard
    warped: np.ndarray
    ocr_result: OcrResult
    match_result: MatchResult


class RecognitionResultCache:
    def __init__(self, max_items: int, ttl_seconds: int) -> None:
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[str, tuple[float, RecognitionResponseDto]] = (
            OrderedDict()
        )

    def get(self, key: str) -> RecognitionResponseDto | None:
        item = self._items.get(key)
        if item is None:
            return None

        stored_at, response = item
        if time.monotonic() - stored_at > self.ttl_seconds:
            self._items.pop(key, None)
            return None

        self._items.move_to_end(key)
        return response

    def set(self, key: str, response: RecognitionResponseDto) -> None:
        self._items[key] = (time.monotonic(), response)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)


class StageTimer:
    def __init__(self) -> None:
        self.metrics: dict[str, int] = {
            "decode_ms": 0,
            "detection_ms": 0,
            "perspective_ms": 0,
            "title_preprocessing_ms": 0,
            "ocr_ms": 0,
            "matching_ms": 0,
            "total_ms": 0,
        }

    def measure(self, key: str):
        return _StageMeasurement(self.metrics, key)


class _StageMeasurement:
    def __init__(self, metrics: dict[str, int], key: str) -> None:
        self.metrics = metrics
        self.key = key
        self.started_at = 0.0

    def __enter__(self):
        self.started_at = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        elapsed = int((time.perf_counter() - self.started_at) * 1000)
        self.metrics[self.key] += elapsed


class CardRecognitionService:
    def __init__(
        self,
        detection_service: CardDetectionService,
        perspective_service: PerspectiveService,
        title_region_service: TitleRegionService,
        ocr_service: OcrService,
        matching_service: CardMatchingService,
        allowed_mime_types: set[str],
        allowed_image_formats: set[str],
        max_size_bytes: int,
        confidence_threshold: float,
        recovery_confidence_threshold: float,
        include_diagnostic_metrics: bool,
        cache_enabled: bool,
        cache_ttl_seconds: int,
        cache_max_items: int,
    ) -> None:
        self.detection_service = detection_service
        self.perspective_service = perspective_service
        self.title_region_service = title_region_service
        self.ocr_service = ocr_service
        self.matching_service = matching_service
        self.allowed_mime_types = allowed_mime_types
        self.allowed_image_formats = allowed_image_formats
        self.max_size_bytes = max_size_bytes
        self.confidence_threshold = confidence_threshold
        self.recovery_confidence_threshold = recovery_confidence_threshold
        self.include_diagnostic_metrics = include_diagnostic_metrics
        self.cache_enabled = cache_enabled
        self.cache = RecognitionResultCache(
            max_items=cache_max_items,
            ttl_seconds=cache_ttl_seconds,
        )

    def recognize(
        self,
        image_bytes: bytes,
        content_type: str | None,
    ) -> RecognitionResponseDto:
        started_at = time.perf_counter()
        timer = StageTimer()

        with timer.measure("decode_ms"):
            image = validate_image_bytes(
                image_bytes=image_bytes,
                content_type=content_type,
                allowed_mime_types=self.allowed_mime_types,
                allowed_formats=self.allowed_image_formats,
                max_size_bytes=self.max_size_bytes,
            )
            cache_key = hashlib.sha256(image_bytes).hexdigest()
            cached = self.cache.get(cache_key) if self.cache_enabled else None
            if cached is not None:
                return cached
            cv_image = pil_to_cv2(image)

        with timer.measure("detection_ms"):
            detections = self.detection_service.detect_cards(cv_image)

        if not detections:
            response = self._build_response([], started_at, timer)
            self._cache_response(cache_key, response)
            return response

        with timer.measure("perspective_ms"):
            warped_cards = [
                self.perspective_service.warp_card(cv_image, detection.polygon)
                for detection in detections
            ]

        with timer.measure("title_preprocessing_ms"):
            title_regions = [
                self.title_region_service.extract_fast_region(warped).image
                for warped in warped_cards
            ]

        with timer.measure("ocr_ms"):
            ocr_results = self.ocr_service.extract_batch(title_regions)

        with timer.measure("matching_ms"):
            match_results = [
                self.matching_service.match(
                    detected_text=ocr_result.text,
                    ocr_confidence=ocr_result.confidence,
                )
                for ocr_result in ocr_results
            ]

        work_items = [
            CardWorkItem(
                index=index,
                detection=detection,
                warped=warped,
                ocr_result=ocr_result,
                match_result=match_result,
            )
            for index, (detection, warped, ocr_result, match_result) in enumerate(
                zip(detections, warped_cards, ocr_results, match_results, strict=True),
                start=1,
            )
        ]

        self._recover_uncertain_cards(work_items, timer)
        response = self._build_response(work_items, started_at, timer)
        self._cache_response(cache_key, response)
        return response

    def _recover_uncertain_cards(
        self, work_items: list[CardWorkItem], timer: StageTimer
    ) -> None:
        uncertain_items = [
            item
            for item in work_items
            if self._final_confidence(item) < self.confidence_threshold
            and (
                self._final_confidence(item) >= self.recovery_confidence_threshold
                or not item.ocr_result.text
            )
        ]
        if not uncertain_items:
            return

        recovery_jobs: list[tuple[CardWorkItem, np.ndarray]] = []
        with timer.measure("title_preprocessing_ms"):
            for item in uncertain_items:
                rotated = cv2.rotate(item.warped, cv2.ROTATE_180)
                recovery_jobs.append(
                    (
                        item,
                        self.title_region_service.extract_fast_region(rotated).image,
                    )
                )
                for region in self.title_region_service.extract_recovery_regions(
                    item.warped
                ):
                    recovery_jobs.append((item, region.image))

        with timer.measure("ocr_ms"):
            recovery_ocr_results = self.ocr_service.extract_batch(
                [image for _, image in recovery_jobs]
            )

        with timer.measure("matching_ms"):
            for (item, _), ocr_result in zip(
                recovery_jobs, recovery_ocr_results, strict=True
            ):
                match_result = self.matching_service.match(
                    detected_text=ocr_result.text,
                    ocr_confidence=ocr_result.confidence,
                )
                recovered_score = self._combined_confidence(
                    match_result=match_result,
                    ocr_result=ocr_result,
                    detection_confidence=item.detection.confidence,
                )
                if recovered_score > self._final_confidence(item):
                    item.ocr_result = ocr_result
                    item.match_result = match_result

    def _build_response(
        self,
        work_items: list[CardWorkItem],
        started_at: float,
        timer: StageTimer,
    ) -> RecognitionResponseDto:
        cards = [self._to_dto(item) for item in work_items]
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        timer.metrics["total_ms"] = elapsed_ms
        return RecognitionResponseDto(
            cards_detected=len(work_items),
            cards_recognized=sum(1 for card in cards if card.recognized),
            processing_time_ms=elapsed_ms,
            cards=cards,
            metrics=timer.metrics if self.include_diagnostic_metrics else None,
        )

    def _to_dto(self, item: CardWorkItem) -> RecognizedCardDto:
        final_confidence = self._final_confidence(item)
        recognized = (
            item.match_result.card is not None
            and final_confidence >= self.confidence_threshold
        )
        card_payload = item.match_result.card.to_match_payload() if recognized else {}

        return RecognizedCardDto(
            index=item.index,
            recognized=recognized,
            detected_text=item.ocr_result.text,
            name=card_payload.get("name"),
            printed_name=card_payload.get("printed_name"),
            oracle_name=card_payload.get("oracle_name"),
            language=card_payload.get("language"),
            confidence=final_confidence,
            ocr_confidence=item.ocr_result.confidence,
            name_match_confidence=item.match_result.name_match_confidence,
            detection_confidence=item.detection.confidence,
            scryfall_id=card_payload.get("scryfall_id"),
            set_name=card_payload.get("set_name"),
            set_code=card_payload.get("set_code"),
            collector_number=card_payload.get("collector_number"),
            image_url=card_payload.get("image_url"),
            scryfall_url=card_payload.get("scryfall_url"),
            prices=card_payload.get("prices"),
            polygon=[
                PointDto(x=round(point[0]), y=round(point[1]))
                for point in self.perspective_service.order_points(
                    item.detection.polygon
                )
            ],
        )

    def _final_confidence(self, item: CardWorkItem) -> float:
        return self._combined_confidence(
            match_result=item.match_result,
            ocr_result=item.ocr_result,
            detection_confidence=item.detection.confidence,
        )

    def _combined_confidence(
        self,
        match_result: MatchResult,
        ocr_result: OcrResult,
        detection_confidence: float,
    ) -> float:
        if match_result.card is None:
            return 0.0
        return (
            match_result.name_match_confidence * 0.70
            + ocr_result.confidence * 0.20
            + detection_confidence * 0.10
        )

    def _cache_response(self, cache_key: str, response: RecognitionResponseDto) -> None:
        if self.cache_enabled:
            self.cache.set(cache_key, response)
