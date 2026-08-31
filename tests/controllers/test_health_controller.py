from __future__ import annotations


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_api_info(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json()["endpoints"]["recognize_cards"] == "/api/cards/recognize"
