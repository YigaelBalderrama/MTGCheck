from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.models.card import Card
from app.repositories.card_repository import CardRepository
from app.utils.text_utils import card_name_variants, normalize_card_name


@dataclass(frozen=True)
class MatchResult:
    card: Card | None
    final_confidence: float
    name_match_confidence: float = 0.0
    source: str | None = None

    @property
    def confidence(self) -> float:
        return self.final_confidence


class CardMatchingService:
    def __init__(
        self,
        repository: CardRepository,
        threshold: float = 0.72,
    ) -> None:
        self.repository = repository
        self.threshold = threshold

    def match(self, detected_text: str, ocr_confidence: float) -> MatchResult:
        normalized_text = normalize_card_name(detected_text)
        if not normalized_text:
            return MatchResult(card=None, final_confidence=0.0)

        exact = self._find_exact_variant(normalized_text)
        if exact is not None:
            return MatchResult(
                card=exact,
                final_confidence=self._combine_confidence(1.0, ocr_confidence),
                name_match_confidence=1.0,
                source="local_exact",
            )

        fuzzy = self._find_fuzzy_local(normalized_text, ocr_confidence)
        return (
            fuzzy
            if fuzzy.card is not None
            else MatchResult(card=None, final_confidence=0.0)
        )

    def _find_exact_variant(self, normalized_text: str) -> Card | None:
        for variant in card_name_variants(normalized_text):
            card = self.repository.find_by_exact_name(variant)
            if card is not None:
                return card
        return None

    def _find_fuzzy_local(
        self, normalized_text: str, ocr_confidence: float
    ) -> MatchResult:
        cards = self.repository.find_candidates_by_name(normalized_text, limit=25)
        if not cards:
            cards = self.repository.list_all()
        choices: dict[str, Card] = {}
        for card in cards:
            choices[card.normalized_name] = card
            for variant in card_name_variants(card.name):
                choices.setdefault(variant, card)

        match = process.extractOne(
            normalized_text,
            choices.keys(),
            scorer=fuzz.WRatio,
        )
        if match is None:
            return MatchResult(card=None, final_confidence=0.0)

        matched_name, score, _ = match
        name_match_confidence = score / 100.0
        confidence = self._combine_confidence(name_match_confidence, ocr_confidence)
        return MatchResult(
            card=choices[matched_name],
            final_confidence=confidence,
            name_match_confidence=name_match_confidence,
            source="local_fuzzy",
        )

    def _combine_confidence(
        self, match_confidence: float, ocr_confidence: float
    ) -> float:
        ocr_component = max(0.0, min(1.0, ocr_confidence))
        match_component = max(0.0, min(1.0, match_confidence))
        return (match_component * 0.75) + (ocr_component * 0.25)
