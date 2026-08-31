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
