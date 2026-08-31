from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import cv2
import numpy as np


@dataclass(frozen=True)
class DetectedCard:
    polygon: np.ndarray
    area: float
    confidence: float = 1.0


class CardDetectionService:
    def __init__(self, max_cards: int = 10, target_max_dimension: int = 1500) -> None:
        self.max_cards = max_cards
        self.target_max_dimension = target_max_dimension

    def detect_cards(self, image: np.ndarray) -> list[DetectedCard]:
        original_height, original_width = image.shape[:2]
        max_dimension = self.target_max_dimension
        scale = min(1.0, max_dimension / max(original_width, original_height))
        resized = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1.0 else image

        candidates: list[DetectedCard] = []
        min_area = resized.shape[0] * resized.shape[1] * 0.008
        max_area = resized.shape[0] * resized.shape[1] * 0.9

        for mask in self._build_detection_masks(resized):
            contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                candidate = self._candidate_from_contour(contour, min_area, max_area)
                if candidate is None:
                    continue

                polygon = candidate.polygon
                area = candidate.area
                confidence = candidate.confidence
                if scale < 1.0:
                    polygon = polygon / scale
                    area = area / (scale * scale)

                if self._touches_image_border(polygon, original_width, original_height):
                    continue

                candidates.append(
                    DetectedCard(polygon=polygon, area=area, confidence=confidence)
                )

        candidates = sorted(
            candidates, key=lambda candidate: candidate.area, reverse=True
        )
        deduplicated = self._remove_duplicates(candidates)
        if self._should_run_grid_fallback(deduplicated):
            deduplicated = self._remove_duplicates(
                deduplicated
                + self._recover_axis_aligned_cards_from_lines(
                    resized=resized,
                    scale=scale,
                    image_width=original_width,
                    image_height=original_height,
                    min_area=min_area,
                    max_area=max_area,
                )
            )
        return sorted(
            deduplicated[: self.max_cards],
            key=self._reading_order_key,
        )

    def _build_detection_masks(self, image: np.ndarray) -> list[np.ndarray]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        equalized = cv2.equalizeHist(gray)
        blurred = cv2.GaussianBlur(equalized, (5, 5), 0)

        edges = cv2.Canny(blurred, 35, 110)
        small_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        large_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed_edges = cv2.morphologyEx(
            edges, cv2.MORPH_CLOSE, small_kernel, iterations=1
        )
        dilated_edges = cv2.dilate(edges, small_kernel, iterations=1)

        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, otsu_inverse = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        adaptive = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            4,
        )
        adaptive_inverse = cv2.bitwise_not(adaptive)

        return [
            edges,
            closed_edges,
            dilated_edges,
            cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, large_kernel, iterations=1),
            cv2.morphologyEx(otsu_inverse, cv2.MORPH_CLOSE, large_kernel, iterations=1),
            cv2.morphologyEx(
                adaptive_inverse, cv2.MORPH_CLOSE, small_kernel, iterations=1
            ),
        ]

    def _candidate_from_contour(
        self,
        contour: np.ndarray,
        min_area: float,
        max_area: float,
    ) -> DetectedCard | None:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            return None

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            return None

        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        polygon: np.ndarray | None = None
        if len(approx) == 4 and cv2.isContourConvex(approx):
            polygon = approx.reshape(4, 2).astype(np.float32)
        else:
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect).astype(np.float32)
            rect_area = rect[1][0] * rect[1][1]
            if rect_area <= 0:
                return None
            extent = area / rect_area
            if extent >= 0.72:
                polygon = box

        if polygon is None:
            return None

        if not self._has_card_aspect_ratio(polygon):
            return None

        detection_confidence = min(
            self._angle_confidence(polygon),
            self._aspect_confidence(polygon),
        )
        if detection_confidence < 0.55:
            return None

        return DetectedCard(
            polygon=polygon,
            area=area,
            confidence=detection_confidence,
        )

    def _has_card_aspect_ratio(self, polygon: np.ndarray) -> bool:
        rect = cv2.minAreaRect(polygon.astype(np.float32))
        width, height = rect[1]
        if width == 0 or height == 0:
            return False
        ratio = min(width, height) / max(width, height)
        return 0.58 <= ratio <= 0.82

    def _aspect_confidence(self, polygon: np.ndarray) -> float:
        rect = cv2.minAreaRect(polygon.astype(np.float32))
        width, height = rect[1]
        ratio = min(width, height) / max(width, height)
        ideal_ratio = 63 / 88
        return max(0.0, 1.0 - abs(ratio - ideal_ratio) / 0.18)

    def _angle_confidence(self, polygon: np.ndarray) -> float:
        points = polygon.astype(np.float32)
        confidences: list[float] = []
        for index in range(4):
            previous_point = points[(index - 1) % 4]
            current_point = points[index]
            next_point = points[(index + 1) % 4]
            vector_a = previous_point - current_point
            vector_b = next_point - current_point
            denominator = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
            if denominator == 0:
                return 0.0
            cosine = float(np.dot(vector_a, vector_b) / denominator)
            angle = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
            confidences.append(max(0.0, 1.0 - abs(angle - 90.0) / 35.0))
        return min(confidences)

    def _touches_image_border(
        self, polygon: np.ndarray, image_width: int, image_height: int
    ) -> bool:
        margin = max(4, int(min(image_width, image_height) * 0.004))
        return bool(
            np.any(polygon[:, 0] <= margin)
            or np.any(polygon[:, 1] <= margin)
            or np.any(polygon[:, 0] >= image_width - margin)
            or np.any(polygon[:, 1] >= image_height - margin)
        )

    def _reading_order_key(self, detection: DetectedCard) -> tuple[int, int]:
        x, y, _, height = cv2.boundingRect(detection.polygon.astype(np.int32))
        row_bucket = int(y / max(height * 0.65, 1))
        return row_bucket, x

    def _remove_duplicates(self, detections: list[DetectedCard]) -> list[DetectedCard]:
        kept: list[DetectedCard] = []
        for detection in detections:
            current_box = cv2.boundingRect(detection.polygon.astype(np.int32))
            if all(
                self._intersection_over_union(
                    current_box, cv2.boundingRect(existing.polygon.astype(np.int32))
                )
                < 0.45
                for existing in kept
            ):
                kept.append(detection)
        return kept

    def _should_run_grid_fallback(self, detections: list[DetectedCard]) -> bool:
        if len(detections) < min(6, self.max_cards):
            return True
        boxes = [cv2.boundingRect(item.polygon.astype(np.int32)) for item in detections]
        widths = [box[2] for box in boxes]
        median_width = float(np.median(widths)) if widths else 0.0
        if median_width <= 0:
            return False

        rows: dict[int, list[tuple[int, int, int, int]]] = {}
        for box in boxes:
            _, y, _, height = box
            row_bucket = int(y / max(height * 0.65, 1))
            rows.setdefault(row_bucket, []).append(box)

        for row_boxes in rows.values():
            if len(row_boxes) < 2:
                continue
            sorted_boxes = sorted(row_boxes, key=lambda box: box[0])
            for left, right in pairwise(sorted_boxes):
                gap = right[0] - (left[0] + left[2])
                if gap > median_width * 0.55:
                    return True
        return False

    def _recover_axis_aligned_cards_from_lines(
        self,
        resized: np.ndarray,
        scale: float,
        image_width: int,
        image_height: int,
        min_area: float,
        max_area: float,
    ) -> list[DetectedCard]:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 35, 110)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=80,
            minLineLength=int(min(resized.shape[:2]) * 0.12),
            maxLineGap=18,
        )
        if lines is None:
            return []

        verticals: list[int] = []
        horizontals: list[int] = []
        for raw_line in lines[:, 0]:
            x1, y1, x2, y2 = raw_line
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            if dy > dx * 4:
                verticals.append(round((x1 + x2) / 2))
            elif dx > dy * 4:
                horizontals.append(round((y1 + y2) / 2))

        vertical_groups = self._group_line_positions(verticals, tolerance=14)
        horizontal_groups = self._group_line_positions(horizontals, tolerance=14)
        detections: list[DetectedCard] = []

        for left_index, left in enumerate(vertical_groups):
            for right in vertical_groups[left_index + 1 :]:
                width = right - left
                if width <= 0:
                    continue
                for top_index, top in enumerate(horizontal_groups):
                    for bottom in horizontal_groups[top_index + 1 :]:
                        height = bottom - top
                        if height <= 0:
                            continue
                        area = width * height
                        if area < min_area or area > max_area:
                            continue
                        ratio = width / height
                        if not 0.58 <= ratio <= 0.82:
                            continue

                        polygon = np.array(
                            [
                                [left, top],
                                [right, top],
                                [right, bottom],
                                [left, bottom],
                            ],
                            dtype=np.float32,
                        )
                        if scale < 1.0:
                            polygon = polygon / scale
                            area = area / (scale * scale)
                        if self._touches_image_border(
                            polygon, image_width, image_height
                        ):
                            continue
                        detections.append(
                            DetectedCard(
                                polygon=polygon,
                                area=float(area),
                                confidence=0.68,
                            )
                        )
        return detections

    def _group_line_positions(self, positions: list[int], tolerance: int) -> list[int]:
        if not positions:
            return []
        groups: list[list[int]] = []
        for position in sorted(positions):
            if not groups or abs(position - groups[-1][-1]) > tolerance:
                groups.append([position])
            else:
                groups[-1].append(position)
        return [round(float(np.median(group))) for group in groups]

    def _intersection_over_union(
        self,
        first: tuple[int, int, int, int],
        second: tuple[int, int, int, int],
    ) -> float:
        x1, y1, w1, h1 = first
        x2, y2, w2, h2 = second
        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)
        if right <= left or bottom <= top:
            return 0.0
        intersection = (right - left) * (bottom - top)
        union = w1 * h1 + w2 * h2 - intersection
        return intersection / union if union else 0.0
