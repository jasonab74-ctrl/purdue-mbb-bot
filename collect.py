#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purdue MBB — resilient collector (SMART FILTERS)
- Pulls feeds from feeds.py
- Retries with backoff
- Smarter include logic so Purdue-targeted feeds don't get over-filtered
- Strict football + other-sport excludes
- Cleans HTML, de-dupes by link, caps per domain
- Sorts newest->oldest and writes items.json atomically
- Guardrails: never clobber previous with 0/low results
- ALWAYS prints JSON summary for /collect-now and /diag
"""

import json, os, re, time, traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import feedparser  # type: ignore
import requests    # type: ignore
from html import unescape

# ---- Config from feeds.py ----------------------------------------------------
try:
    from feeds import (
        FEEDS, STATIC_LINKS,
        KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE,
        MAX_ITEMS_PER_FEED, ALLOW_DUPLICATE_DOMAINS, SOURCE_ALIASES,
        DOMAIN_PER_FEED_LIMIT,
    )
except Exception:
    FEEDS = []
    STATIC_LINKS = []
    KEYWORDS_INCLUDE = [
        "purdue","boilers","boilermakers","boilermaker","boilerball",
        "men’s basketball","mens basketball","men's basketball","basketball","college basketball","ncaa",
        "big ten","b1g","mackey arena","matt painter","painter",
        "zach edey","braden smith","fletcher loyer","lance jones","trey kaufman","mason gillis","caleb first","myles colvin",
    ]
    KEYWORDS_EXCLUDE = [
        "football","cfb","gridiron","quarterback","qb","running back","rb","wide receiver","wr","tight end","te",
        "linebacker","lb","cornerback","cb","safety","edge","defensive end","de","nose tackle",
        "offensive line","defensive line","kickoff","punt","field goal","touchdown","two-point conversion","extra point",
        "rushing yards","passing yards","sack","spring game","fall camp","depth chart","nfl","combine","pro day",
        "baseball","softball","volleyball","soccer","wrestling","track and field","cross country","golf","tennis","swimming",
        "women’s basketball","womens basketball","women's basketball",
    ]
    MAX_ITEMS_PER_FEED = 120
    ALLOW_DUPLICATE_DOMAINS = False
    DOMAIN_PER_FEED_LIMIT = 4
    SOURCE_ALIASES = {}

# -----------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(ROOT, "items.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (PurdueMBBFeed/1.5) Python/requests",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
}
TIMEOUT = 25
RETRIES = 3
BACKOFF_BASE = 1.6

# Core cue regexes (word boundaries, case-insensitive)
CORE_INCLUDE_RE = re.compile(r"\b(purdue|boilers?|boilermakers?|boilerball|basketball|ncaa|painter|mackey)\b", re.IGNORECASE)
INCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_INCLUDE]), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_EXCLUDE]), re.IGNORECASE)
YOUTUBE_HOSTS = ("youtube.com", "youtu.be")

# Feeds we consider Purdue-targeted by name and thus safe to auto-include
TARGETED_FEED_HINTS = (
    "purdue", "boiler", "mackey", "matt painter", "youTube mentions", "r/boilermakers"
)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def to_iso(dt_struct) -> str:
    try:
        if not dt_struct:
            return now_iso()
        ts = time.mktime(dt_struct)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return now_iso()

def normalize_link(url: str) -> str:
    if not url: return ""
    try:
        from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode
        u = urlparse(url)
        q = dict(parse_qsl(u.query, keep_blank_values=True))
        if any(h in u.netloc for h in YOUTUBE_HOSTS):
            q = {k: v for k, v in q.items() if k in ("t","time_continue")}
        else:
            q = {}
        return urlunparse((u.scheme,u.netloc,u.path,u.params, urlencode(q), "")) or url
    except Exception:
        return url

def domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def clean_html(s: str) -> str:
    if not s: return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(re.sub(r"\s+", " ", s)).strip()
    return s

def text_of(entry: Dict[str, Any]) -> str:
    parts=[]
    for k in ("title","summary","description"):
        v = entry.get(k)
        if isinstance(v,str): parts.append(v)
    return " ".join(parts)

def feed_is_targeted(feed_name: str) -> bool:
    n = (feed_name or "").lower()
    return any(h in n for h in TARGETED_FEED_HINTS)

def passes_filters(entry: Dict[str, Any], source_name: str) -> bool:
    txt = text_of(entry)
    # Hard exclude first
    if EXCLUDE_RE.search(txt):
        return False
    # If the feed itself is Purdue-targeted by name, accept unless excluded
    if feed_is_targeted(source_name):
        return True
    # Otherwise, require at least a core cue OR any extended include
    if CORE_INCLUDE_RE.search(txt):
        return True
    if INCLUDE_RE.search(txt):
        return True
    return False

def entry_to_item(entry: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    title = entry.get("title") or "Untitled"
    link  = normalize_link(entry.get("link") or entry.get("id") or "")
    iso   = to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))
    source= SOURCE_ALIASES.get(source_name, source_name)
    summary = clean_html(entry.get("summary") or entry.get("description") or "")
    host = domain_of(link)
    if any(h in host for h in YOUTUBE_HOSTS) and "YouTube" not in source:
        source = f"YouTube — {source}"
    return {"title": title, "link": link, "date": iso, "source": source, "summary": summary[:600]}

def fetch_bytes_with_retries(url: str) -> bytes:
    last = None
    for i in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            last = e
            time.sleep(BACKOFF_BASE ** i)
    if last: raise last
    return b""

def fetch_feed(url: str):
    try:
        data = fetch_bytes_with_retries(url)
        if data: return feedparser.parse(data)
    except Exception:
        pass
    return feedparser.parse(url)

def load_previous() -> Dict[str, Any]:
    if not os.path.exists(ITEMS_PATH):
        return {"items": [], "generated_at": now_iso()}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "generated_at": now_iso()}

def collect_once() -> Tuple[List[Dict[str, Any]], List[str], Dict[str,int], Dict[str,int]]:
    items: List[Dict[str, Any]] = []
    errors: List[str] = []
    per_feed_kept: Dict[str,int] = {}
    per_feed_seen: Dict[str,int] = {}

    seen_links = set()
    domain_counts: Dict[Tuple[str,str], int] = {}

    per_feed_cap = max(40, int(MAX_ITEMS_PER_FEED))
    dom_cap = max(1, int(DOMAIN_PER_FEED_LIMIT)) if "DOMAIN_PER_FEED_LIMIT" in globals() else 3

    for f in FEEDS:
        name = f.get("name","Feed")
        url  = f.get("url")
        if not url: continue
        try:
            parsed = fetch_feed(url)
            entries = parsed.entries or []
            per_feed_seen[name] = len(entries)
            added = 0
            for e in entries:
                if not passes_filters(e, name): continue
                itm = entry_to_item(e, name)
                if not itm["link"]: continue
                if itm["link"] in seen_links: continue

                if not ALLOW_DUPLICATE_DOMAINS:
                    d = domain_of(itm["link"])
                    key = (name, d)
                    cnt = domain_counts.get(key, 0)
                    if d and cnt >= dom_cap:
                        continue
                    if d:
                        domain_counts[key] = cnt + 1

                seen_links.add(itm["link"])
                items.append(itm)
                added += 1
                if added >= per_feed_cap: break
            per_feed_kept[name] = added
        except Exception as ex:
            errors.append(f"{name}: {ex}")
            per_feed_seen[name] = per_feed_seen.get(name, 0)
            per_feed_kept[name] = per_feed_kept.get(name, 0)
            traceback.print_exc()

    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    items = items[:700]
    return items, errors, per_feed_kept, per_feed_seen

def merge_items(new_items: List[Dict[str, Any]], prev_items: List[Dict[str, Any]], keep: int = 550) -> List[Dict[str, Any]]:
    by_link: Dict[str, Dict[str, Any]] = {}
    for it in prev_items: by_link[it.get("link","")] = it
    for it in new_items:
        link = it.get("link","")
        if not link: continue
        old = by_link.get(link)
        if (not old) or (it.get("date","") > old.get("date","")):
            by_link[link] = it
    merged = list(by_link.values())
    merged.sort(key=lambda x: x.get("date") or "", reverse=True)
    return merged[:keep]

def write_items_safely(items: List[Dict[str, Any]]):
    payload = {"items": items, "generated_at": now_iso()}
    tmp = ITEMS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ITEMS_PATH)

def main():
    prev = load_previous()
    prev_items = prev.get("items", [])
    prev_n = len(prev_items)

    new_items, errors, per_feed_kept, per_feed_seen = collect_once()
    new_n = len(new_items)

    # Guard rails
    MIN_ABSOLUTE = 80
    REL_DROP = 0.6

    if new_n == 0 and prev_n > 0:
        final_items, decision = prev_items, "kept_previous_zero_new"
    elif new_n < MIN_ABSOLUTE and prev_n > 0:
        final_items, decision = merge_items(new_items, prev_items), "merged_min_absolute"
    elif prev_n > 0 and new_n < int(prev_n * REL_DROP):
        final_items, decision = merge_items(new_items, prev_items), "merged_relative_drop"
    else:
        final_items, decision = new_items, "accepted_new"

    write_items_safely(final_items)

    summary = {
        "ok": True,
        "decision": decision,
        "new_count": new_n,
        "prev_count": prev_n,
        "final_count": len(final_items),
        "per_feed_counts": per_feed_kept,
        "per_feed_seen": per_feed_seen,
        "errors": errors,
        "ts": now_iso()
    }
    print(json.dumps(summary))

if __name__ == "__main__":
    main()
