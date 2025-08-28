import os, json, datetime, requests, feedparser
from feeds import FEEDS

HEADERS = {"User-Agent": "Mozilla/5.0 (mbb-news-collector)"}

# Filter out obvious non-MBB topics
EXCLUDE_WORDS = {
    "football","nfl","volleyball","baseball","softball","wrestling","soccer",
    "golf","tennis","track","swim","hockey","lacrosse"
}

# Positive signals to keep relevant MBB items
INCLUDE_HINTS = {
    "basketball","mbb","matt painter","painter","mackey","edey","zach edey",
    "braden","braden smith","fletcher","loyer","gillis","lance jones",
    "boilerball","boiler ball","ncaa","big ten","purdue"
}

def _norm(*parts):
    return " ".join(p for p in parts if p).lower()

def _is_basketball(title, summary):
    t = _norm(title, summary)
    if not any(w in t for w in ("purdue","boilermaker","boilermakers")):
        return False
    if any(w in t for w in EXCLUDE_WORDS):
        return False
    return any(w in t for w in INCLUDE_HINTS)

def _fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return feedparser.parse(r.content)

def collect_all():
    items, seen = [], set()
    for feed in FEEDS:
        try:
            parsed = _fetch(feed["url"])
        except Exception:
            continue
        for e in parsed.entries:
            title = getattr(e, "title", "").strip()
            link = getattr(e, "link", "").strip()
            summary = getattr(e, "summary", "")
            published = getattr(e, "published", "") or getattr(e, "updated", "")
            if not title or not link:
                continue
            key = (title, link)
            if key in seen:
                continue
            if not _is_basketball(title, summary):
                continue
            items.append({
                "title": title,
                "link": link,
                "source": feed["name"],
                "published": published
            })
            seen.add(key)

    # Sort newest-ish first (best effort; RSS dates vary)
    items.sort(key=lambda x: x.get("published", ""), reverse=True)

    data = {
        "modified": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items
    }
    out = os.path.join(os.path.dirname(__file__), "items.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return len(items)

if __name__ == "__main__":
    n = collect_all()
    print(f"Wrote {n} items")
