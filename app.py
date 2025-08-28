# app.py — minimal validator
import os, pathlib
from flask import Flask, jsonify

BASE = pathlib.Path(__file__).parent
app = Flask(__name__)

@app.get("/")
def home():
    return "OK - minimal app alive"

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/debug")
def debug():
    tree = {}
    for p in [BASE, BASE/"templates", BASE/"static"]:
        try:
            tree[str(p)] = sorted(x.name for x in p.iterdir())
        except FileNotFoundError:
            tree[str(p)] = []
    return jsonify({
        "cwd": str(BASE),
        "tree": tree,
        "has_items_json": (BASE/"items.json").exists(),
        "env_PORT": os.environ.get("PORT"),
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
