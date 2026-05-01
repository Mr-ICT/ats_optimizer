"""
app/__init__.py
Flask application factory.
"""
import logging
import os
from flask import Flask
from flask_cors import CORS

from config.settings import ActiveConfig


def create_app(config=None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load config
    app.config.from_object(ActiveConfig)
    if config:
        app.config.update(config)

    # CORS for API usage
    CORS(app)

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Ensure upload folder exists
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)

    # Register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    return app
