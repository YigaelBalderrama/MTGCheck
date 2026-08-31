from __future__ import annotations

from flask import Flask
from sqlalchemy import text

from app.commands import register_commands
from app.config import get_config
from app.controllers.card_recognition_controller import create_card_blueprint
from app.controllers.docs_controller import docs_blueprint
from app.controllers.health_controller import health_blueprint
from app.exceptions.error_handlers import register_error_handlers
from app.extensions import db, limiter
from app.services.factory import create_card_recognition_service


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        db.create_all()
        _ensure_card_schema()
        card_recognition_service = create_card_recognition_service(app.config)

    app.register_blueprint(
        create_card_blueprint(
            card_recognition_service,
            rate_limit=app.config.get("RATELIMIT_DEFAULT", "60 per minute"),
        )
    )
    app.register_blueprint(health_blueprint)
    app.register_blueprint(docs_blueprint)
    register_error_handlers(app)
    register_commands(app)

    return app


def _ensure_card_schema() -> None:
    if db.engine.dialect.name != "sqlite":
        return

    existing_columns = {
        row[1] for row in db.session.execute(text("PRAGMA table_info(cards)")).fetchall()
    }
    column_definitions = {
        "printed_name": "VARCHAR(255)",
        "normalized_printed_name": "VARCHAR(255)",
        "oracle_name": "VARCHAR(255)",
        "language": "VARCHAR(8)",
    }
    for column_name, column_type in column_definitions.items():
        if column_name not in existing_columns:
            db.session.execute(
                text(f"ALTER TABLE cards ADD COLUMN {column_name} {column_type}")
            )
    db.session.commit()
