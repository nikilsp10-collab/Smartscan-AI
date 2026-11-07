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
        raw_path = (
            environ.get("HTTP_X_MATCHED_PATH")
            or environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("PATH_INFO", "")
        )

        # Strip any Vercel internal script prefix (/api/index.py or /api/index)
        for prefix in ["/api/index.py", "/api/index", "api/index.py", "api/index"]:
            if raw_path.startswith(prefix):
                raw_path = raw_path[len(prefix):]
                break

        if not raw_path.startswith("/"):
            raw_path = "/" + raw_path

        # Strip query string if it was included in URI
        if "?" in raw_path:
            raw_path = raw_path.split("?", 1)[0]

        environ["PATH_INFO"] = raw_path
        return self.wsgi_app(environ, start_response)


# Apply WSGI middleware for Vercel
app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)
