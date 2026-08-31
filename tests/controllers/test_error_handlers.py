from __future__ import annotations


def test_not_found_returns_json_error(client):
    response = client.get("/missing-route")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"
