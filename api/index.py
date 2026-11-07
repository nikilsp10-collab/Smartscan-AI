import json
import os
import sys
import urllib.parse

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.middleware.proxy_fix import ProxyFix

from src.app import app


class VercelPathFixMiddleware:
    """WSGI middleware ensuring accurate URL routing under Vercel serverless environment."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        raw_qs = environ.get("QUERY_STRING", "")
        raw_path = environ.get("PATH_INFO", "")

        # Emergency debug endpoint to inspect exact Vercel WSGI environment variables
        if "show_debug_env=1" in raw_qs or raw_path.endswith("/debug-inspect"):
            status = "200 OK"
            headers = [("Content-Type", "application/json")]
            start_response(status, headers)
            dump = {k: v for k, v in environ.items() if isinstance(v, (str, int, float, bool))}
            return [json.dumps(dump, indent=2).encode("utf-8")]

        # Determine original incoming path from Vercel
        # Check standard reverse proxy headers first
        orig = (
            environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("HTTP_X_ORIGINAL_URI")
            or environ.get("HTTP_X_INVOKE_PATH")
            or environ.get("REQUEST_URI")
        )

        if orig:
            orig_path = orig.split("?")[0]
            if orig_path and orig_path != "/api/index.py" and orig_path != "/api/index":
                environ["PATH_INFO"] = orig_path

        return self.wsgi_app(environ, start_response)


app.wsgi_app = ProxyFix(VercelPathFixMiddleware(app.wsgi_app), x_for=1, x_proto=1, x_host=1, x_prefix=1)
