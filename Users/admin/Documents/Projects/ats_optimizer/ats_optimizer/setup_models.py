#!/usr/bin/env python3
"""
setup_models.py
Run this ONCE after pip install to download required NLP models.
Usage:  python setup_models.py
"""
import subprocess
import sys

def run(cmd):
    print(f"\n▶ {cmd}")
    result = subprocess.run(cmd.split(), capture_output=False)
    if result.returncode != 0:
        print(f"  ✗ Failed (exit {result.returncode})")
    else:
        print(f"  ✓ Done")
    return result.returncode == 0

print("=" * 55)
print("  ATS Optimizer — Model Setup")
print("=" * 55)

# spaCy model
run(f"{sys.executable} -m spacy download en_core_web_sm")

# Sentence-Transformers will auto-download on first use,
# but we can pre-cache it here:
print("\n▶ Pre-caching Sentence-Transformers model (all-MiniLM-L6-v2)...")
try:
    from sentence_transformers import SentenceTransformer
    SentenceTransformer("all-MiniLM-L6-v2")
    print("  ✓ Done")
except Exception as e:
    print(f"  ✗ Failed: {e}")

print("\n✅ Setup complete. You can now run:  python run.py\n")
