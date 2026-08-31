from __future__ import annotations

from flask import Blueprint, Response, jsonify, render_template_string

from app.docs.openapi_spec import OPENAPI_SPEC

docs_blueprint = Blueprint("docs", __name__)


@docs_blueprint.get("/openapi.json")
def openapi_json() -> tuple:
    return jsonify(OPENAPI_SPEC), 200


@docs_blueprint.get("/docs")
def swagger_ui() -> Response:
    return Response(
        render_template_string("""
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>MTG Multi-Card Recognition API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: "/openapi.json",
          dom_id: "#swagger-ui"
        });
      };
    </script>
  </body>
</html>
            """.strip()),
        mimetype="text/html",
    )
