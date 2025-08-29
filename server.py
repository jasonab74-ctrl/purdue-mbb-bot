# server.py
from flask import Flask

def init_things():
    # put DB/cache init here later if needed
    pass

def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return "ok", 200

    @app.get("/")
    def index():
        return (
            "<h1>Purdue Basketball — OK</h1>"
            "<p>Healthcheck at <code>/healthz</code>.</p>"
        ), 200

    with app.app_context():
        init_things()

    return app

# Optional: local dev (not used on Railway)
if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8080)
