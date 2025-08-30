from flask import Flask, render_template, jsonify
import json, os
from json import JSONDecodeError

app = Flask(__name__)
ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")

def read_items():
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = data.get("items", [])
            meta  = data.get("meta", {})
            return items, meta
    except (FileNotFoundError, JSONDecodeError, OSError):
        return [], {"generated_at": "", "items_count": 0}

@app.route("/")
def index():
    items, meta = read_items()
    return render_template("index.html", items=items, meta=meta)

@app.route("/api/items")
def api_items():
    items, meta = read_items()
    return jsonify({"items": items, "meta": meta})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
