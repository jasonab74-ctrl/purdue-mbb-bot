import os
from flask import Flask, jsonify, render_template_string

def init_things():
    """
    One-time startup work (DB connections, cache warmup, local folders, etc).
    If you previously had code in @app.before_first_request, move it here.
    It's safe to leave this empty.
    """
    # Example:
    # os.makedirs("data", exist_ok=True)
    pass


def _register_optional_routes(app: Flask):
    """
    If you have a routes.py with a `register(app)` function,
    it will be imported and registered. If not present, no error.
    """
    try:
        import routes  # type: ignore
        if hasattr(routes, "register") and callable(routes.register):
            routes.register(app)
    except Exception:
        # We explicitly don't fail boot if optional routes are missing or broken.
        # Comment out the `except` block above to surface errors instead.
        pass


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Health check (used by curl/browser) ---
    @app.get("/healthz")
    def healthz():
        return "ok", 200

    # --- Minimal home page so you see success immediately ---
    @app.get("/")
    def index():
        html = """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Purdue MBB Feed</title>
            <style>
              body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
                     margin: 0; padding: 2rem; background: #0a0a0a; color: #f5f5f5; }
              .card { max-width: 720px; margin: 0 auto; background: #151515; border-radius: 16px;
                      padding: 24px; box-shadow: 0 6px 24px rgba(0,0,0,.35); }
              h1 { margin: 0 0 8px; font-size: 1.75rem; }
              p { margin: 0 0 16px; color: #cfcfcf; }
              code { background: #1f1f1f; padding: 2px 6px; border-radius: 6px; }
              a { color: #ffd166; text-decoration: none; }
              a:hover { text-decoration: underline; }
            </style>
          </head>
          <body>
            <div class="card">
              <h1>🚂 Purdue MBB feed is live</h1>
              <p>Server booted with Flask 3–safe app factory.</p>
              <p>Health check: <a href="/healthz">/healthz</a> should say <code>ok</code>.</p>
              <p>If you have additional routes in <code>routes.py</code> with <code>register(app)</code>, they will be auto-loaded.</p>
            </div>
          </body>
        </html>
        """
        return render_template_string(html)

    # Do one-time startup safely for Flask 3+
    with app.app_context():
        init_things()

    # Optionally load user routes if present (no-op if missing)
    _register_optional_routes(app)

    return app


# Allow `python server.py` for local runs
if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
