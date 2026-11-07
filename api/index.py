import os
import sys

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app import app


class VercelPathFixMiddleware:
    """WSGI middleware ensuring proper URL dispatching under Vercel serverless rewrites."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = environ.get("HTTP_X_MATCHED_PATH")
        path = environ.get("PATH_INFO", "")

        if matched_path:
            environ["PATH_INFO"] = matched_path
        elif path.startswith("/api/index"):
            subpath = path[len("/api/index"):]
            environ["PATH_INFO"] = subpath if subpath else "/"

        return self.wsgi_app(environ, start_response)


# Apply WSGI middleware for Vercel
app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)
