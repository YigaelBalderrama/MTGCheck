from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.exceptions.recognition_exception import RecognitionException


def validate_image_bytes(
    image_bytes: bytes,
    content_type: str | None,
    allowed_mime_types: Iterable[str],
    allowed_formats: Iterable[str],
    max_size_bytes: int,
) -> Image.Image:
    if not image_bytes:
        raise RecognitionException(
            code="INVALID_IMAGE",
            message="El archivo enviado está vacío o no es una imagen válida.",
            status_code=400,
        )

    if len(image_bytes) > max_size_bytes:
        raise RecognitionException(
            code="IMAGE_TOO_LARGE",
            message="La imagen excede el tamaño máximo permitido.",
            status_code=413,
        )

    if content_type not in set(allowed_mime_types):
        raise RecognitionException(
            code="UNSUPPORTED_IMAGE_TYPE",
            message="Solo se aceptan imágenes JPG, JPEG, PNG o WebP.",
            status_code=415,
        )

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
        image = Image.open(BytesIO(image_bytes))
        if image.format not in set(allowed_formats):
            raise RecognitionException(
                code="UNSUPPORTED_IMAGE_TYPE",
                message="Solo se aceptan imágenes JPG, JPEG, PNG o WebP.",
                status_code=415,
            )
        return ImageOps.exif_transpose(image).convert("RGB")
    except UnidentifiedImageError as exc:
        raise RecognitionException(
            code="INVALID_IMAGE",
            message="El archivo enviado no es una imagen válida.",
            status_code=400,
        ) from exc
    except OSError as exc:
        raise RecognitionException(
            code="INVALID_IMAGE",
            message="El archivo enviado no es una imagen válida.",
            status_code=400,
        ) from exc


def pil_to_cv2(image: Image.Image) -> np.ndarray:
    rgb = np.array(image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def preprocess_name_region(card_image: np.ndarray) -> np.ndarray:
    height, width = card_image.shape[:2]
    y1 = max(0, int(height * 0.035))
    y2 = min(height, int(height * 0.18))
    x1 = max(0, int(width * 0.055))
    x2 = min(width, int(width * 0.945))
    region = card_image[y1:y2, x1:x2]

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 5, 50, 50)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, sharpen_kernel)
    return cv2.equalizeHist(sharpened)
