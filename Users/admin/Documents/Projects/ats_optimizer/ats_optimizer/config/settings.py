"""
config/settings.py
Central configuration for ATS Optimizer.
All tunable weights and constants live here.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS = {"pdf", "docx"}

    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

    # ─── ATS Scoring Weights (must sum to 1.0) ───────────────────────────────
    WEIGHTS = {
        "semantic_similarity": 0.40,
        "keyword_match":       0.30,
        "formatting":          0.15,
        "content_quality":     0.15,
    }

    # ─── NLP Models ──────────────────────────────────────────────────────────
    SPACY_MODEL = "en_core_web_sm"
    SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"

    # ─── YAKE Keyword Extraction ─────────────────────────────────────────────
    YAKE_LANGUAGE = "en"
    YAKE_MAX_NGRAM_SIZE = 3
    YAKE_DEDUP_THRESHOLD = 0.9
    YAKE_TOP_N_KEYWORDS = 40

    # ─── Keyword Matching ────────────────────────────────────────────────────
    # Fuzzy-style: how many chars can differ for a "soft" match
    KEYWORD_SOFT_MATCH_RATIO = 0.85

    # ─── Content Quality ─────────────────────────────────────────────────────
    ACTION_VERBS = {
        "led", "managed", "built", "developed", "designed", "implemented",
        "launched", "delivered", "improved", "increased", "reduced",
        "optimized", "created", "established", "coordinated", "analyzed",
        "architected", "automated", "accelerated", "achieved", "streamlined",
        "transformed", "spearheaded", "orchestrated", "engineered", "drove",
        "executed", "generated", "negotiated", "collaborated", "mentored",
    }

    # ─── Structure Sections ──────────────────────────────────────────────────
    REQUIRED_SECTIONS = ["experience", "education", "skills"]
    OPTIONAL_SECTIONS = ["summary", "objective", "projects", "certifications",
                         "awards", "publications", "volunteer"]

    # ─── Groq Model ──────────────────────────────────────────────────────────
    GROQ_MODEL = "llama3-8b-8192"
    GROQ_MAX_TOKENS = 1500


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}

ActiveConfig = config_map.get(os.getenv("FLASK_ENV", "development"), DevelopmentConfig)
