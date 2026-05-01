# ATS Resume Optimizer

A production-ready Flask web application that uses a multi-stage NLP pipeline to evaluate resumes against job descriptions — giving you a precise ATS compatibility score, keyword gap analysis, semantic alignment, and AI-generated improvement suggestions.

---

## Tech Stack

| Layer | Library |
|---|---|
| Web Framework | Flask 3 |
| PDF Parsing | PyMuPDF (fitz) |
| DOCX Parsing | python-docx |
| NER / Section Detection | spaCy (en_core_web_sm) |
| Semantic Similarity | Sentence-Transformers (all-MiniLM-L6-v2) |
| Keyword Extraction | YAKE |
| AI Suggestions | Groq API (llama3-8b-8192) |

---

## Project Structure

```
ats_optimizer/
├── run.py                        # Entry point
├── setup_models.py               # One-time model download
├── requirements.txt
├── .env.example                  # Copy → .env
│
├── config/
│   └── settings.py               # All weights, model names, config
│
└── app/
    ├── __init__.py               # Flask app factory
    ├── routes/
    │   └── main.py               # GET /, POST /analyze, GET /health
    ├── services/
    │   ├── analyzer_service.py   # Pipeline orchestrator
    │   ├── nlp_service.py        # spaCy + Sentence-Transformers + YAKE
    │   ├── scoring_service.py    # Weighted ATS score computation
    │   └── ai_feedback_service.py # Groq LLM integration
    ├── utils/
    │   ├── document_parser.py    # PDF + DOCX parser with confidence score
    │   └── text_utils.py        # Shared text helpers
    ├── templates/
    │   └── index.html            # Main UI
    └── static/
        ├── css/style.css
        └── js/app.js
```

---

## Step-by-Step Setup

### Step 1 — Clone / create the project

```bash
# If you received this as a zip, unzip it:
unzip ats_optimizer.zip
cd ats_optimizer

# OR if starting fresh, create the directory:
mkdir ats_optimizer && cd ats_optimizer
```

### Step 2 — Create a Python virtual environment

```bash
# Python 3.9+ required
python3 -m venv venv

# Activate it:
# macOS / Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3 — Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs Flask, PyMuPDF, python-docx, spaCy, sentence-transformers, YAKE, Groq, and all other dependencies.

> **Note:** `sentence-transformers` will pull in PyTorch (~700 MB). This is a one-time download.

### Step 4 — Download NLP models

```bash
python setup_models.py
```

This downloads:
- `en_core_web_sm` — spaCy English model (~12 MB)
- `all-MiniLM-L6-v2` — Sentence-Transformers model (~80 MB, cached by HuggingFace)

### Step 5 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
GROQ_API_KEY=your_groq_api_key_here   # Get free key at console.groq.com
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=change-this-to-a-random-string
```

> **Getting a Groq API key (free):**
> 1. Go to https://console.groq.com
> 2. Sign up → API Keys → Create key
> 3. Paste into `.env`
>
> The app works WITHOUT a Groq key — it will use rule-based fallback suggestions instead of LLM-generated ones.

### Step 6 — Run the application

```bash
python run.py
```

You should see:

```
🚀 ATS Resume Optimizer running at http://localhost:5000
```

Open your browser at **http://localhost:5000**

---

## API Endpoints

### `POST /analyze`

Upload a resume and job description for full ATS analysis.

**Request** (multipart/form-data):
```
resume          File    PDF or DOCX file
job_description Text    Full job description (min 50 chars)
```

**Response** (JSON):
```json
{
  "ats_score": 72.4,
  "grade": "Good",
  "grade_color": "blue",
  "scoring_breakdown": {
    "semantic_similarity": { "score": 68.1, "weight": 0.40 },
    "keyword_match":       { "score": 75.0, "weight": 0.30 },
    "formatting":          { "score": 80.0, "weight": 0.15 },
    "content_quality":     { "score": 65.0, "weight": 0.15 }
  },
  "keyword_analysis": {
    "found_keywords":   ["python", "machine learning", "flask"],
    "missing_keywords": ["kubernetes", "mlops", "ci/cd"],
    "match_percentage": 60.0,
    "total_jd_keywords": 35
  },
  "semantic_similarity": 68.1,
  "sections_detected": {
    "experience": true,
    "education": true,
    "skills": true,
    "summary": false
  },
  "parse_info": {
    "confidence": 0.97,
    "word_count": 542,
    "pages": 1,
    "warnings": [],
    "layout_flags": {
      "multi_column": false,
      "has_tables": false,
      "has_graphics": false
    }
  },
  "ai_feedback": {
    "top_priority": "Add kubernetes and mlops to your skills section",
    "improvements": [...],
    "missing_skills": ["kubernetes", "mlops", "terraform"],
    "bullet_rewrites": [...],
    "summary_suggestion": "...",
    "source": "groq_llm"
  },
  "all_issues": [...],
  "processing_time_seconds": 3.12
}
```

### `GET /health`

```json
{
  "status": "ok",
  "spacy_loaded": true,
  "encoder_loaded": true,
  "groq_configured": true
}
```

### `GET /api/config`

Returns the current scoring weights and model configuration.

---

## Scoring Model

| Component | Weight | What it measures |
|---|---|---|
| Semantic Similarity | 40% | Cosine similarity via Sentence-Transformers |
| Keyword Match | 30% | YAKE-extracted JD keywords found in resume |
| Formatting | 15% | ATS-safe layout, required sections, date consistency |
| Content Quality | 15% | Action verbs, quantified achievements, bullet density |

Weights are fully configurable in `config/settings.py`.

---

## Tuning Scoring Weights

Edit `config/settings.py`:

```python
WEIGHTS = {
    "semantic_similarity": 0.40,  # ← adjust these
    "keyword_match":       0.30,
    "formatting":          0.15,
    "content_quality":     0.15,
}
# Must sum to 1.0
```

---

## Running in Production

```bash
# Install gunicorn (already in requirements.txt)
gunicorn "app:create_app()" --workers 2 --bind 0.0.0.0:8000

# Or with Docker (create Dockerfile based on python:3.11-slim)
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `OSError: [E050] Can't find model 'en_core_web_sm'` | Run `python setup_models.py` or `python -m spacy download en_core_web_sm` |
| `ModuleNotFoundError: No module named 'fitz'` | Run `pip install PyMuPDF` |
| Groq suggestions not appearing | Add `GROQ_API_KEY` to `.env` — app still works without it |
| PDF shows 0 words extracted | PDF is likely image-based (scanned). Convert to text-based PDF first |
| Slow first request | Sentence-Transformers model loads on first request (~5s). Subsequent requests are fast |

---

## License

MIT — free to use and modify.
