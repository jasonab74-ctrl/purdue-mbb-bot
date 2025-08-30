#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purdue MBB — collector with host-aware headers, smarter football exclusion,
YouTube guard, and fail-safe lenient pass.

- Chrome-like UA + referer for Google/Bing (prevents empty RSS bodies)
- Smarter exclusion: only blocks football if NO basketball signal is present
- Stricter YouTube: always allow PurdueSports channel + Purdue MBB playlist;
  other YouTube needs Purdue/Boilermakers/players/coach context
- Pass 1 = normal filters; if < 40 items, Pass 2 = lenient (non-football only)
- Freshness window 365d (override with env FRESH_DAYS)
- Atomic write to items.json + rich diagnostics
"""

import json, os, re, time, traceback
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

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
    KEYWORDS_INCLUDE = ["purdue","boilers","boilermakers","basketball","ncaa","painter","mackey","roster","brian neubert"]
    KEYWORDS_EXCLUDE = ["football","qb","nfl"]
    MAX_ITEMS_PER_FEED = 200
    ALLOW_DUPLICATE_DOMAINS = True
    DOMAIN_PER_FEED_LIMIT = 999
    SOURCE_ALIASES = {}

# -----------------------------------------------------------------------------
# Player keywords (you can extend via env PLAYER_EXTRA="name1,name2")
PLAYER_KEYWORDS_DEFAULT = [
    "braden smith","fletcher loyer","trey kaufman","trey kaufman-renn","mason gillis","caleb furst",
    "myles colvin","camden heide","will berg","jack benter","daniel jacobsen","levi cook",
    "matt painter","zach edey"
]
EXTRA = os.environ.get("PLAYER_EXTRA", "").strip()
PLAYER_KEYWORDS = PLAYER_KEYWORDS_DEFAULT + (
    [s.strip().lower() for s in EXTRA.split(",") if s.strip()] if EXTRA else []
)

ROOT = os.path.dirname(os.path.abspath(__file__))
ITEMS_PATH = os.path.join(ROOT, "items.json")

# Browser-like headers
BASE_HEADERS = {
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

# Freshness window (days)
FRESH_DAYS = int(os.environ.get("FRESH_DAYS", "365"))

# Regexes
INCLUDE_TERMS = (KEYWORDS_INCLUDE or []) + PLAYER_KEYWORDS
BASKETBALL_RE = re.compile(
    r"\b(basketball|men['’]s basketball|boilers?|boilermakers?|boilerball|purdue|painter|mackey|roster)\b",
    re.IGNORECASE,
)
CORE_INCLUDE_RE = re.compile(
    r"\b(purdue|boilers?|boilermakers?|boilerball|basketball|ncaa|painter|mackey|roster|brian neubert)\b"
    r"|2025[\-—–]26|class of 2025|class of 2026",
    re.IGNORECASE,
)
INCLUDE_RE = re.compile("|".join([re.escape(k) for k in INCLUDE_TERMS]), re.IGNORECASE)
EXCLUDE_RE = re.compile("|".join([re.escape(k) for k in (KEYWORDS_EXCLUDE or [])]), re.IGNORECASE)

YOUTUBE_HOSTS = ("youtube.com","youtu.be")
# Always-allow playlist (official)
YT_PLAYLIST_ALLOW = {"PLCIT1wYGMWN80GZO_ybcH6vuHeObcOcmh"}

TARGETED_FEED_HINTS = (
    "purdue","boiler","mackey","matt painter","brian neubert","youtube","r/boilermakers",
    "bing news","google news","hammer & rails","on3","rivals","goldandblack","journalcourier"
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
            q = {k: v for k, v in q.items() if k in ("t","time_continue","v","list","channel_id","ab_channel")}
        else:
            q = {}
        return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(q), "")) or url
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

def is_youtube_link(url: str) -> bool:
    return any(h in (url or "") for h in YOUTUBE_HOSTS)

def youtube_allowed(entry: Dict[str, Any], txt: str) -> bool:
    """Allow official Purdue sources unconditionally; otherwise require Purdue context."""
    link = (entry.get("link") or entry.get("id") or "")
    if not is_youtube_link(link):
        return True
    if "list=PLCIT1wYGMWN80GZO_ybcH6vuHeObcOcmh" in link:
        return True  # official playlist
    if "ab_channel=PurdueSports" in link or "user=purduesports" in link:
        return True  # PurdueSports channel
    # otherwise require Purdue/basketball signals
    if CORE_INCLUDE_RE.search(txt) or INCLUDE_RE.search(txt) or BASKETBALL_RE.search(txt):
        return True
    return False

def passes_filters(entry: Dict[str, Any], source_name: str, *, lenient: bool) -> bool:
    txt = text_of(entry)

    # Smart exclusion: only block if football appears AND no basketball context present
    has_football = bool(EXCLUDE_RE.search(txt))
    has_hoops    = bool(BASKETBALL_RE.search(txt) or INCLUDE_RE.search(txt) or CORE_INCLUDE_RE.search(txt))
    if has_football and not has_hoops:
        return False

    if not youtube_allowed(entry, txt):
        return False

    if lenient:
        # In lenient pass, any non-football (or mixed but with hoops) gets through
        return True

    if feed_is_targeted(source_name): return True
    if CORE_INCLUDE_RE.search(txt):  return True
    if INCLUDE_RE.search(txt):       return True
    if BASKETBALL_RE.search(txt):    return True
    return False

def entry_to_item(entry: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    title = entry.get("title") or "Untitled"
    link  = normalize_link(entry.get("link") or entry.get("id") or "")
    iso   = to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))
    source= SOURCE_ALIASES.get(source_name, source_name)
    summary = clean_html(entry.get("summary") or entry.get("description") or "")
    if is_youtube_link(link) and "YouTube" not in source:
        source = f"YouTube — {source}"
    return {"title": title, "link": link, "date": iso, "source": source, "summary": summary[:600]}

# ---------- host-aware fetch with diagnostics ----------
def _headers_for(url: str) -> Dict[str,str]:
    h = dict(BASE_HEADERS)
    host = domain_of(url)
    if "news.google.com" in host:
        h["Referer"] = "https://news.google.com/"
    elif "bing.com" in host:
        h["Referer"] = "https://www.bing.com/news"
    elif "reddit.com" in host:
        h["Accept"] = "*/*"
    return h

def fetch_bytes_with_retries(url: str):
    last_exc = None
    for i in range(RETRIES):
        try:
            resp = requests.get(url, headers=_headers_for(url), timeout=TIMEOUT, allow_redirects=True)
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
        parsed = feedparser.parse(data or url)
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
def write_items_with_meta(items: List[Dict[str, Any]], last_run: Dict[str, Any]):
    payload = {
        "items": items,
        "generated_at": now_iso(),
        "last_run": last_run,
        "items_mtime": now_iso(),
    }
    tmp = ITEMS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ITEMS_PATH)

def load_previous() -> Dict[str, Any]:
    if not os.path.exists(ITEMS_PATH):
        return {"items": [], "generated_at": now_iso(), "last_run": {}}
    try:
        with open(ITEMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "generated_at": now_iso(), "last_run": {}}

# ---------- collection ----------
def collect_pass(*, lenient: bool):
    items: List[Dict[str, Any]] = []
    errors: List[str] = []
    per_feed_kept: Dict[str,int] = {}
    per_feed_seen: Dict[str,int] = {}
    per_feed_meta: Dict[str,Dict[str,Any]] = {}
    debug_seen_titles: Dict[str, List[str]] = {}
    debug_kept_titles: Dict[str, List[str]] = {}

    seen_links = set()
    per_feed_cap = max(80, int(MAX_ITEMS_PER_FEED))

    for f in FEEDS:
        name = f.get("name","Feed")
        url  = f.get("url")
        if not url: continue
        try:
            entries, meta = fetch_feed_with_meta(url)
            per_feed_meta[name] = meta
            per_feed_seen[name] = len(entries)
            debug_seen_titles[name] = []
            debug_kept_titles[name] = []
            added = 0
            for e in entries:
                title = (e.get("title") or "").strip()
                if len(debug_seen_titles[name]) < 5:
                    debug_seen_titles[name].append(title)

                if not passes_filters(e, name, lenient=lenient):
                    continue

                itm = entry_to_item(e, name)
                if not itm["link"]:
                    continue
                if too_old(itm["date"]):
                    continue
                if itm["link"] in seen_links:
                    continue

                if len(debug_kept_titles[name]) < 5:
                    debug_kept_titles[name].append(itm["title"])

                seen_links.add(itm["link"])
                items.append(itm)
                added += 1
                if added >= per_feed_cap:
                    break
            per_feed_kept[name] = added
        except Exception as ex:
            errors.append(f"{name}: {ex}")
            per_feed_seen[name] = per_feed_seen.get(name, 0)
            per_feed_kept[name] = per_feed_kept.get(name, 0)
            per_feed_meta[name] = {"http": None, "bytes": 0, "error": str(ex)}
            debug_seen_titles[name] = debug_seen_titles.get(name, [])
            debug_kept_titles[name] = debug_kept_titles.get(name, [])
            traceback.print_exc()

    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    items = items[:800]
    debug = {"seen_titles": debug_seen_titles, "kept_titles": debug_kept_titles}
    return items, errors, per_feed_kept, per_feed_seen, per_feed_meta, debug

def merge_items(new_items, prev_items, keep: int = 650):
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

    # Pass 1 (strict)
    new_items, errors, kept, seen, meta, dbg = collect_pass(lenient=False)

    # Pass 2 (lenient) if too few
    used_lenient = False
    if len(new_items) < 40:
        l_items, l_err, l_kept, l_seen, l_meta, l_dbg = collect_pass(lenient=True)
        used_lenient = True
        errors += ["-- lenient retry --"] + l_err
        for k,v in l_kept.items(): kept[k] = max(kept.get(k,0), v)
        for k,v in l_seen.items(): seen[k] = max(seen.get(k,0), v)
        for k,v in l_meta.items(): meta[k] = v
        dbg["seen_titles"].update(l_dbg["seen_titles"])
        dbg["kept_titles"].update(l_dbg["kept_titles"])
        new_items = l_items

    new_n = len(new_items)

    # Guard rails
    MIN_ABSOLUTE = 60
    REL_DROP = 0.6
    if new_n == 0 and prev_n > 0:
        final_items, decision = prev_items, "kept_previous_zero_new"
    elif new_n < MIN_ABSOLUTE and prev_n > 0:
        final_items, decision = merge_items(new_items, prev_items), "merged_min_absolute"
    elif prev_n > 0 and new_n < int(prev_n * REL_DROP):
        final_items, decision = merge_items(new_items, prev_items), "merged_relative_drop"
    else:
        final_items, decision = new_items, "accepted_new"

    last_run = {
        "ok": True,
        "invoked_at": now_iso(),
        "decision": decision,
        "used_lenient": used_lenient,
        "new_count": new_n,
        "prev_count": prev_n,
        "final_count": len(final_items),
        "per_feed_counts": kept,
        "per_feed_seen": seen,
        "per_feed_meta": meta,
        "fresh_days": FRESH_DAYS,
        "player_keywords": PLAYER_KEYWORDS,
        "debug_titles": dbg,
        "ts": now_iso()
    }

    write_items_with_meta(final_items, last_run)
    print(json.dumps(last_run))

if __name__ == "__main__":
    main()
