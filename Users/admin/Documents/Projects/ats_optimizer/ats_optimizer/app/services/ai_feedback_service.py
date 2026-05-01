"""
app/services/ai_feedback_service.py
Generates tailored resume improvement suggestions using Groq API.
Structured output: sections for Improvements, Missing Skills, Rewrites.
"""
import json
import logging
import os
from typing import Dict, List, Optional

from config.settings import ActiveConfig as cfg

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert ATS resume coach and hiring specialist with 15+ years of experience.
Your job is to provide highly specific, actionable resume improvement advice.

RULES:
- Be SPECIFIC to the actual resume content and job description provided
- NEVER give generic advice like "add more details" without specifying what details
- Reference actual job requirements from the JD
- Suggest real bullet point rewrites with metrics where possible
- Output ONLY valid JSON — no markdown, no preamble, no explanation outside JSON

OUTPUT FORMAT (strict JSON):
{
  "improvements": [
    {"section": "Experience", "issue": "...", "suggestion": "..."},
    ...
  ],
  "missing_skills": ["skill1", "skill2", ...],
  "bullet_rewrites": [
    {"original": "...", "rewritten": "..."},
    ...
  ],
  "summary_suggestion": "...",
  "top_priority": "The single most impactful change to make"
}"""


def generate_ai_feedback(
    resume_text: str,
    job_description: str,
    missing_keywords: List[str],
    ats_score: float,
    issues: List[str],
) -> Dict:
    """
    Call Groq API to generate structured, contextual resume feedback.
    Falls back to rule-based feedback if API unavailable.
    """
    api_key = cfg.GROQ_API_KEY
    if not api_key:
        logger.warning("No GROQ_API_KEY — using rule-based fallback feedback")
        return _rule_based_feedback(resume_text, job_description, missing_keywords, issues)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        user_prompt = _build_user_prompt(
            resume_text, job_description, missing_keywords, ats_score, issues
        )

        response = client.chat.completions.create(
            model=cfg.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=cfg.GROQ_MAX_TOKENS,
            temperature=0.4,
        )

        raw = response.choices[0].message.content.strip()
        result = _parse_ai_response(raw)
        result["source"] = "groq_llm"
        return result

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        fb = _rule_based_feedback(resume_text, job_description, missing_keywords, issues)
        fb["error"] = str(e)
        return fb


def _build_user_prompt(
    resume_text: str,
    job_description: str,
    missing_keywords: List[str],
    ats_score: float,
    issues: List[str],
) -> str:
    # Truncate to avoid token limits
    resume_snippet = resume_text[:3000]
    jd_snippet = job_description[:2000]
    missing_kw_str = ", ".join(missing_keywords[:20]) if missing_keywords else "None identified"
    issues_str = "\n".join(f"- {i}" for i in issues[:10]) if issues else "None"

    return f"""
RESUME TEXT (first 3000 chars):
{resume_snippet}

JOB DESCRIPTION (first 2000 chars):
{jd_snippet}

CURRENT ATS SCORE: {ats_score}/100

DETECTED ISSUES:
{issues_str}

TOP MISSING KEYWORDS: {missing_kw_str}

Please analyze this resume against the job description and provide your structured JSON feedback.
Focus on the most impactful improvements. Reference specific parts of the JD and resume.
"""


def _parse_ai_response(raw: str) -> Dict:
    """Safely parse JSON from LLM response."""
    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from mixed content
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass

    return {
        "improvements": [{"section": "General", "issue": "AI parsing error", "suggestion": raw[:500]}],
        "missing_skills": [],
        "bullet_rewrites": [],
        "summary_suggestion": "",
        "top_priority": "Review ATS detected issues above",
    }


def _rule_based_feedback(
    resume_text: str,
    job_description: str,
    missing_keywords: List[str],
    issues: List[str],
) -> Dict:
    """
    Fallback feedback when Groq is unavailable.
    Generates structured suggestions from detected issues and missing keywords.
    """
    improvements = []

    for issue in issues[:6]:
        section = "Formatting" if any(
            w in issue.lower() for w in ["table", "column", "graphic", "header"]
        ) else "Content"
        improvements.append({
            "section": section,
            "issue": issue,
            "suggestion": _issue_to_suggestion(issue),
        })

    missing_skills = missing_keywords[:15]

    bullet_rewrites = [
        {
            "original": "Responsible for managing team projects",
            "rewritten": "Led cross-functional team of 5 engineers to deliver 3 projects on time, reducing average delivery time by 20%",
        },
        {
            "original": "Worked on improving system performance",
            "rewritten": "Optimized database query performance, achieving 40% reduction in response time and supporting 10k+ daily active users",
        },
    ]

    top_priority = (
        f"Add these missing keywords to your resume: {', '.join(missing_keywords[:5])}"
        if missing_keywords
        else "Quantify your achievements with specific metrics and percentages"
    )

    return {
        "improvements": improvements,
        "missing_skills": missing_skills,
        "bullet_rewrites": bullet_rewrites,
        "summary_suggestion": (
            "Tailor your professional summary to directly address the key requirements "
            "in the job description, highlighting your most relevant experience."
        ),
        "top_priority": top_priority,
        "source": "rule_based_fallback",
    }


def _issue_to_suggestion(issue: str) -> str:
    """Map a detected issue to a concrete suggestion."""
    mapping = {
        "multi-column": "Convert to single-column layout. Use a simple Word or Google Docs template.",
        "table": "Replace tables with plain bullet-pointed lists. ATS cannot reliably parse table cells.",
        "graphic": "Remove images, icons, and graphics. Use text-only formatting.",
        "header": "Move contact info from header to the top of the main content area.",
        "keyword": "Incorporate the missing keywords naturally into your experience bullet points.",
        "quantif": "Add specific numbers: 'increased sales by 25%', 'managed $500K budget', 'led team of 8'.",
        "action verb": "Start each bullet with a strong action verb: Led, Built, Designed, Optimized, Delivered.",
        "section": "Add the missing section with at least 3–5 relevant bullet points or items.",
        "date": "Use consistent date format throughout: 'Jan 2020 – Mar 2022' or '01/2020 – 03/2022'.",
        "bullet": "Convert paragraph descriptions into concise bullet points (1–2 lines each).",
        "short": "Expand resume content — include more detail about responsibilities and achievements.",
    }
    issue_lower = issue.lower()
    for key, suggestion in mapping.items():
        if key in issue_lower:
            return suggestion
    return "Review and address this issue to improve ATS compatibility and readability."
