from flask import Flask, jsonify, render_template, send_from_directory
import json
import os

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_ROOT, "items.json")

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

def load_items():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {"items": [], "modified": "never"}
    return {"items": [], "modified": "never"}

@app.route("/")
def index():
    data = load_items()
    return render_template("index.html", modified=data.get("modified", "never"))

@app.route("/api/items")
def api_items():
    return jsonify(load_items())

@app.route("/api/last-mod")
def api_last_mod():
    return jsonify({"modified": load_items().get("modified", "never")})

# Optional: serve a robots.txt that’s harmless
@app.route("/robots.txt")
def robots():
    return "User-agent: *\nDisallow:\n", 200, {"Content-Type": "text/plain; charset=utf-8"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
