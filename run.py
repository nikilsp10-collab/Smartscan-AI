"""
SmartScan AI - Application Launcher
To start the application, run:
    python run.py
Then open your web browser to:
    http://localhost:5000
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.app import app
from src.config import SERVER_CONFIG

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("  SMARTSCAN AI - Electronic Warfare Signal Prioritization", flush=True)
    print(f"  Tactical Dashboard running at: http://127.0.0.1:{SERVER_CONFIG.port}", flush=True)
    print("=" * 60, flush=True)
    app.run(host=SERVER_CONFIG.host, port=SERVER_CONFIG.port, debug=False)
