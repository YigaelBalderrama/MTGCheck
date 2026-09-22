from __future__ import annotations

from flask import Blueprint, jsonify

health_blueprint = Blueprint("health", __name__)


@health_blueprint.get("/api")
def api_info() -> tuple:
    return (
        jsonify(
            {
                "name": "MTG Multi-Card Recognition API",
                "status": "ok",
                "endpoints": {
                    "app": "/",
                    "docs": "/docs",
                    "health": "/health",
                    "openapi": "/openapi.json",
                    "recognize_cards": "/api/cards/recognize",
                },
            }
        ),
        200,
    )


@health_blueprint.get("/health")
def health() -> tuple:
    return jsonify({"status": "ok"}), 200
