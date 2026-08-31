from __future__ import annotations

import pytest

from app.models.card import Card
from app.services.card_matching_service import CardMatchingService
from app.utils.text_utils import card_name_variants, normalize_card_name


class InMemoryCardRepository:
    def __init__(self, cards: list[Card]) -> None:
        self.cards = cards
        self.saved: list[Card] = []

    def find_by_exact_name(self, name: str) -> Card | None:
        normalized = normalize_card_name(name)
        return next(
            (card for card in self.cards if card.normalized_name == normalized),
            None,
        )

    def find_candidates_by_name(self, name: str, limit: int = 5) -> list[Card]:
        return self.cards[:limit]

    def list_all(self) -> list[Card]:
        return self.cards

    def save_or_update(self, card: Card) -> Card:
        self.saved.append(card)
        return card


def make_card(
    name: str,
    printed_name: str | None = None,
    oracle_name: str | None = None,
    language: str = "en",
) -> Card:
    return Card(
        scryfall_id=f"id-{normalize_card_name(name)}",
        name=name,
        normalized_name=normalize_card_name(name),
        printed_name=printed_name,
        normalized_printed_name=normalize_card_name(printed_name),
        oracle_name=oracle_name or name,
        language=language,
        set_name="Test Set",
        set_code="tst",
        collector_number="1",
        image_url="https://example.test/image.jpg",
        scryfall_url="https://scryfall.com/card/test",
        prices={"usd": "1.00"},
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Ajani’s Pridemate  ", "ajani's pridemate"),
        (
            "Fable of the Mirror-Breaker // Reflection of Kiki-Jiki",
            "fable of the mirror-breaker // reflection of kiki-jiki",
        ),
        ("Café", "cafe"),
    ],
)
def test_normalize_card_name(raw, expected):
    assert normalize_card_name(raw) == expected


def test_card_name_variants_handles_double_faced_cards():
    variants = card_name_variants("Fire // Ice")

    assert variants == ["fire", "fire // ice", "ice"]


def test_exact_match_returns_card():
    card = make_card("Sol Ring")
    service = CardMatchingService(
        repository=InMemoryCardRepository([card]),
        threshold=0.72,
    )

    result = service.match("Sol Ring", ocr_confidence=0.95)

    assert result.card == card
    assert result.confidence >= 0.9


def test_fuzzy_match_returns_card_above_threshold():
    card = make_card("Llanowar Elves")
    service = CardMatchingService(
        repository=InMemoryCardRepository([card]),
        threshold=0.72,
    )

    result = service.match("Llanowar Elvs", ocr_confidence=0.9)

    assert result.card == card
    assert result.confidence >= 0.72


def test_match_below_threshold_is_not_accepted_by_caller_contract():
    card = make_card("Black Lotus")
    service = CardMatchingService(
        repository=InMemoryCardRepository([card]),
        threshold=0.95,
    )

    result = service.match("Llanowar", ocr_confidence=0.4)

    assert result.confidence < 0.95


def test_spanish_printed_name_matches_local_index():
    card = make_card(
        name="Incinerar",
        printed_name="Incinerar",
        oracle_name="Incinerate",
        language="es",
    )
    service = CardMatchingService(
        repository=InMemoryCardRepository([card]),
        threshold=0.72,
    )

    result = service.match("Incinerar", ocr_confidence=0.95)

    assert result.card == card
    assert result.card.oracle_name == "Incinerate"
    assert result.card.language == "es"


def test_repository_local_miss_does_not_call_remote_or_invent_card():
    service = CardMatchingService(
        repository=InMemoryCardRepository([]),
        threshold=0.72,
    )

    result = service.match("Unknown Card", ocr_confidence=0.9)

    assert result.card is None
    assert result.confidence == 0.0
