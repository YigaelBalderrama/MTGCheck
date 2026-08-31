from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

from app.exceptions.recognition_exception import RecognitionException
from app.models.card import Card
from app.utils.text_utils import normalize_card_name


class ScryfallClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        user_agent: str,
        accept_header: str,
        min_request_interval_seconds: float = 0.1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.min_request_interval_seconds = min_request_interval_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": accept_header,
            }
        )
        self._last_request_at = 0.0
        self._named_cache: dict[str, Card | None] = {}

    def find_named_card(self, name: str) -> Card | None:
        normalized_name = normalize_card_name(name)
        if not normalized_name:
            return None
        if normalized_name in self._named_cache:
            return self._named_cache[normalized_name]

        payload = self._get("/cards/named", params={"fuzzy": name})
        if payload is None:
            self._named_cache[normalized_name] = None
            return None

        card = self._card_from_payload(payload)
        self._named_cache[normalized_name] = card
        return card

    def get_bulk_data(self, bulk_type: str = "all_cards") -> dict[str, Any]:
        payload = self._get("/bulk-data", params=None)
        if payload is None or "data" not in payload:
            raise RecognitionException(
                code="SCRYFALL_UNAVAILABLE",
                message="Scryfall no esta disponible temporalmente.",
                status_code=503,
            )

        for bulk_data in payload["data"]:
            if bulk_data.get("type") == bulk_type:
                return bulk_data

        raise RecognitionException(
            code="SCRYFALL_UNAVAILABLE",
            message=f"No se encontro el bulk '{bulk_type}' en Scryfall.",
            status_code=503,
        )

    def download_bulk_file(self, download_uri: str) -> bytes:
        self._respect_rate_limit()
        try:
            response = self.session.get(download_uri, timeout=self.timeout_seconds * 6)
        except requests.RequestException as exc:
            raise RecognitionException(
                code="SCRYFALL_UNAVAILABLE",
                message="Scryfall no esta disponible temporalmente.",
                status_code=503,
            ) from exc

        self._raise_for_external_error(response)
        return response.content

    def download_bulk_file_to_path(self, download_uri: str, target_path: Path) -> None:
        self._respect_rate_limit()
        try:
            with self.session.get(
                download_uri,
                timeout=self.timeout_seconds * 12,
                stream=True,
            ) as response:
                self._raise_for_external_error(response)
                with target_path.open("wb") as target_file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            target_file.write(chunk)
        except requests.RequestException as exc:
            raise RecognitionException(
                code="SCRYFALL_UNAVAILABLE",
                message="Scryfall no esta disponible temporalmente.",
                status_code=503,
            ) from exc

    def _get(self, path: str, params: dict[str, Any] | None) -> dict[str, Any] | None:
        self._respect_rate_limit()
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise RecognitionException(
                code="SCRYFALL_UNAVAILABLE",
                message="Scryfall no esta disponible temporalmente.",
                status_code=503,
            ) from exc

        if response.status_code == 404:
            return None
        self._raise_for_external_error(response)
        return response.json()

    def _raise_for_external_error(self, response: requests.Response) -> None:
        if response.status_code == 429:
            raise RecognitionException(
                code="RATE_LIMIT_EXCEEDED",
                message="Scryfall rechazo temporalmente las solicitudes por limite de frecuencia.",
                status_code=429,
            )
        if response.status_code >= 500:
            raise RecognitionException(
                code="SCRYFALL_UNAVAILABLE",
                message="Scryfall no esta disponible temporalmente.",
                status_code=503,
            )
        response.raise_for_status()

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_request_interval_seconds:
            time.sleep(self.min_request_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()

    def _card_from_payload(self, payload: dict[str, Any]) -> Card:
        image_uris = payload.get("image_uris") or {}
        if not image_uris and payload.get("card_faces"):
            image_uris = payload["card_faces"][0].get("image_uris") or {}

        display_name = payload.get("printed_name") or payload["name"]
        return Card(
            scryfall_id=payload["id"],
            name=display_name,
            normalized_name=normalize_card_name(display_name),
            printed_name=payload.get("printed_name"),
            normalized_printed_name=normalize_card_name(payload.get("printed_name")),
            oracle_name=payload.get("oracle_name") or payload["name"],
            language=payload.get("lang"),
            set_name=payload.get("set_name"),
            set_code=payload.get("set"),
            collector_number=payload.get("collector_number"),
            image_url=image_uris.get("normal") or image_uris.get("large"),
            scryfall_url=payload.get("scryfall_uri"),
            prices=payload.get("prices"),
            raw_data=None,
        )
