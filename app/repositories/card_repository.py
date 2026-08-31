from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

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
        self._trigram_index: dict[str, set[str]] = defaultdict(set)
        self._length_index: dict[int, set[str]] = defaultdict(set)
        self._indexed_names: dict[str, IndexedName] = {}

    def load_index(self, force: bool = False) -> None:
        if self._index_loaded and not force:
            return

        self._exact_index.clear()
        self._trigram_index.clear()
        self._length_index.clear()
        self._indexed_names.clear()

        for card in Card.query.order_by(Card.name.asc()).all():
            for name in self._searchable_names(card):
                self._exact_index.setdefault(name, card)
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
        for card in cards:
            existing = self.find_by_scryfall_id(card.scryfall_id)
            if existing is None:
                db.session.add(card)
            else:
                self._apply_card_values(existing, card)
            saved += 1
        db.session.commit()
        self._index_loaded = False
        return saved

    def import_scryfall_bulk_file(self, path: str | Path) -> int:
        bulk_path = Path(path)
        with bulk_path.open("r", encoding="utf-8") as bulk_file:
            payload = json.load(bulk_file)

        cards = [
            card
            for item in payload
            if (card := self._card_from_scryfall_payload(item)) is not None
        ]
        return self.bulk_save_or_update(cards)

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

    def _searchable_names(self, card: Card) -> set[str]:
        names: set[str] = set()
        for value in {
            card.name,
            card.printed_name,
            card.oracle_name,
            card.normalized_name,
            card.normalized_printed_name,
        }:
            names.update(card_name_variants(value))
        return {name for name in names if name}

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
            raw_data=payload,
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
