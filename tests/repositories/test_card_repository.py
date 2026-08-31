from __future__ import annotations

import json

from app.repositories.card_repository import CardRepository


def test_repository_imports_and_queries_local_bulk_source(db_app, tmp_path):
    bulk_path = tmp_path / "cards.json"
    bulk_path.write_text(
        json.dumps(
            [
                {
                    "id": "scryfall-id",
                    "name": "Sol Ring",
                    "set_name": "Commander Masters",
                    "set": "cmm",
                    "collector_number": "396",
                    "image_uris": {"normal": "https://example.test/sol-ring.jpg"},
                    "scryfall_uri": "https://scryfall.com/card/cmm/396",
                    "prices": {"usd": "1.50"},
                }
            ]
        ),
        encoding="utf-8",
    )

    with db_app.app_context():
        repository = CardRepository()
        imported = repository.import_scryfall_bulk_file(bulk_path)
        exact = repository.find_by_exact_name("Sol Ring")
        candidates = repository.find_candidates_by_name("Ring", limit=5)

    assert imported == 1
    assert exact is not None
    assert exact.scryfall_id == "scryfall-id"
    assert candidates[0].name == "Sol Ring"
