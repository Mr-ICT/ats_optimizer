"""
app/services/nlp_service.py
Core NLP pipeline:
  - spaCy: NER, section detection, entity extraction
  - Sentence-Transformers: semantic similarity via cosine similarity
  - YAKE: keyword extraction from job description
"""
import logging
import re
from typing import Dict, List, Tuple
from functools import lru_cache

import numpy as np

from config.settings import ActiveConfig as cfg
from app.utils.text_utils import normalize, tokenize, remove_stopwords, STOPWORDS

logger = logging.getLogger(__name__)


# ─── Lazy Model Loading ──────────────────────────────────────────────────────

_nlp = None
_encoder = None
_yake_extractor = None


def get_spacy():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load(cfg.SPACY_MODEL)
            logger.info(f"Loaded spaCy model: {cfg.SPACY_MODEL}")
        except OSError:
            logger.warning(f"spaCy model '{cfg.SPACY_MODEL}' not found. Run: python -m spacy download en_core_web_sm")
            _nlp = None
    return _nlp


def get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _encoder = SentenceTransformer(cfg.SENTENCE_TRANSFORMER_MODEL)
            logger.info(f"Loaded SentenceTransformer: {cfg.SENTENCE_TRANSFORMER_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            _encoder = None
    return _encoder


def get_yake():
    global _yake_extractor
    if _yake_extractor is None:
        try:
            import yake
            _yake_extractor = yake.KeywordExtractor(
                lan=cfg.YAKE_LANGUAGE,
                n=cfg.YAKE_MAX_NGRAM_SIZE,
                dedupLim=cfg.YAKE_DEDUP_THRESHOLD,
                top=cfg.YAKE_TOP_N_KEYWORDS,
                features=None,
            )
            logger.info("Loaded YAKE keyword extractor")
        except ImportError:
            logger.warning("YAKE not installed. Run: pip install yake")
            _yake_extractor = None
    return _yake_extractor


# ─── Section Detection ───────────────────────────────────────────────────────

SECTION_KEYWORDS = {
    "experience": ["experience", "work history", "employment", "professional background",
                   "career history", "work experience", "professional experience"],
    "education":  ["education", "academic background", "qualifications", "degrees",
                   "academic history", "educational background"],
    "skills":     ["skills", "technical skills", "core competencies", "competencies",
                   "technologies", "tools", "expertise", "proficiencies"],
    "summary":    ["summary", "profile", "objective", "about me", "professional summary",
                   "career objective", "overview"],
    "projects":   ["projects", "portfolio", "personal projects", "key projects"],
    "certifications": ["certifications", "certificates", "licenses", "credentials"],
    "awards":     ["awards", "honors", "achievements", "accomplishments", "recognition"],
    "publications": ["publications", "papers", "research", "articles"],
    "volunteer":  ["volunteer", "volunteering", "community", "non-profit"],
}


def detect_sections(text: str) -> Dict[str, bool]:
    """
    Scan resume text for presence of standard resume sections.
    Returns dict: section_name → found (True/False)
    """
    text_lower = text.lower()
    found = {}
    for section, keywords in SECTION_KEYWORDS.items():
        found[section] = any(kw in text_lower for kw in keywords)
    return found


# ─── Named Entity Extraction (spaCy) ────────────────────────────────────────

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Use spaCy NER to extract:
      - PERSON (names)
      - ORG (companies, schools)
      - DATE (years, ranges)
      - GPE (locations)
      - PRODUCT / WORK_OF_ART (tech names)
    Returns empty lists if spaCy unavailable.
    """
    nlp = get_spacy()
    if nlp is None:
        return {}

    entities: Dict[str, List[str]] = {}
    try:
        doc = nlp(text[:50000])  # cap to avoid memory issues
        for ent in doc.ents:
            label = ent.label_
            entities.setdefault(label, [])
            val = ent.text.strip()
            if val and val not in entities[label]:
                entities[label].append(val)
    except Exception as e:
        logger.error(f"spaCy NER failed: {e}")

    return entities


# ─── Semantic Similarity (Sentence-Transformers) ─────────────────────────────

def compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Encode both texts and compute cosine similarity.
    Returns a float in [0, 1].
    Falls back to simple token-overlap Jaccard if encoder unavailable.
    """
    encoder = get_encoder()
    if encoder is None:
        return _jaccard_fallback(text_a, text_b)

    try:
        from sklearn.metrics.pairwise import cosine_similarity
        embeddings = encoder.encode([text_a[:8192], text_b[:8192]])
        sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return float(np.clip(sim, 0.0, 1.0))
    except Exception as e:
        logger.error(f"Semantic similarity failed: {e}")
        return _jaccard_fallback(text_a, text_b)


def _jaccard_fallback(text_a: str, text_b: str) -> float:
    """Token-overlap Jaccard similarity as fallback."""
    tokens_a = set(remove_stopwords(tokenize(text_a)))
    tokens_b = set(remove_stopwords(tokenize(text_b)))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ─── Keyword Extraction (YAKE) ───────────────────────────────────────────────

def extract_keywords_from_jd(job_description: str) -> List[str]:
    """
    Extract top keywords from job description using YAKE.
    YAKE scores are inverted (lower = more important), so we sort ascending.
    Falls back to TF-style frequency extraction if YAKE unavailable.
    """
    extractor = get_yake()
    if extractor is None:
        return _frequency_fallback_keywords(job_description)

    try:
        keywords_with_scores = extractor.extract_keywords(job_description)
        # keywords_with_scores: list of (keyword, score) — lower score = more relevant
        keywords = [kw for kw, score in sorted(keywords_with_scores, key=lambda x: x[1])]
        return keywords
    except Exception as e:
        logger.error(f"YAKE extraction failed: {e}")
        return _frequency_fallback_keywords(job_description)


def _frequency_fallback_keywords(text: str, top_n: int = 40) -> List[str]:
    """Simple frequency-based keyword extraction as fallback."""
    tokens = remove_stopwords(tokenize(text))
    freq: Dict[str, int] = {}
    for token in tokens:
        if len(token) > 2:
            freq[token] = freq.get(token, 0) + 1
    sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [token for token, _ in sorted_tokens[:top_n]]


# ─── Keyword Matching ────────────────────────────────────────────────────────

def match_keywords(
    resume_text: str,
    jd_keywords: List[str]
) -> Dict:
    """
    Match job description keywords against resume text.
    Uses both exact and soft (substring) matching.

    Returns:
      found_keywords    - keywords present in resume
      missing_keywords  - keywords absent from resume
      match_percentage  - float 0–100
    """
    resume_lower = resume_text.lower()
    resume_tokens = set(tokenize(resume_text))

    found = []
    missing = []

    for kw in jd_keywords:
        kw_lower = kw.lower()
        kw_tokens = set(kw_lower.split())

        # Exact phrase match
        if kw_lower in resume_lower:
            found.append(kw)
            continue

        # All tokens of multi-word keyword present individually
        if kw_tokens and kw_tokens.issubset(resume_tokens):
            found.append(kw)
            continue

        # Partial match: keyword is substring of any resume word (handles plurals, stemming)
        partial_match = any(
            kw_lower in tok or tok in kw_lower
            for tok in resume_tokens
            if abs(len(tok) - len(kw_lower)) <= 3
        )
        if partial_match:
            found.append(kw)
        else:
            missing.append(kw)

    total = len(jd_keywords)
    pct = (len(found) / total * 100) if total > 0 else 0.0

    return {
        "found_keywords": found,
        "missing_keywords": missing,
        "total_jd_keywords": total,
        "matched_count": len(found),
        "match_percentage": round(pct, 1),
    }
