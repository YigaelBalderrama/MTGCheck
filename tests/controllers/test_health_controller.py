from __future__ import annotations


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_api_info(client):
    response = client.get("/api")

    assert response.status_code == 200
    assert response.get_json()["endpoints"]["recognize_cards"] == "/api/cards/recognize"


def test_home_serves_card_scanner_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"Magic Card Scanner" in response.data
    assert b"/api/cards/recognize" in response.data
