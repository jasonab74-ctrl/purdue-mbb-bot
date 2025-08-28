import os, json
from flask import Flask, jsonify, render_template, request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_DIR, "items.json")

app = Flask(__name__, static_folder="static", template_folder="templates")


def load_data():
    """
    items.json format (created by collect.py):

      {
        "modified": "YYYY-MM-DD HH:MM:SS",
        "items": [
          {"title": "...", "link": "...", "source": "...", "published": "..."},
          ...
        ]
      }
    """
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "items" in data:
                return data
            # if old style (just a list), normalize
            if isinstance(data, list):
                return {"modified": "never", "items": data}
        except Exception:
            pass
    return {"modified": "never", "items": []}


@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", modified=data.get("modified", "never"))


@app.route("/api/items")
def api_items():
    # Return just the array for simplicity on the frontend
    return jsonify(load_data().get("items", []))


@app.route("/api/last-mod")
def api_last_mod():
    return jsonify(load_data().get("modified", "never"))


@app.route("/api/refresh-now", methods=["GET", "POST"])
def refresh_now():
    expected = os.environ.get("REFRESH_KEY")
    key = request.args.get("key")
    if expected and key != expected:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    try:
        from collect import collect_all
        count = collect_all()
        return jsonify({"ok": True, "count": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
