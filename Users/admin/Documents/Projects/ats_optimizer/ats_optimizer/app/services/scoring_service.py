"""
app/services/scoring_service.py
Computes the final ATS score from four weighted sub-scores:
  1. Semantic similarity      (40%)
  2. Keyword match            (30%)
  3. Formatting/structure     (15%)
  4. Content quality          (15%)

Each sub-scorer returns a dict with:
  - score: float 0–100
  - details: dict of breakdown info
  - issues: list of string issue descriptions
"""
import re
import logging
from typing import Dict, List, Tuple

from config.settings import ActiveConfig as cfg
from app.utils.text_utils import (
    split_into_sentences,
    extract_first_word,
    has_quantified_achievement,
    detect_date_formats,
)
from app.services.nlp_service import detect_sections

logger = logging.getLogger(__name__)


# ─── Sub-scorer 1: Semantic Similarity ──────────────────────────────────────

def score_semantic(similarity: float) -> Dict:
    """
    similarity is already in [0, 1] from nlp_service.
    Map to 0–100.
    """
    score = round(similarity * 100, 1)
    return {
        "score": score,
        "raw_similarity": round(similarity, 4),
        "issues": [] if score >= 60 else ["Low semantic alignment with job description"],
    }


# ─── Sub-scorer 2: Keyword Match ────────────────────────────────────────────

def score_keywords(keyword_result: Dict) -> Dict:
    """
    keyword_result from nlp_service.match_keywords.
    Returns score 0–100 proportional to match_percentage.
    """
    pct = keyword_result.get("match_percentage", 0)
    score = round(pct, 1)
    issues = []
    if pct < 50:
        issues.append("Fewer than 50% of required keywords found in resume")
    if len(keyword_result.get("missing_keywords", [])) > 10:
        issues.append(f"{len(keyword_result['missing_keywords'])} important keywords missing")
    return {
        "score": score,
        "match_percentage": pct,
        "issues": issues,
    }


# ─── Sub-scorer 3: Formatting & Structure ────────────────────────────────────

def score_formatting(
    resume_text: str,
    layout_flags: Dict,
    parse_warnings: List[str],
) -> Dict:
    """
    Penalize ATS-unfriendly formatting and missing standard sections.
    Max score: 100. Each penalty reduces score.
    """
    score = 100.0
    issues = []
    details = {}

    # ── Layout penalties ────────────────────────────────────────────────────
    if layout_flags.get("multi_column"):
        score -= 20
        issues.append("Multi-column layout detected — ATS parsers often misread column order")
        details["multi_column"] = True

    if layout_flags.get("has_tables"):
        score -= 15
        issues.append("Tables detected — ATS systems frequently fail to parse table content")
        details["has_tables"] = True

    if layout_flags.get("has_graphics"):
        score -= 10
        issues.append("Embedded images/graphics found — remove for ATS compatibility")
        details["has_graphics"] = True

    if layout_flags.get("has_headers_footers"):
        score -= 5
        issues.append("Headers/footers present — content may be missed by ATS")
        details["has_headers_footers"] = True

    # ── Section presence ────────────────────────────────────────────────────
    sections_found = detect_sections(resume_text)
    missing_sections = [s for s in cfg.REQUIRED_SECTIONS if not sections_found.get(s)]
    details["sections_found"] = [s for s, v in sections_found.items() if v]
    details["missing_required_sections"] = missing_sections

    if missing_sections:
        penalty = len(missing_sections) * 10
        score -= penalty
        issues.append(f"Missing required sections: {', '.join(missing_sections)}")

    # ── Date format consistency ─────────────────────────────────────────────
    dates = detect_date_formats(resume_text)
    details["dates_found"] = len(dates)
    if dates:
        # Check for consistency: mixed numeric and text formats
        numeric_dates = [d for d in dates if re.match(r"\d{1,2}/\d{4}", d)]
        text_dates = [d for d in dates if re.match(r"[A-Za-z]", d)]
        if numeric_dates and text_dates:
            score -= 5
            issues.append("Inconsistent date formats — standardize to 'Mon YYYY' or 'MM/YYYY'")

    # ── Non-standard section headings ───────────────────────────────────────
    lines = resume_text.split("\n")
    all_caps_headings = [
        l.strip() for l in lines
        if l.strip().isupper() and 3 < len(l.strip()) < 40
    ]
    details["all_caps_headings"] = all_caps_headings[:5]

    score = max(0.0, score)
    return {
        "score": round(score, 1),
        "details": details,
        "issues": issues,
    }


# ─── Sub-scorer 4: Content Quality ──────────────────────────────────────────

def score_content_quality(resume_text: str) -> Dict:
    """
    Evaluate:
      - Quantified achievements (numbers, %, metrics)
      - Bullet point quality
      - Action verb usage
    """
    score = 100.0
    issues = []
    details = {}

    sentences = split_into_sentences(resume_text)
    if not sentences:
        return {"score": 0.0, "details": {}, "issues": ["Could not extract text content"]}

    # ── Quantified achievements ──────────────────────────────────────────────
    quantified = [s for s in sentences if has_quantified_achievement(s)]
    quant_ratio = len(quantified) / len(sentences) if sentences else 0
    details["quantified_achievement_count"] = len(quantified)
    details["quantified_ratio"] = round(quant_ratio, 2)

    if quant_ratio < 0.1:
        score -= 25
        issues.append("Very few quantified achievements — add metrics (%, $, numbers) to bullet points")
    elif quant_ratio < 0.2:
        score -= 10
        issues.append("Limited quantified achievements — aim for 20%+ of bullets to include metrics")

    # ── Action verb usage ────────────────────────────────────────────────────
    action_verb_hits = []
    weak_starts = []

    for sentence in sentences[:40]:  # cap for performance
        first_word = extract_first_word(sentence)
        if first_word in cfg.ACTION_VERBS:
            action_verb_hits.append(first_word)
        elif first_word and len(first_word) > 2 and first_word not in {"the", "a", "an"}:
            weak_starts.append(first_word)

    verb_ratio = len(action_verb_hits) / len(sentences) if sentences else 0
    details["action_verb_count"] = len(action_verb_hits)
    details["action_verbs_used"] = list(set(action_verb_hits))[:10]
    details["weak_starts"] = list(set(weak_starts))[:5]
    details["verb_ratio"] = round(verb_ratio, 2)

    if verb_ratio < 0.15:
        score -= 20
        issues.append("Few action verbs detected — start bullets with strong verbs (Led, Built, Achieved…)")
    elif verb_ratio < 0.30:
        score -= 8
        issues.append("Action verb usage could be stronger — review bullet point openings")

    # ── Bullet density ───────────────────────────────────────────────────────
    bullet_lines = [
        l for l in resume_text.split("\n")
        if l.strip().startswith(("•", "–", "-", "›", "*", "·"))
    ]
    details["bullet_count"] = len(bullet_lines)

    if len(bullet_lines) < 5:
        score -= 15
        issues.append("Few bullet points detected — structure experience as bullet points for ATS")

    # ── Word count check ────────────────────────────────────────────────────
    word_count = len(resume_text.split())
    details["word_count"] = word_count
    if word_count < 200:
        score -= 20
        issues.append("Resume appears very short — aim for 400–800 words for a 1-page resume")
    elif word_count > 1200:
        score -= 5
        issues.append("Resume may be too long — consider condensing to 1–2 pages")

    score = max(0.0, score)
    return {
        "score": round(score, 1),
        "details": details,
        "issues": issues,
    }


# ─── Final ATS Score ────────────────────────────────────────────────────────

def compute_ats_score(
    semantic_similarity: float,
    keyword_result: Dict,
    layout_flags: Dict,
    parse_warnings: List[str],
    resume_text: str,
) -> Dict:
    """
    Orchestrate all sub-scorers and combine into final ATS score.

    Returns full scoring breakdown dict.
    """
    w = cfg.WEIGHTS

    # Individual sub-scores
    sem_result  = score_semantic(semantic_similarity)
    kw_result   = score_keywords(keyword_result)
    fmt_result  = score_formatting(resume_text, layout_flags, parse_warnings)
    cq_result   = score_content_quality(resume_text)

    # Weighted final score
    final = (
        sem_result["score"]  * w["semantic_similarity"] +
        kw_result["score"]   * w["keyword_match"] +
        fmt_result["score"]  * w["formatting"] +
        cq_result["score"]   * w["content_quality"]
    )
    final = round(min(max(final, 0), 100), 1)

    # Aggregate all issues
    all_issues = (
        sem_result.get("issues", []) +
        kw_result.get("issues", []) +
        fmt_result.get("issues", []) +
        cq_result.get("issues", [])
    )

    # Grade label
    if final >= 80:
        grade = "Excellent"
        grade_color = "green"
    elif final >= 65:
        grade = "Good"
        grade_color = "blue"
    elif final >= 50:
        grade = "Fair"
        grade_color = "orange"
    else:
        grade = "Poor"
        grade_color = "red"

    return {
        "final_score": final,
        "grade": grade,
        "grade_color": grade_color,
        "weights": w,
        "breakdown": {
            "semantic_similarity": {
                **sem_result,
                "weight": w["semantic_similarity"],
                "weighted_contribution": round(sem_result["score"] * w["semantic_similarity"], 1),
            },
            "keyword_match": {
                **kw_result,
                "weight": w["keyword_match"],
                "weighted_contribution": round(kw_result["score"] * w["keyword_match"], 1),
            },
            "formatting": {
                **fmt_result,
                "weight": w["formatting"],
                "weighted_contribution": round(fmt_result["score"] * w["formatting"], 1),
            },
            "content_quality": {
                **cq_result,
                "weight": w["content_quality"],
                "weighted_contribution": round(cq_result["score"] * w["content_quality"], 1),
            },
        },
        "all_issues": all_issues,
    }
