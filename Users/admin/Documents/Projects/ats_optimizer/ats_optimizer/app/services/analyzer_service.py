"""
app/services/analyzer_service.py
Orchestrates the full ATS analysis pipeline:
  1. Parse document
  2. Extract keywords from JD
  3. Match keywords
  4. Compute semantic similarity
  5. Score (weighted ATS score)
  6. Generate AI feedback
Returns a unified result dict ready for the API response.
"""
import os
import logging
import time
from typing import Dict

from app.utils.document_parser import DocumentParser
from app.services.nlp_service import (
    extract_keywords_from_jd,
    match_keywords,
    compute_semantic_similarity,
    extract_entities,
    detect_sections,
)
from app.services.scoring_service import compute_ats_score
from app.services.ai_feedback_service import generate_ai_feedback

logger = logging.getLogger(__name__)

_parser = DocumentParser()


def analyze_resume(file_path: str, job_description: str) -> Dict:
    """
    Full pipeline entry point.

    Args:
        file_path:       Path to uploaded resume (PDF or DOCX)
        job_description: Raw job description text

    Returns:
        Complete analysis result dict
    """
    t0 = time.time()

    # ── Step 1: Parse document ───────────────────────────────────────────────
    logger.info(f"Parsing document: {file_path}")
    parse_result = _parser.parse(file_path)

    resume_text = parse_result.text
    if not resume_text.strip():
        return {
            "error": "Could not extract text from resume. "
                     "The file may be image-based or corrupted.",
            "parse_result": parse_result.to_dict(),
        }

    # ── Step 2: Extract JD keywords ─────────────────────────────────────────
    logger.info("Extracting keywords from job description")
    jd_keywords = extract_keywords_from_jd(job_description)

    # ── Step 3: Keyword matching ─────────────────────────────────────────────
    logger.info("Matching keywords against resume")
    keyword_result = match_keywords(resume_text, jd_keywords)

    # ── Step 4: Semantic similarity ──────────────────────────────────────────
    logger.info("Computing semantic similarity")
    similarity = compute_semantic_similarity(resume_text, job_description)

    # ── Step 5: Entity extraction & section detection ────────────────────────
    logger.info("Extracting entities and sections")
    entities = extract_entities(resume_text)
    sections = detect_sections(resume_text)

    # ── Step 6: ATS scoring ──────────────────────────────────────────────────
    logger.info("Computing ATS score")
    scoring = compute_ats_score(
        semantic_similarity=similarity,
        keyword_result=keyword_result,
        layout_flags=parse_result.layout_flags,
        parse_warnings=parse_result.warnings,
        resume_text=resume_text,
    )

    # ── Step 7: AI feedback ──────────────────────────────────────────────────
    logger.info("Generating AI feedback")
    ai_feedback = generate_ai_feedback(
        resume_text=resume_text,
        job_description=job_description,
        missing_keywords=keyword_result.get("missing_keywords", []),
        ats_score=scoring["final_score"],
        issues=scoring.get("all_issues", []),
    )

    elapsed = round(time.time() - t0, 2)
    logger.info(f"Analysis complete in {elapsed}s — score: {scoring['final_score']}")

    return {
        "ats_score": scoring["final_score"],
        "grade": scoring["grade"],
        "grade_color": scoring["grade_color"],
        "scoring_breakdown": scoring["breakdown"],
        "all_issues": scoring["all_issues"],
        "keyword_analysis": keyword_result,
        "semantic_similarity": round(similarity * 100, 1),
        "sections_detected": sections,
        "entities": entities,
        "parse_info": parse_result.to_dict(),
        "ai_feedback": ai_feedback,
        "processing_time_seconds": elapsed,
    }
