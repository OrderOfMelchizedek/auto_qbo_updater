#!/usr/bin/env python
"""Run the Flask backend server."""
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import app  # noqa: E402

if __name__ == "__main__":
    app.run(debug=True, port=5000)
