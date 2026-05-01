"""
app/routes/main.py
Flask routes:
  GET  /              — Main UI
  POST /analyze       — Upload resume + JD, run full pipeline
  GET  /health        — Health check
  GET  /api/config    — Expose scoring weights (for transparency)
"""
import os
import uuid
import logging
from pathlib import Path

from flask import (
    Blueprint, request, jsonify, render_template,
    current_app, flash, redirect, url_for
)
from werkzeug.utils import secure_filename

from app.services.analyzer_service import analyze_resume

logger = logging.getLogger(__name__)
main_bp = Blueprint("main", __name__)


def _allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"pdf", "docx"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _save_upload(file) -> str:
    """Save uploaded file with a UUID prefix to avoid collisions."""
    filename = secure_filename(file.filename)
    ext = Path(filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)
    return file_path


def _cleanup(file_path: str):
    """Remove uploaded file after processing."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Could not delete temp file {file_path}: {e}")


# ─── Routes ─────────────────────────────────────────────────────────────────

@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    POST /analyze
    Form fields:
      - resume:  file (PDF or DOCX)
      - job_description: text
    Returns JSON result.
    """
    # Validate file
    if "resume" not in request.files:
        return jsonify({"error": "No resume file provided"}), 400

    file = request.files["resume"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Upload PDF or DOCX only."}), 400

    # Validate JD
    job_description = request.form.get("job_description", "").strip()
    if len(job_description) < 50:
        return jsonify({"error": "Job description too short (minimum 50 characters)"}), 400

    file_path = None
    try:
        file_path = _save_upload(file)
        logger.info(f"Analyzing: {file.filename} | JD length: {len(job_description)}")

        result = analyze_resume(file_path, job_description)

        if "error" in result:
            return jsonify(result), 422

        return jsonify(result), 200

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.exception(f"Analysis failed: {e}")
        print(f"\n{'='*60}\nANALYSIS ERROR:\n{tb}\n{'='*60}\n")
        return jsonify({"error": f"Analysis failed: {str(e)}", "traceback": tb}), 500

    finally:
        _cleanup(file_path)


@main_bp.route("/health")
def health():
    """Health check — also reports which models are loaded."""
    from app.services.nlp_service import get_spacy, get_encoder
    return jsonify({
        "status": "ok",
        "spacy_loaded": get_spacy() is not None,
        "encoder_loaded": get_encoder() is not None,
        "groq_configured": bool(current_app.config.get("GROQ_API_KEY")),
    })


@main_bp.route("/api/config")
def api_config():
    """Expose scoring weights so clients understand the scoring model."""
    from config.settings import ActiveConfig as cfg
    return jsonify({
        "scoring_weights": cfg.WEIGHTS,
        "models": {
            "spacy": cfg.SPACY_MODEL,
            "sentence_transformer": cfg.SENTENCE_TRANSFORMER_MODEL,
            "llm": cfg.GROQ_MODEL,
        },
        "keyword_extraction": {
            "method": "YAKE",
            "top_n": cfg.YAKE_TOP_N_KEYWORDS,
            "max_ngram": cfg.YAKE_MAX_NGRAM_SIZE,
        },
    })
