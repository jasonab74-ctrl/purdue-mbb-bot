#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purdue MBB — robust collector (freshness + diagnostics, FIXED SYNTAX)
"""

import json, os, re, time, traceback
from datetime import datetime, timezone, timedelta
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
    KEYWORDS_INCLUDE = ["purdue","boilers","boilermakers","basketball","ncaa","painter","mackey","roster","class of 2025","class of 2026","2025-26","2025–26"]
    KEYWORDS_EXCLUDE = ["football","qb","nfl"]
    MAX_ITEMS_PER_FEED = 120
    ALLOW_DUPLICATE_DOMAINS = False
    DOMAIN_PER_FEED_LIMIT = 4
    SOURCE_ALIASES = {}

# -----------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(ROOT, "items.json")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0 Safari/537.36"),
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "close",
}
TIMEOUT = 25
RETRIES = 3
BACKOFF_BASE = 1.7
FRESH_DAYS = int(os.environ.get("FRESH_DAYS", "120"))

CORE_INCLUDE_RE = re.compile(
    r"\b(purdue|boilers?|boilermakers?|boilerball|basketball|ncaa|painter|mackey|roster)\b"
    r"|2025[\-—–]26|class of 2025|class of 2026",
    re.IGNORECASE,
)
INCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_INCLUDE]), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join([re.escape(k) for k in KEYWORDS_EXCLUDE]), re.IGNORECASE)
YOUTUBE_HOSTS = ("youtube.com","youtu.be")

TARGETED_FEED_HINTS = (
    "purdue","boiler","mackey","matt painter","youtube mentions","r/boilermakers","bing news","google news",
    "on3 — purdue","247sports — purdue"
)

def now_iso() -> str: return datetime.now(timezone.utc).isoformat()

def domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def normalize_link(url: str) -> str:
    if not url: return ""
    try:
        from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode
        u = urlparse(url)
        q = dict(parse_qsl(u.query, keep_blank_values=True))
        if any(h in u.netloc for h in YOUTUBE_HOSTS):
            q = {k:v for k,v in q.items() if k in ("t","time_continue")}
        else:
            q = {}
        return urlunparse((u.scheme,u.netloc,u.path,u.params, urlencode(q), "")) or url
    except Exception:
        return url

def to_iso(dt_struct) -> str:
    try:
        if not dt_struct: return now_iso()
        ts = time.mktime(dt_struct)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return now_iso()

def too_old(iso: str) -> bool:
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        return (datetime.now(timezone.utc) - dt) > timedelta(days=FRESH_DAYS)
    except Exception:
        return False

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
    if EXCLUDE_RE.search(txt): return False
    if feed_is_targeted(source_name): return True
    if CORE_INCLUDE_RE.search(txt): return True
    if INCLUDE_RE.search(txt): return True
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

# ---------- fetch with diagnostics ----------
def fetch_bytes_with_retries(url: str):
    last_exc = None
    for i in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            return resp.content or b"", resp.status_code
        except Exception as e:
            last_exc = e
        time.sleep(BACKOFF_BASE ** i)
    if last_exc: raise last_exc
    return b"", 0

def fetch_feed_with_meta(url: str):
    meta = {"http": None, "bytes": 0, "error": None}
    try:
        data, code = fetch_bytes_with_retries(url)
        meta["http"]  = int(code) if code else None
        meta["bytes"] = len(data)
        if data:
            parsed = feedparser.parse(data)
        else:
            parsed = feedparser.parse(url)
        entries = parsed.entries or []
        return entries, meta
    except Exception as e:
        meta["error"] = str(e)
        try:
            parsed = feedparser.parse(url)
            entries = parsed.entries or []
            return entries, meta
        except Exception as e2:
            meta["error"] = f"{meta['error']} | fp:{e2}"
            return [], meta

# ---------- persistence ----------
def load_previous() -> Dict[str, Any]:
    if not os.path.exists(ITEMS_PATH):
        return {"items": [], "generated_at": now_iso()}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "generated_at": now_iso()}

def write_items_safely(items: List[Dict[str, Any]]):
    payload = {"items": items, "generated_at": now_iso()}
    tmp = ITEMS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ITEMS_PATH)

# ---------- collection ----------
def collect_once():
    items: List[Dict[str, Any]] = []
    errors: List[str] = []
    per_feed_kept: Dict[str,int] = {}
    per_feed_seen: Dict[str,int] = {}
    per_feed_meta: Dict[str,Dict[str,Any]] = {}

    seen_links = set()
    domain_counts: Dict[Tuple[str,str], int] = {}

    per_feed_cap = max(40, int(MAX_ITEMS_PER_FEED))
    dom_cap = max(1, int(DOMAIN_PER_FEED_LIMIT)) if "DOMAIN_PER_FEED_LIMIT" in globals() else 3

    for f in FEEDS:
        name = f.get("name","Feed")
        url  = f.get("url")
        if not url: continue
        try:
            entries, meta = fetch_feed_with_meta(url)
            per_feed_meta[name] = meta
            per_feed_seen[name] = len(entries)
            added = 0
            for e in entries:
                if not passes_filters(e, name): continue
                itm = entry_to_item(e, name)
                if not itm["link"]:
                    continue
                if too_old(itm["date"]):
                    continue
                if itm["link"] in seen_links:
                    continue

                if not ALLOW_DUPLICATE_DOMAINS:
                    d = domain_of(itm["link"]); key = (name, d); cnt = domain_counts.get(key, 0)
                    if d and cnt >= dom_cap: continue
                    if d: domain_counts[key] = cnt + 1

                seen_links.add(itm["link"])
                items.append(itm)
                added += 1
                if added >= per_feed_cap: break
            per_feed_kept[name] = added
        except Exception as ex:
            errors.append(f"{name}: {ex}")
            per_feed_seen[name] = per_feed_seen.get(name, 0)
            per_feed_kept[name] = per_feed_kept.get(name, 0)
            per_feed_meta[name] = {"http": None, "bytes": 0, "error": str(ex)}
            traceback.print_exc()

    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    items = items[:700]
    return items, errors, per_feed_kept, per_feed_seen, per_feed_meta

def merge_items(new_items, prev_items, keep: int = 550):
    by_link: Dict[str, Dict[str, Any]] = {}
    for it in prev_items:
        link = it.get("link","")
        if link:
            by_link[link] = it
    for it in new_items:
        link = it.get("link","")
        if not link:
            continue
        old = by_link.get(link)
        if (not old) or (it.get("date","") > old.get("date","")):
            by_link[link] = it
    merged = list(by_link.values())
    merged.sort(key=lambda x: x.get("date") or "", reverse=True)
    return merged[:keep]

def main():
    prev = load_previous()
    prev_items = prev.get("items", [])
    prev_n = len(prev_items)

    new_items, errors, per_feed_kept, per_feed_seen, per_feed_meta = collect_once()
    new_n = len(new_items)

    MIN_ABSOLUTE = 50
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
        "per_feed_meta": per_feed_meta,
        "fresh_days": FRESH_DAYS,
        "errors": errors,
        "ts": now_iso()
    }
    print(json.dumps(summary))

if __name__ == "__main__":
    main()
