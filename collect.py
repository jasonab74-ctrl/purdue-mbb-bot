#!/usr/bin/env python3
import json, time, re
from datetime import datetime, timezone
import feedparser
from feeds import FEEDS, TRUSTED_SOURCES

OUTFILE = "items.json"
MAX_ITEMS = 120

# --- Tighten filtering for Purdue MBB ---
# Keep if any INCLUDE terms appear OR if source is trusted MBB source
INCLUDE = [
    r"\bmen'?s?\s*basketball\b", r"\bMBB\b", r"\bNCAA\b",
    r"\bBoilermakers\b", r"\bPainter\b", r"\bMatt Painter\b",
    r"\bEdey\b", r"\bBraden Smith\b", r"\bFletcher Loyer\b",
    r"\bPurdue\b.*\bbasketball\b"
]

# Strong football negatives
EXCLUDE = [
    r"\bfootball\b", r"\bQB\b", r"\bquarterback\b", r"\brunning back\b",
    r"\btouchdown\b", r"\bfield goal\b", r"\bRoss[- ]Ade\b",
    r"\bWalters\b", r"\bgridiron\b", r"\bBig Ten West\b"
]

inc_re = re.compile("|".join(INCLUDE), re.I)
exc_re = re.compile("|".join(EXCLUDE), re.I)

def allow_item(title, summary, source):
    text = f"{title} {summary or ''}"
    if source in TRUSTED_SOURCES:
        # allow through unless it screams football
        if exc_re.search(text):
            return False
        return True
    # Otherwise, must look like basketball and not football
    if exc_re.search(text):
        return False
    return bool(inc_re.search(text))

def simplify_source(src):
    # Normalize common names for stable dropdown labels
    s = src.strip()
    s = s.replace("Hammer & Rails", "Hammer and Rails")
    s = s.replace("Journal & Courier", "Journal & Courier")
    return s

def fetch():
    items = []
    for url in FEEDS:
        d = feedparser.parse(url)
        source = simplify_source(d.feed.get("title", "Unknown"))
        for e in d.entries[:30]:
            title = e.get("title", "").strip()
            link = e.get("link")
            summary = e.get("summary", "") or ""
            published = None
            if "published_parsed" in e and e.published_parsed:
                published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat()
            elif "updated_parsed" in e and e.updated_parsed:
                published = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
            else:
                published = datetime.now(timezone.utc).isoformat()

            if allow_item(title, summary, source):
                items.append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "published": published
                })
    # Sort newest first & trim
    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:MAX_ITEMS]

def main():
    items = fetch()
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": items
    }
    with open(OUTFILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(items)} items to {OUTFILE}")

if __name__ == "__main__":
    main()