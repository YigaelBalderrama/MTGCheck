from __future__ import annotations

from pathlib import Path

import click
from flask import Flask

from app.clients.scryfall_client import ScryfallClient
from app.repositories.card_repository import CardRepository


def register_commands(app: Flask) -> None:
    @app.cli.command("update-scryfall-catalog")
    @click.option("--bulk-type", default="default_cards", show_default=True)
    def update_scryfall_catalog(bulk_type: str) -> None:
        """Download Scryfall bulk data and import it into the local SQLite cache."""
        data_dir: Path = app.config["DATA_DIR"]
        data_dir.mkdir(parents=True, exist_ok=True)

        client = ScryfallClient(
            base_url=app.config["SCRYFALL_BASE_URL"],
            timeout_seconds=app.config["SCRYFALL_TIMEOUT_SECONDS"],
            user_agent=app.config["SCRYFALL_USER_AGENT"],
            accept_header=app.config["SCRYFALL_ACCEPT"],
            min_request_interval_seconds=app.config[
                "SCRYFALL_MIN_REQUEST_INTERVAL_SECONDS"
            ],
        )
        bulk_metadata = client.get_bulk_data(bulk_type)
        download_uri = bulk_metadata["download_uri"]
        target_path = data_dir / f"scryfall-{bulk_type}.json"

        target_path.write_bytes(client.download_bulk_file(download_uri))

        imported = CardRepository().import_scryfall_bulk_file(target_path)
        click.echo(f"Imported {imported} cards into the local catalog.")
