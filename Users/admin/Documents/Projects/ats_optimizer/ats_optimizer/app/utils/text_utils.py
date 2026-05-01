"""
app/utils/text_utils.py
Shared text-processing helpers used across services.
"""
import re
from typing import List, Set


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer after normalization."""
    return normalize(text).split()


def extract_numbers(text: str) -> List[str]:
    """Extract all numeric mentions (plain and with units)."""
    pattern = r"\b\d+(?:\.\d+)?(?:\s?%|x|k|m|b|million|billion|thousand)?\b"
    return re.findall(pattern, text, re.IGNORECASE)


def has_quantified_achievement(sentence: str) -> bool:
    """
    Returns True if sentence contains a measurable metric.
    Examples: '30%', '2x', '$50k', '10 million'
    """
    pattern = r"\b\d+(?:\.\d+)?\s?(?:%|x|k|m|b|million|billion|thousand|percent|\$|usd|eur|gbp)?\b"
    matches = re.findall(pattern, sentence, re.IGNORECASE)
    return len(matches) > 0


def extract_first_word(sentence: str) -> str:
    """Return the first meaningful word of a sentence (for verb analysis)."""
    words = sentence.strip().split()
    if words:
        return words[0].lower().strip("•–-›*")
    return ""


def detect_date_formats(text: str) -> List[str]:
    """
    Find all date strings in text.
    Supports: Jan 2020, January 2020, 01/2020, 2020, 2018–2022
    """
    patterns = [
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
        r"\b\d{1,2}/\d{4}\b",
        r"\b\d{4}\s*[-–—]\s*(?:\d{4}|Present|Current|Now)\b",
        r"\b\d{4}\b",
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, text, re.IGNORECASE))
    return found


def split_into_sentences(text: str) -> List[str]:
    """
    Naive sentence splitter — splits on newlines and period-terminated phrases.
    Good enough for resume bullet detection without full NLP overhead.
    """
    lines = text.split("\n")
    sentences = []
    for line in lines:
        line = line.strip().strip("•–-›*").strip()
        if len(line) > 15:  # skip very short fragments
            sentences.append(line)
    return sentences


STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "during",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "this", "that", "these", "those", "i", "you", "he", "she",
    "it", "we", "they", "my", "your", "his", "her", "its", "our", "their",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "not", "no", "nor", "so", "yet", "both", "either", "neither", "each",
    "as", "if", "then", "than", "too", "very", "just", "also", "such",
}


def remove_stopwords(tokens: List[str]) -> List[str]:
    return [t for t in tokens if t not in STOPWORDS]
