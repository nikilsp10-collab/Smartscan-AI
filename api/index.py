import sys
import os

# Ensure the root directory is on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import app

# Export WSGI application for Vercel
app = app
