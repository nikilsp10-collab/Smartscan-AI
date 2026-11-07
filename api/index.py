import os
import sys

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from src.app import app


@app.route("/api/debug-env")
def debug_env():
    return jsonify({k: v for k, v in request.environ.items() if isinstance(v, (str, int, float, bool))})


class VercelPathFixMiddleware:
    """WSGI middleware ensuring proper URL dispatching under Vercel serverless rewrites."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = environ.get("HTTP_X_MATCHED_PATH")
        if matched_path:
            environ["PATH_INFO"] = matched_path.split("?")[0]
        else:
            path = environ.get("PATH_INFO", "")
            for prefix in ["/api/index.py", "/api/index"]:
                if path.startswith(prefix):
                    path = path[len(prefix):] or "/"
                    break
            environ["PATH_INFO"] = path

        return self.wsgi_app(environ, start_response)


# Wrap with VercelPathFix and Werkzeug ProxyFix
app.wsgi_app = ProxyFix(VercelPathFixMiddleware(app.wsgi_app), x_for=1, x_proto=1, x_host=1, x_prefix=1)
