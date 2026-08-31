from __future__ import annotations

import re
import unicodedata

_REPLACEMENTS = {
    "’": "'",
    "`": "'",
    "´": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "／": "//",
}


def normalize_card_name(value: str | None) -> str:
    if not value:
        return ""

    text = value.strip()
    for source, replacement in _REPLACEMENTS.items():
        text = text.replace(source, replacement)

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character for character in text if not unicodedata.combining(character)
    )
    text = text.lower()
    text = re.sub(r"[^a-z0-9/' -]+", " ", text)
    text = re.sub(r"\s*//\s*", " // ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def card_name_variants(value: str | None) -> list[str]:
    normalized = normalize_card_name(value)
    if not normalized:
        return []
    variants = {normalized}
    if " // " in normalized:
        variants.update(
            part.strip() for part in normalized.split(" // ") if part.strip()
        )
    return sorted(variants)
