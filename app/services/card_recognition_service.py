from __future__ import annotations

import time

from app.dtos.recognition_response_dto import RecognitionResponseDto
from app.dtos.recognized_card_dto import PointDto, RecognizedCardDto
from app.services.card_detection_service import CardDetectionService, DetectedCard
from app.services.card_matching_service import CardMatchingService, MatchResult
from app.services.ocr_service import OcrResult, OcrService
from app.services.perspective_service import PerspectiveService
from app.utils.image_utils import pil_to_cv2, validate_image_bytes


class CardRecognitionService:
    def __init__(
        self,
        detection_service: CardDetectionService,
        perspective_service: PerspectiveService,
        ocr_service: OcrService,
        matching_service: CardMatchingService,
        allowed_mime_types: set[str],
        allowed_image_formats: set[str],
        max_size_bytes: int,
        confidence_threshold: float,
    ) -> None:
        self.detection_service = detection_service
        self.perspective_service = perspective_service
        self.ocr_service = ocr_service
        self.matching_service = matching_service
        self.allowed_mime_types = allowed_mime_types
        self.allowed_image_formats = allowed_image_formats
        self.max_size_bytes = max_size_bytes
        self.confidence_threshold = confidence_threshold

    def recognize(
        self,
        image_bytes: bytes,
        content_type: str | None,
    ) -> RecognitionResponseDto:
        started_at = time.perf_counter()
        image = validate_image_bytes(
            image_bytes=image_bytes,
            content_type=content_type,
            allowed_mime_types=self.allowed_mime_types,
            allowed_formats=self.allowed_image_formats,
            max_size_bytes=self.max_size_bytes,
        )
        cv_image = pil_to_cv2(image)
        detections = self.detection_service.detect_cards(cv_image)

        recognized_cards: list[RecognizedCardDto] = []
        for index, detection in enumerate(detections, start=1):
            recognized_cards.append(
                self._recognize_detected_card(index, cv_image, detection)
            )

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return RecognitionResponseDto(
            cards_detected=len(detections),
            cards_recognized=sum(1 for card in recognized_cards if card.recognized),
            processing_time_ms=elapsed_ms,
            cards=recognized_cards,
        )

    def _recognize_detected_card(
        self,
        index: int,
        image,
        detection: DetectedCard,
    ) -> RecognizedCardDto:
        warped = self.perspective_service.warp_card(image, detection.polygon)
        ocr_result, match_result = self._best_orientation_match(warped)

        recognized = (
            match_result.card is not None
            and match_result.confidence >= self.confidence_threshold
        )
        card_payload = match_result.card.to_match_payload() if recognized else {}

        return RecognizedCardDto(
            index=index,
            recognized=recognized,
            detected_text=ocr_result.text,
            name=card_payload.get("name"),
            confidence=match_result.confidence,
            scryfall_id=card_payload.get("scryfall_id"),
            set_name=card_payload.get("set_name"),
            set_code=card_payload.get("set_code"),
            collector_number=card_payload.get("collector_number"),
            image_url=card_payload.get("image_url"),
            scryfall_url=card_payload.get("scryfall_url"),
            prices=card_payload.get("prices"),
            polygon=[
                PointDto(x=round(point[0]), y=round(point[1]))
                for point in self.perspective_service.order_points(detection.polygon)
            ],
        )

    def _best_orientation_match(self, warped):
        best_ocr = OcrResult(text="", confidence=0.0)
        best_match = MatchResult(card=None, confidence=0.0)
        best_score = -1.0

        for candidate in self.perspective_service.orientation_candidates(warped):
            ocr_result = self.ocr_service.extract_name(candidate)
            match_result = self.matching_service.match(
                detected_text=ocr_result.text,
                ocr_confidence=ocr_result.confidence,
            )
            coherence = self.ocr_service.score_text_coherence(ocr_result.text)
            score = (match_result.confidence * 0.85) + (coherence * 0.15)
            if score > best_score:
                best_score = score
                best_ocr = ocr_result
                best_match = match_result

        return best_ocr, best_match
