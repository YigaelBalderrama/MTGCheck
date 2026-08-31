from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.exceptions.recognition_exception import RecognitionException
from app.extensions import limiter
from app.services.card_recognition_service import CardRecognitionService


def create_card_blueprint(
    card_recognition_service: CardRecognitionService,
    rate_limit: str = "60 per minute",
) -> Blueprint:
    card_blueprint = Blueprint("card_recognition", __name__)

    @card_blueprint.post("/api/cards/recognize")
    @limiter.limit(rate_limit)
    def recognize_cards() -> tuple:
        uploaded_image = request.files.get("image")
        if uploaded_image is None:
            raise RecognitionException(
                code="MISSING_IMAGE",
                message="Debe enviar una imagen en el campo 'image'.",
                status_code=400,
            )

        if not uploaded_image.filename:
            raise RecognitionException(
                code="MISSING_IMAGE",
                message="El campo 'image' no contiene un archivo.",
                status_code=400,
            )

        image_bytes = uploaded_image.read()
        result = card_recognition_service.recognize(
            image_bytes=image_bytes,
            content_type=uploaded_image.mimetype,
        )
        return jsonify(result.to_dict()), 200

    return card_blueprint
