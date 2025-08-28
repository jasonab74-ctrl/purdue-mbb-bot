import os
import json
import pathlib
from flask import Flask, render_template

BASE_DIR = pathlib.Path(__file__).parent

app = Flask(__name__, static_folder="static", template_folder="templates")


def load_items():
    """
    Loads items from items.json.
    Accepts either:
      - a list: [ {title, link, source, date, description?}, ... ]
      - an object: { "items": [ ... ] }
    Returns a normalized list of dicts. Never raises on bad json; returns [].
    """
    path = BASE_DIR / "items.json"
    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(raw, dict):
        raw_items = raw.get("items", [])
    elif isinstance(raw, list):
        raw_items = raw
    else:
        raw_items = []

    items = []
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        items.append({
            "title": it.get("title") or it.get("name") or "Untitled",
            "link": it.get("link") or it.get("url") or "",
            "source": (it.get("source") or "").strip(),
            "date": it.get("date") or "",
            "description": it.get("description") or ""
        })
    return items


@app.route("/")
def index():
    items = load_items()

    # Dynamic source list derived from items.json (deduped, sorted)
    dynamic_sources = sorted({it["source"] for it in items if it.get("source")})

    # Always-present quick links (static sources) — these do not depend on JSON
    quick_links = [
        {"id": "hammerandrails", "label": "Hammer & Rails",
         "url": "https://www.hammerandrails.com/purdue-basketball"},
        {"id": "goldandblack", "label": "GoldandBlack",
         "url": "https://purdue.rivals.com/"},
        {"id": "espn", "label": "ESPN — Purdue MBB",
         "url": "https://www.espn.com/mens-college-basketball/team/_/id/2509/purdue-boilermakers"},
        {"id": "cbs", "label": "CBS — Purdue MBB",
         "url": "https://www.cbssports.com/college-basketball/teams/PURDUE/purdue-boilermakers/"},
        {"id": "barstool", "label": "Barstool — Purdue Tag",
         "url": "https://www.barstoolsports.com/tag/purdue"},
        {"id": "fieldof68", "label": "YouTube — Field of 68",
         "url": "https://www.youtube.com/c/RobDausterFieldOf68"},
        {"id": "sleepers", "label": "YouTube — Sleepers Media",
         "url": "https://www.youtube.com/@SleepersMedia"},
        {"id": "reddit", "label": "Reddit — r/Boilermakers",
         "url": "https://www.reddit.com/r/Boilermakers/"},
        {"id": "schedule", "label": "Purdue — Schedule",
         "url": "https://purduesports.com/sports/mens-basketball/schedule"},
        {"id": "roster", "label": "Purdue — Roster",
         "url": "https://purduesports.com/sports/mens-basketball/roster"},
    ]

    return render_template(
        "index.html",
        items=items,
        sources=dynamic_sources,
        quick_links=quick_links
    )


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    # Local only; Railway uses Gunicorn with injected $PORT
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
