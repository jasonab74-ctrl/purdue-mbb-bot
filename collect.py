#!/usr/bin/env python3
import json, time, re
from datetime import datetime, timezone
import feedparser
from feeds import FEEDS, STATIC_LINKS, TRUSTED_SOURCES

OUTFILE = "items.json"
MAX_ITEMS = 120

# ---------- Purdue MBB filtering ----------
# Strategy:
# 1) If source is explicitly trusted-for-hoops, allow unless it looks obviously football.
# 2) Otherwise require Purdue context + basketball indicators, and exclude football cues.
#
# These heuristics aim to block football pieces that don't say "football" in the title
# (e.g., Ross-Ade mentions, QB/WR/RB positions, Walters, etc.) while letting hoops through.

FB_EXCLUDES = [
    r"\bfootball\b", r"\bgridiron\b", r"\bross-ade\b", r"\bwalters\b",
    r"\bqb\b", r"\bquarterback\b", r"\brb\b", r"\brunning back\b",
    r"\bwr\b", r"\bwide receiver\b", r"\btouchdown\b", r"\bkickoff\b",
    r"\blinebacker\b", r"\bdefensive (end|line|tackle|back)\b",
    r"\boffensive (line|tackle|guard|center)\b",
    r"\bfield goal\b", r"\bextra point\b", r"\bpunter?\b", r"\bspecial teams?\b",
    r"\bBig Ten (football|FB)\b",
]
FB_EXCLUDE_RE = re.compile("|".join(FB_EXCLUDES), re.I)

# Hoops indicators
BB_INCLUDES = [
    r"\bbasketball\b", r"\bmbb\b", r"\bmen['’]s?\s*basketball\b",
    r"\bmackey\b", r"\bkenpom\b", r"\bbracketology\b",
    r"\b(paintner|matt painter)\b",
    r"\bboilermakers?\b", r"\bpurdue\b",
]
BB_INCLUDE_RE = re.compile("|".join(BB_INCLUDES), re.I)

# Some site-path hints for official pages that do multi-sport
LINK_HOOPS_HINT = re.compile(r"/(mbb|mens-basketball|basketball)/", re.I)

def is_trusted_hoops_source(source_name: str, link: str) -> bool:
    s = (source_name or "").lower()
    if s in [x.lower() for x in TRUSTED_SOURCES]:
        return True
    # URLs that clearly live under a men's basketball section
    if LINK_HOOPS_HINT.search(link or ""):
        return True
    return False

def allow_item(entry):
    title = (entry.get("title") or "")
    summary = (entry.get("summary") or "")
    source  = (entry.get("source") or "")
    link    = (entry.get("link") or "")

    blob = " ".join([title, summary, source, link]).lower()

    # Obvious football? bail
    if FB_EXCLUDE_RE.search(blob):
        return False

    # Trusted hoops sources/paths: allow unless flagged as football above
    if is_trusted_hoops_source(source, link):
        return True

    # Otherwise require basketball context
    # Must mention Purdue/Boilermakers and basketball-ish language
    has_bb = BB_INCLUDE_RE.search(blob) is not None
    mentions_purdue = ("purdue" in blob) or ("boilermaker" in blob)

    return has_bb and mentions_purdue


def normalize_item(e):
    # Many feeds differ; we normalize a few fields
    published = None
    if "published_parsed" in e and e.published_parsed:
        published = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
    elif "updated_parsed" in e and e.updated_parsed:
        published = datetime.fromtimestamp(time.mktime(e.updated_parsed), tz=timezone.utc)
    else:
        published = datetime.now(tz=timezone.utc)

    return {
        "title": e.get("title", "").strip(),
        "link": e.get("link", ""),
        "source": e.get("source", e.get("author", "")).strip() or "",
        "summary": re.sub("<.*?>", "", e.get("summary", "")).strip(),
        "published": published.isoformat(),
    }


def collect():
    items = []
    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            src_name = feed.get("name", "")
            for e in parsed.entries:
                entry = {
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "summary": e.get("summary", ""),
                    "source": src_name or e.get("source", ""),
                    "published_parsed": e.get("published_parsed"),
                    "updated_parsed": e.get("updated_parsed"),
                }
                if allow_item(entry):
                    items.append(normalize_item(entry))
        except Exception as err:
            # Skip bad feeds; keep the rest
            print(f"[WARN] feed failed {feed.get('name','')} -> {err}")

    # Sort & trim
    items.sort(key=lambda x: x["published"], reverse=True)
    items = items[:MAX_ITEMS]

    payload = {
        "updated": datetime.now(tz=timezone.utc).isoformat(),
        "links": STATIC_LINKS,     # quick buttons row
        "sources": sorted({it["source"] for it in items if it.get("source")}),
        "items": items,
    }

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote {OUTFILE} with {len(items)} items.")


if __name__ == "__main__":
    collect()
