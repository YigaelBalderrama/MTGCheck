from __future__ import annotations

import cv2
import numpy as np


class PerspectiveService:
    def __init__(self, output_width: int = 448, output_height: int = 624) -> None:
        self.output_width = output_width
        self.output_height = output_height

    def order_points(self, points: np.ndarray) -> np.ndarray:
        pts = np.asarray(points, dtype=np.float32)
        ordered = np.zeros((4, 2), dtype=np.float32)

        sums = pts.sum(axis=1)
        differences = np.diff(pts, axis=1)

        ordered[0] = pts[np.argmin(sums)]
        ordered[2] = pts[np.argmax(sums)]
        ordered[1] = pts[np.argmin(differences)]
        ordered[3] = pts[np.argmax(differences)]
        return ordered

    def warp_card(self, image: np.ndarray, points: np.ndarray) -> np.ndarray:
        ordered = self.order_points(points)
        destination = np.array(
            [
                [0, 0],
                [self.output_width - 1, 0],
                [self.output_width - 1, self.output_height - 1],
                [0, self.output_height - 1],
            ],
            dtype=np.float32,
        )
        matrix = cv2.getPerspectiveTransform(ordered, destination)
        return cv2.warpPerspective(
            image, matrix, (self.output_width, self.output_height)
        )

    def orientation_candidates(self, image: np.ndarray) -> list[np.ndarray]:
        return [
            image,
            cv2.rotate(image, cv2.ROTATE_180),
        ]
