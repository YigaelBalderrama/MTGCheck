from __future__ import annotations

import gzip
import json

from app.repositories.card_repository import CardRepository


def test_repository_imports_and_queries_local_bulk_source(db_app, tmp_path):
    bulk_path = tmp_path / "cards.json"
    bulk_path.write_text(
        json.dumps(
            [
                {
                    "id": "scryfall-id",
                    "name": "Incinerate",
                    "printed_name": "Incinerar",
                    "oracle_name": "Incinerate",
                    "lang": "es",
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
        exact = repository.find_by_exact_name("Incinerar")
        oracle = repository.find_by_exact_name("Incinerate")
        candidates = repository.find_candidates_by_name("Incinerar", limit=5)

    assert imported == 1
    assert exact is not None
    assert exact.scryfall_id == "scryfall-id"
    assert exact.oracle_name == "Incinerate"
    assert exact.language == "es"
    assert oracle is not None
    assert candidates[0].printed_name == "Incinerar"


def test_repository_does_not_use_network_for_lookup(db_app, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("Repository lookup must not use HTTP")

    monkeypatch.setattr("requests.sessions.Session.request", fail_network)

    with db_app.app_context():
        repository = CardRepository()
        assert repository.find_candidates_by_name("Unknown", limit=5) == []


def test_repository_imports_jsonl_gzip_bulk_source(db_app, tmp_path):
    bulk_path = tmp_path / "cards.jsonl.gz"
    payload = {
        "id": "spanish-id",
        "name": "Feed the Swarm",
        "printed_name": "Alimentar el enjambre",
        "oracle_name": "Feed the Swarm",
        "lang": "es",
        "set": "znr",
        "set_name": "Zendikar Rising",
        "collector_number": "102",
        "image_uris": {"normal": "https://example.test/feed.jpg"},
        "prices": {"usd": "0.20"},
    }
    with gzip.open(bulk_path, "wt", encoding="utf-8") as bulk_file:
        bulk_file.write(json.dumps(payload) + "\n")

    with db_app.app_context():
        repository = CardRepository()
        imported = repository.import_scryfall_bulk_file(bulk_path)
        card = repository.find_by_exact_name("Alimentar el enjambre")

    assert imported == 1
    assert card is not None
    assert card.oracle_name == "Feed the Swarm"


def test_repository_prefers_english_card_for_oracle_name_exact_match(db_app):
    from app.models.card import Card
    from app.utils.text_utils import normalize_card_name

    with db_app.app_context():
        repository = CardRepository()
        repository.bulk_save_or_update(
            [
                Card(
                    scryfall_id="es-feed",
                    name="Alimentar al enjambre",
                    normalized_name=normalize_card_name("Alimentar al enjambre"),
                    printed_name="Alimentar al enjambre",
                    normalized_printed_name=normalize_card_name(
                        "Alimentar al enjambre"
                    ),
                    oracle_name="Feed the Swarm",
                    language="es",
                ),
                Card(
                    scryfall_id="en-feed",
                    name="Feed the Swarm",
                    normalized_name=normalize_card_name("Feed the Swarm"),
                    printed_name=None,
                    normalized_printed_name="",
                    oracle_name="Feed the Swarm",
                    language="en",
                ),
            ]
        )

        english = repository.find_by_exact_name("Feed the Swarm")
        spanish = repository.find_by_exact_name("Alimentar al enjambre")

    assert english is not None
    assert english.scryfall_id == "en-feed"
    assert spanish is not None
    assert spanish.scryfall_id == "es-feed"
