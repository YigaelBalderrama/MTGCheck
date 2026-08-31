from __future__ import annotations

import gzip
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import load_only

from app.extensions import db
from app.models.card import Card
from app.utils.text_utils import card_name_variants, normalize_card_name


@dataclass(frozen=True)
class IndexedName:
    value: str
    card: Card


class CardRepository:
    def __init__(self) -> None:
        self._index_loaded = False
        self._exact_index: dict[str, Card] = {}
        self._exact_index_priority: dict[str, int] = {}
        self._trigram_index: dict[str, set[str]] = defaultdict(set)
        self._length_index: dict[int, set[str]] = defaultdict(set)
        self._indexed_names: dict[str, IndexedName] = {}

    def load_index(self, force: bool = False) -> None:
        if self._index_loaded and not force:
            return

        self._exact_index.clear()
        self._exact_index_priority.clear()
        self._trigram_index.clear()
        self._length_index.clear()
        self._indexed_names.clear()

        for card in (
            Card.query.options(
                load_only(
                    Card.scryfall_id,
                    Card.name,
                    Card.normalized_name,
                    Card.printed_name,
                    Card.normalized_printed_name,
                    Card.oracle_name,
                    Card.language,
                    Card.set_name,
                    Card.set_code,
                    Card.collector_number,
                    Card.image_url,
                    Card.scryfall_url,
                    Card.prices,
                )
            )
            .order_by(Card.language.asc(), Card.name.asc())
            .all()
        ):
            for name, priority in self._searchable_names(card).items():
                existing_priority = self._exact_index_priority.get(name)
                if existing_priority is None or priority < existing_priority:
                    self._exact_index[name] = card
                    self._exact_index_priority[name] = priority
                self._indexed_names.setdefault(name, IndexedName(value=name, card=card))
                self._length_index[len(name)].add(name)
                for trigram in self._trigrams(name):
                    self._trigram_index[trigram].add(name)

        self._index_loaded = True

    def find_by_exact_name(self, name: str) -> Card | None:
        self.load_index()
        normalized_name = normalize_card_name(name)
        return self._exact_index.get(normalized_name)

    def find_candidates_by_name(self, name: str, limit: int = 50) -> list[Card]:
        self.load_index()
        normalized_name = normalize_card_name(name)
        if not normalized_name:
            return []

        candidate_names = self._candidate_names(
            normalized_name, limit=max(limit * 4, 80)
        )
        seen_card_ids: set[str] = set()
        cards: list[Card] = []
        for candidate_name in candidate_names:
            indexed = self._indexed_names[candidate_name]
            if indexed.card.scryfall_id in seen_card_ids:
                continue
            seen_card_ids.add(indexed.card.scryfall_id)
            cards.append(indexed.card)
            if len(cards) >= limit:
                break
        return cards

    def find_by_scryfall_id(self, scryfall_id: str) -> Card | None:
        return Card.query.filter(Card.scryfall_id == scryfall_id).first()

    def list_all(self) -> list[Card]:
        self.load_index()
        seen_card_ids: set[str] = set()
        cards: list[Card] = []
        for indexed in self._indexed_names.values():
            if indexed.card.scryfall_id not in seen_card_ids:
                seen_card_ids.add(indexed.card.scryfall_id)
                cards.append(indexed.card)
        return cards

    def save_or_update(self, card: Card) -> Card:
        existing = self.find_by_scryfall_id(card.scryfall_id)
        if existing is None:
            db.session.add(card)
            db.session.commit()
            self._index_loaded = False
            return card

        self._apply_card_values(existing, card)
        db.session.commit()
        self._index_loaded = False
        return existing

    def bulk_save_or_update(self, cards: list[Card]) -> int:
        saved = 0
        for batch in self._chunks(cards, size=500):
            existing_cards = {
                card.scryfall_id: card
                for card in Card.query.filter(
                    Card.scryfall_id.in_([card.scryfall_id for card in batch])
                ).all()
            }
            for card in batch:
                existing = existing_cards.get(card.scryfall_id)
                if existing is None:
                    db.session.add(card)
                else:
                    self._apply_card_values(existing, card)
                saved += 1
            db.session.commit()
        self._index_loaded = False
        return saved

    def import_scryfall_bulk_file(self, path: str | Path) -> int:
        imported = 0
        batch: list[Card] = []
        for payload in self._iter_scryfall_payloads(Path(path)):
            card = self._card_from_scryfall_payload(payload)
            if card is None:
                continue
            batch.append(card)
            if len(batch) >= 500:
                imported += self.bulk_save_or_update(batch)
                batch = []
        if batch:
            imported += self.bulk_save_or_update(batch)
        return imported

    def _iter_scryfall_payloads(self, path: Path):
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as bulk_file:
            first_character = bulk_file.read(1)
            bulk_file.seek(0)
            if first_character == "[":
                yield from json.load(bulk_file)
                return

            for line in bulk_file:
                stripped = line.strip()
                if stripped:
                    yield json.loads(stripped)

    def _chunks(self, cards: list[Card], size: int):
        for index in range(0, len(cards), size):
            yield cards[index : index + size]

    def _candidate_names(self, normalized_name: str, limit: int) -> list[str]:
        scores: dict[str, int] = defaultdict(int)
        query_trigrams = self._trigrams(normalized_name)
        for trigram in query_trigrams:
            for indexed_name in self._trigram_index.get(trigram, set()):
                scores[indexed_name] += 3

        query_length = len(normalized_name)
        for length in range(max(1, query_length - 5), query_length + 6):
            for indexed_name in self._length_index.get(length, set()):
                scores[indexed_name] += 1

        if not scores:
            return list(self._indexed_names.keys())[:limit]

        return [
            name
            for name, _ in sorted(
                scores.items(),
                key=lambda item: (-item[1], abs(len(item[0]) - query_length), item[0]),
            )[:limit]
        ]

    def _searchable_names(self, card: Card) -> dict[str, int]:
        names: dict[str, int] = {}
        self._add_searchable_names(names, card.name, priority=0)
        self._add_searchable_names(names, card.printed_name, priority=0)
        self._add_searchable_names(names, card.normalized_name, priority=0)
        self._add_searchable_names(names, card.normalized_printed_name, priority=0)
        oracle_priority = 0 if card.language == "en" else 2
        self._add_searchable_names(names, card.oracle_name, priority=oracle_priority)
        return names

    def _add_searchable_names(
        self,
        names: dict[str, int],
        value: str | None,
        priority: int,
    ) -> None:
        for variant in card_name_variants(value):
            if not variant:
                continue
            existing_priority = names.get(variant)
            if existing_priority is None or priority < existing_priority:
                names[variant] = priority

    def _trigrams(self, value: str) -> set[str]:
        compact = f"  {value}  "
        if len(compact) <= 3:
            return {compact.strip()}
        return {compact[index : index + 3] for index in range(len(compact) - 2)}

    def _card_from_scryfall_payload(self, payload: dict) -> Card | None:
        scryfall_id = payload.get("id")
        oracle_name = payload.get("oracle_name") or payload.get("name")
        printed_name = payload.get("printed_name")
        display_name = printed_name or payload.get("name") or oracle_name
        if not scryfall_id or not display_name:
            return None

        image_uris = payload.get("image_uris") or {}
        if not image_uris and payload.get("card_faces"):
            image_uris = payload["card_faces"][0].get("image_uris") or {}

        return Card(
            scryfall_id=scryfall_id,
            name=display_name,
            normalized_name=normalize_card_name(display_name),
            printed_name=printed_name,
            normalized_printed_name=normalize_card_name(printed_name),
            oracle_name=oracle_name,
            language=payload.get("lang"),
            set_name=payload.get("set_name"),
            set_code=payload.get("set"),
            collector_number=payload.get("collector_number"),
            image_url=image_uris.get("normal") or image_uris.get("large"),
            scryfall_url=payload.get("scryfall_uri"),
            prices=payload.get("prices"),
            raw_data=None,
        )

    def _apply_card_values(self, target: Card, source: Card) -> None:
        target.name = source.name
        target.normalized_name = normalize_card_name(source.name)
        target.printed_name = source.printed_name
        target.normalized_printed_name = normalize_card_name(source.printed_name)
        target.oracle_name = source.oracle_name
        target.language = source.language
        target.set_name = source.set_name
        target.set_code = source.set_code
        target.collector_number = source.collector_number
        target.image_url = source.image_url
        target.scryfall_url = source.scryfall_url
        target.prices = source.prices
        target.raw_data = source.raw_data
