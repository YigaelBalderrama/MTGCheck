from __future__ import annotations

from app.clients.scryfall_client import ScryfallClient


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_get_bulk_data_fetches_list_and_selects_by_type(monkeypatch):
    client = ScryfallClient(
        base_url="https://api.scryfall.com",
        timeout_seconds=1,
        user_agent="test",
        accept_header="application/json",
        min_request_interval_seconds=0,
    )

    def fake_get(url, params=None, timeout=None):
        assert url == "https://api.scryfall.com/bulk-data"
        return FakeResponse(
            {
                "data": [
                    {"type": "default_cards", "download_uri": "default.json"},
                    {"type": "all_cards", "jsonl_download_uri": "all.jsonl.gz"},
                ]
            }
        )

    monkeypatch.setattr(client.session, "get", fake_get)

    bulk = client.get_bulk_data("all_cards")

    assert bulk["jsonl_download_uri"] == "all.jsonl.gz"
