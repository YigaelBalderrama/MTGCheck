from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np

from app.services.ocr_service import OcrService


def test_ocr_reader_is_initialized_once(monkeypatch):
    created = []

    class FakeReader:
        def __init__(self, languages, gpu=False):
            created.append((languages, gpu))

        def readtext(self, image, **kwargs):
            return [([[0, 0], [1, 0], [1, 1], [0, 1]], "Sol Ring", 0.92)]

    monkeypatch.setitem(sys.modules, "easyocr", SimpleNamespace(Reader=FakeReader))
    service = OcrService(languages=["en", "es"], gpu=False)

    first = service.extract_text(np.zeros((40, 200), dtype=np.uint8))
    second = service.extract_text(np.zeros((40, 200), dtype=np.uint8))

    assert first.text == "Sol Ring"
    assert second.text == "Sol Ring"
    assert created == [(["en", "es"], False)]


def test_ocr_batch_groups_images_by_shape(monkeypatch):
    batched_shapes = []

    class FakeReader:
        def __init__(self, languages, gpu=False):
            pass

        def readtext_batched(self, images, **kwargs):
            shapes = {image.shape for image in images}
            if len(shapes) != 1:
                raise ValueError("ragged batch")
            batched_shapes.append(tuple(images[0].shape))
            return [
                (
                    [
                        (
                            [[0, 0], [1, 0], [1, 1], [0, 1]],
                            f"text-{image.shape[0]}",
                            0.9,
                        )
                    ]
                )
                for image in images
            ]

        def readtext(self, image, **kwargs):
            return [([[0, 0], [1, 0], [1, 1], [0, 1]], "fallback", 0.5)]

    monkeypatch.setitem(sys.modules, "easyocr", SimpleNamespace(Reader=FakeReader))
    service = OcrService()

    results = service.extract_batch(
        [
            np.zeros((40, 200), dtype=np.uint8),
            np.zeros((60, 200), dtype=np.uint8),
            np.zeros((40, 200), dtype=np.uint8),
        ]
    )

    assert [result.text for result in results] == ["text-40", "text-60", "text-40"]
    assert sorted(batched_shapes) == [(40, 200), (60, 200)]
