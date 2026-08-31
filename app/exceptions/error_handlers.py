from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import (
    HTTPException,
    NotFound,
    RequestEntityTooLarge,
    TooManyRequests,
)

from app.exceptions.recognition_exception import RecognitionException


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(RecognitionException)
    def handle_recognition_exception(error: RecognitionException) -> tuple:
        return jsonify({"error": {"code": error.code, "message": error.message}}), (
            error.status_code
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(_: RequestEntityTooLarge) -> tuple:
        return (
            jsonify(
                {
                    "error": {
                        "code": "IMAGE_TOO_LARGE",
                        "message": "La imagen excede el tamano maximo permitido.",
                    }
                }
            ),
            413,
        )

    @app.errorhandler(TooManyRequests)
    def handle_rate_limit(_: TooManyRequests) -> tuple:
        return (
            jsonify(
                {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Demasiadas solicitudes. Intente nuevamente mas tarde.",
                    }
                }
            ),
            429,
        )

    @app.errorhandler(NotFound)
    def handle_not_found(_: NotFound) -> tuple:
        return (
            jsonify(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "La ruta solicitada no existe.",
                    }
                }
            ),
            404,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple:
        return (
            jsonify(
                {
                    "error": {
                        "code": error.name.upper().replace(" ", "_"),
                        "message": error.description,
                    }
                }
            ),
            error.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple:
        app.logger.exception("Unhandled recognition API error")
        return (
            jsonify(
                {
                    "error": {
                        "code": "RECOGNITION_ERROR",
                        "message": "Ocurrio un error interno durante el reconocimiento.",
                    }
                }
            ),
            500,
        )
