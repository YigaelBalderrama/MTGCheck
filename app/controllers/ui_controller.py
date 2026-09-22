from __future__ import annotations

from flask import Blueprint, Response, render_template

ui_blueprint = Blueprint("ui", __name__)


@ui_blueprint.get("/")
def card_scanner_page() -> Response:
    return Response(render_template("index.html"), mimetype="text/html")
