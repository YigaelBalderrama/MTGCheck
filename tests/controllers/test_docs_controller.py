from __future__ import annotations


def test_openapi_json_documents_recognition_endpoint(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["openapi"] == "3.0.3"
    assert "/api/cards/recognize" in payload["paths"]
    assert (
        payload["paths"]["/api/cards/recognize"]["post"]["requestBody"]["content"][
            "multipart/form-data"
        ]["schema"]["properties"]["image"]["format"]
        == "binary"
    )


def test_swagger_ui_serves_docs_page(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"SwaggerUIBundle" in response.data
    assert b"/openapi.json" in response.data
