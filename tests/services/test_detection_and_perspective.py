from __future__ import annotations

import cv2
import numpy as np

from app.services.card_detection_service import CardDetectionService
from app.services.perspective_service import PerspectiveService


def test_detection_returns_no_cards_for_blank_image():
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    detections = CardDetectionService().detect_cards(image)

    assert detections == []


def test_detection_finds_multiple_cards_in_synthetic_image():
    image = np.zeros((900, 1200, 3), dtype=np.uint8)
    first = np.array([[80, 80], [380, 105], [350, 525], [55, 500]], dtype=np.int32)
    second = np.array([[520, 130], [830, 90], [890, 535], [575, 575]], dtype=np.int32)
    cv2.fillPoly(image, [first, second], (245, 245, 245))
    cv2.polylines(image, [first, second], True, (20, 20, 20), 8)

    detections = CardDetectionService().detect_cards(image)

    assert len(detections) >= 2


def test_detection_separates_adjacent_cards_in_same_photo():
    image = np.full((900, 1300, 3), 35, dtype=np.uint8)
    cards = [
        np.array([[70, 80], [345, 75], [350, 470], [75, 480]], dtype=np.int32),
        np.array([[385, 82], [660, 78], [665, 475], [390, 478]], dtype=np.int32),
        np.array([[705, 80], [980, 86], [970, 482], [700, 472]], dtype=np.int32),
    ]
    for card in cards:
        cv2.fillPoly(image, [card], (235, 235, 235))
        cv2.polylines(image, [card], True, (5, 5, 5), 10)

    detections = CardDetectionService(max_cards=10).detect_cards(image)

    assert len(detections) >= 3


def test_order_points_returns_top_left_top_right_bottom_right_bottom_left():
    points = np.array([[100, 300], [100, 100], [300, 100], [300, 300]], dtype=float)
    ordered = PerspectiveService().order_points(points)

    assert ordered.tolist() == [
        [100.0, 100.0],
        [300.0, 100.0],
        [300.0, 300.0],
        [100.0, 300.0],
    ]


def test_warp_card_returns_normalized_card_ratio():
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    points = np.array([[100, 80], [350, 100], [330, 450], [80, 430]], dtype=float)

    warped = PerspectiveService(output_width=630, output_height=880).warp_card(
        image, points
    )

    assert warped.shape == (880, 630, 3)
