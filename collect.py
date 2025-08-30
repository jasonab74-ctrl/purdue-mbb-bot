#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import os, re, json, time
from html import unescape
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import requests, feedparser   # robust parsing for Google/Bing/Reddit/blog RSS

# ---- config ----
ITEMS_PATH = Path(os.environ.get("ITEMS_PATH", "items.json"))
MAX_ITEMS  = int(os.environ.get("MAX_ITEMS", "500"))
MAX_PER_FEED = 80
HTTP_TIMEOUT = 18
UA = "Mozilla/5.0 (X11; Linux x86_64) PurdueMBBFeed/1.2 (+https://example.local)"

from feeds import FEEDS  # dropdown + sources

# ---- men’s-only matching (lenient but targeted) ----

PLAYERS = [
    # 2025–26 roster you provided
    "c.j. cox","cj cox","antione west jr","fletcher loyer","braden smith","aaron fine",
    "jack lusk","jack benter","omer mayer","gicarri harris","jace rayl",
    "trey kaufman-renn","liam murphy","sam king","raleigh burgess","daniel jacobsen","oscar cluff",
    # coaches / program signals
    "matt painter","mackey arena","boilermakers","boilers"
]

WOMENS = re.compile(r"\bwomen'?s\b|\bwbb\b|\bwbk\b|\blady\b", re.I)
MEN_SIG = re.compile(r"\bmen'?s\b|\bmbb\b|\bmen'?s?\s+basketball\b", re.I)
BASKETBALL = re.compile(r"\bbasketball\b", re.I)
PURDUE = re.compile(r"\bpurdue\b|\bboilermakers?\b|\bboilers?\b", re.I)
PLAYER_RX = re.compile("|".join(re.escape(n) for n in PLAYERS), re.I)
OTHER_SPORTS = re.compile(
    r"\bfootball\b|\bvolleyball\b|\bbaseball\b|\bsoccer\b|\bwrestling\b|\bsoftball\b|\bhockey\b|"
    r"\btrack\b|\bgolf\b|\bswim|min|swimming|xc|cross\s*country", re.I
)

def _clean_html(s: str) -> str:
    if not s: return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return unescape(s)

def _norm_date(e) -> str:
    # Try feedparser’s published / updated
    for key in ("published_parsed","updated_parsed"):
        tm = getattr(e, key, None)
        if tm:
            return f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}T{tm.tm_hour:02d}:{tm.tm_min:02d}:00Z"
    # Last resort: today (keeps sort stable)
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _blob_from_entry(e, source_name: str) -> str:
    parts = [
        getattr(e, "title", ""),
        getattr(e, "summary", "") or getattr(e, "description", "")
    ]
    # feedparser sometimes exposes content[]
    content = getattr(e, "content", None)
    if isinstance(content, list):
        for c in content:
            parts.append((c or {}).get("value") or "")
    # tags/keywords help for YouTube/news
    tags = getattr(e, "tags", None)
    if isinstance(tags, list):
        for t in tags:
            term = getattr(t, "term", "") if hasattr(t, "term") else (t.get("term") if isinstance(t, dict) else "")
            parts.append(term or "")
    return _clean_html(" ".join(p for p in parts if p))

def _is_mbb(title: str, body: str, source_name: str) -> bool:
    blob = f"{title}\n{body}"
    # never include explicit women's items unless men's is also present
    if WOMENS.search(blob) and not MEN_SIG.search(blob):
        return False

    purdueish = PURDUE.search(blob) or ("purdue" in source_name.lower())
    hoopsish = BASKETBALL.search(blob) or MEN_SIG.search(blob) or PLAYER_RX.search(blob)

    # if it's clearly another sport AND we don't see any hoops-ish signal, drop
    if OTHER_SPORTS.search(blob) and not hoopsish:
        return False

    # trusted path: lots of our feeds already query for basketball — allow if purdue-ish OR player/coach
    if purdueish and hoopsish:
        return True

    # fallback: if the source name itself is basketball-focused, be more lenient
    lname = source_name.lower()
    if ("basketball" in lname or "mbb" in lname or "hammer & rails" in lname or "goldandblack" in lname):
        return hoopsish or purdueish

    # final nudge: strong player or coach mention + generic headline
    if PLAYER_RX.search(blob) and PURDUE.search(blob):
        return True

    return False

def _score(title: str, body: str, source: str) -> int:
    t, b = title.lower(), body.lower()
    s = 0
    if "purdue" in t or "boilermaker" in t: s += 4
    if "basketball" in t or "mbb" in t: s += 3
    s += sum(2 for k in ("matt painter","mackey") if k in t)
    s += sum(1 for k in PLAYERS if k in t)
    s += sum(1 for k in PLAYERS if k in b)
    if any(k in source.lower() for k in ("purduesports", "goldandblack", "hammer & rails")):
        s += 1
    return s

def _fetch(url: str):
    # Robust fetch (Google/Bing/Reddit/blog) -> feedparser entries
    r = requests.get(url, headers={"User-Agent": UA}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return feedparser.parse(r.content)

def collect() -> Tuple[List[Dict], Dict[str,int]]:
    ranked: List[Tuple[Dict,int]] = []
    per_counts: Dict[str,int] = {}

    for f in FEEDS:
        name, url = f.get("name","Feed"), f["url"]
        per_counts[name] = 0
        try:
            parsed = _fetch(url)
        except Exception:
            # skip but keep count at 0
            continue

        pulled = 0
        for e in parsed.entries:
            title = (getattr(e, "title", "") or "").strip()
            link  = (getattr(e, "link", "") or "").strip()
            if not title or not link: 
                continue

            body = _blob_from_entry(e, name)
            if not _is_mbb(title, body, name):
                continue

            item = {
                "title": title,
                "link": link,
                "source": name,
                "date": _norm_date(e),
                "summary": (body[:260] + ("…" if len(body) > 260 else "")) if body else ""
            }
            ranked.append((item, _score(title, body, name)))
            pulled += 1
            if pulled >= MAX_PER_FEED:
                break

        per_counts[name] = pulled
        time.sleep(0.15)  # be polite

    # sort by (date, score)
    def dkey(it: Dict) -> str:
        return it.get("date") or "0000-00-00T00:00:00Z"

    ranked.sort(key=lambda p: (dkey(p[0]), p[1]), reverse=True)
    items = [it for it,_ in ranked][:MAX_ITEMS]
    return items, per_counts

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def write_items(items: List[Dict], per_counts: Dict[str,int]):
    meta = {
        "generated_at": now_iso(),
        "items_count": len(items),
        "items_mtime": now_iso(),
        "last_run": {
            "ok": True, "rc": 0, "final_count": len(items),
            "per_feed_counts": per_counts, "ts": now_iso()
        }
    }
    ITEMS_PATH.write_text(json.dumps({"items": items, "meta": meta}, ensure_ascii=False), encoding="utf-8")

def main():
    try:
        items, per = collect()
    except Exception as e:
        items, per = [], {}
    write_items(items, per)
    print(json.dumps({"ok": True, "count": len(items), "ts": now_iso()}))

if __name__ == "__main__":
    main()
