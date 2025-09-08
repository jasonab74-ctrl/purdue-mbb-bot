#!/usr/bin/env python3
"""
Hardened collector for Purdue MBB (GitHub Pages):
- Pull feeds, filter to MBB, write items.json (stable format).
- Stricter football suppression: drops gridiron terms even if title omits 'football'.
"""

import json, time, feedparser, re
from datetime import datetime, timezone

# -----------------------------
# Feeds (you can add/remove)
# -----------------------------
FEEDS = [
    # Local / team
    ("PurdueSports.com", "https://purduesports.com/rss.aspx?path=mbball"),
    ("Hammer and Rails", "https://www.hammerandrails.com/rss/index.xml"),
    ("Journal & Courier", "https://www.jconline.com/sports/purdue/rss/"),
    ("GoldandBlack.com", "https://api.allorigins.win/raw?url=https://goldandblack.com/feed/"),
    ("Yahoo Sports", "https://sports.yahoo.com/college-basketball/teams/purdue/news/?format=rss"),
    ("Sports Illustrated", "https://www.si.com/rss/college/purdue/"),
    ("ESPN", "https://www.espn.com/espn/rss/ncb/news"),
    ("CBS Sports", "https://www.cbssports.com/college-basketball/teams/PUR/purdue-boilermakers/rss/"),
    ("Big Ten Network", "https://btn.com/feed/"),
    # Google News query strictly for hoops
    ("Google News", "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20basketball%20OR%20%22Purdue%20MBB%22&hl=en-US&gl=US&ceid=US:en"),
]

# Trusted sources that are already hoops-targeted
TRUSTED = {
    "PurdueSports.com", "Hammer and Rails", "ESPN",
    "Sports Illustrated", "Yahoo Sports", "CBS Sports",
    "Google News", "Journal & Courier", "GoldandBlack.com", "Big Ten Network"
}

# Football-y words/contexts that often sneak in without the word 'football'
FOOTBALL_BLOCK = re.compile(
    r"\b(Ross[- ]Ade|quarterback|QB|wide receiver|WR|running back|RB|defensive end|DE|linebacker|LB|"
    r"kickoff|touchdown|field goal|gridiron|pigskin|Ryan Walters|West Lafayette High .* football)\b",
    re.IGNORECASE
)

# Hoops-required hints (at least one must appear OR source is trusted)
HOOPS_REQUIRE = re.compile(
    r"\b(basketball|MBB|men'?s basketball|KenPom|bracketology|Big Ten|Purdue hoops|Matt Painter|Edey|Boilers hoops)\b",
    re.IGNORECASE
)

def allow_item(title: str, summary: str, source: str) -> bool:
    text = f"{title} {summary or ''}"

    # hard block obvious football contexts
    if FOOTBALL_BLOCK.search(text):
        return False

    # if source is trusted, allow unless it clearly looks like football
    if source in TRUSTED:
        return not re.search(r"\bfootball|NFL\b", text, re.IGNORECASE)

    # otherwise require a hoops indicator
    return bool(HOOPS_REQUIRE.search(text)) and not re.search(r"\bfootball|NFL\b", text, re.IGNORECASE)

def parse_feed(name, url):
    try:
        d = feedparser.parse(url)
        out = []
        for e in d.entries[:50]:
            title = getattr(e, 'title', '') or ''
            link = getattr(e, 'link', '') or ''
            summary = getattr(e, 'summary', '') or getattr(e, 'description', '') or ''
            dt = None
            for key in ('published_parsed','updated_parsed'):
                if getattr(e, key, None):
                    dt = time.mktime(getattr(e,key))
                    break
            if not allow_item(title, summary, name):
                continue
            out.append({
                "title": title,
                "link": link,
                "source": name,
                "published": datetime.fromtimestamp(dt, timezone.utc).isoformat() if dt else None
            })
        return out
    except Exception:
        return []

def main():
    items = []
    for name, url in FEEDS:
        items.extend(parse_feed(name, url))

    # Sort newest first (stable)
    def key(i):
        try:
            return datetime.fromisoformat(i["published"]).timestamp() if i["published"] else 0
        except Exception:
            return 0
    items.sort(key=key, reverse=True)

    payload = {
        "team": "Purdue MBB",
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": items
    }
    with open("items.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} items.")

if __name__ == "__main__":
    main()