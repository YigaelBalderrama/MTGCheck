from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.extensions import db


class Card(db.Model):
    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    scryfall_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    normalized_name = db.Column(db.String(255), nullable=False, index=True)
    printed_name = db.Column(db.String(255), nullable=True, index=True)
    normalized_printed_name = db.Column(db.String(255), nullable=True, index=True)
    oracle_name = db.Column(db.String(255), nullable=True, index=True)
    language = db.Column(db.String(8), nullable=True, index=True)
    set_name = db.Column(db.String(255), nullable=True)
    set_code = db.Column(db.String(16), nullable=True)
    collector_number = db.Column(db.String(64), nullable=True)
    image_url = db.Column(db.String(1024), nullable=True)
    scryfall_url = db.Column(db.String(1024), nullable=True)
    prices = db.Column(db.JSON, nullable=True)
    raw_data = db.Column(db.JSON, nullable=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def to_match_payload(self) -> dict[str, Any]:
        oracle_name = self.oracle_name or self.name
        printed_name = self.printed_name or self.name
        return {
            "scryfall_id": self.scryfall_id,
            "name": printed_name,
            "printed_name": printed_name,
            "oracle_name": oracle_name,
            "language": self.language,
            "set_name": self.set_name,
            "set_code": self.set_code,
            "collector_number": self.collector_number,
            "image_url": self.image_url,
            "scryfall_url": self.scryfall_url,
            "prices": self.prices,
        }
