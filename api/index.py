import os
import sys
import urllib.parse

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.middleware.proxy_fix import ProxyFix

from src.app import app


class VercelPathFixMiddleware:
    """WSGI middleware ensuring 100% accurate URL routing on Vercel serverless rewrites."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs_raw = environ.get("QUERY_STRING", "")
        if "__path__=" in qs_raw:
            qs = urllib.parse.parse_qs(qs_raw, keep_blank_values=True)
            real_path = qs.pop("__path__", ["/"])[0]
            if not real_path.startswith("/"):
                real_path = "/" + real_path
            environ["PATH_INFO"] = real_path
            environ["QUERY_STRING"] = urllib.parse.urlencode(qs, doseq=True)
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
