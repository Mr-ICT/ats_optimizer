"""
run.py
Entry point for the ATS Resume Optimizer Flask application.
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"\n🚀 ResumeIQ running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
