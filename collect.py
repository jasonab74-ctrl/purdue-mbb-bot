#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, html, hashlib
from datetime import datetime, timezone
from urllib.request import Request, urlopen

import feedparser  # robust RSS/Atom parser

ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")
MAX_ITEMS  = int(os.environ.get("MAX_ITEMS", "400"))

# Use your existing feeds file as-is
from feeds import FEEDS

# -------------------- helpers --------------------

UA = "Mozilla/5.0 (compatible; MBB-Lite/1.0; +https://example)"

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def http_get(url, headers=None, timeout=20):
    req = Request(url, headers=headers or {"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read()

def to_text(x):
    if x is None:
        return ""
    if isinstance(x, bytes):
        return x.decode("utf-8", "ignore")
    return str(x)

def parse_any(xml_bytes):
    d = feedparser.parse(xml_bytes)
    out = []
    for e in d.entries:
        title = to_text(getattr(e, "title", "")).strip()
        link  = to_text(getattr(e, "link", "")).strip()

        # Prefer content/summary/detail in that order
        summary = ""
        if "content" in e and e.content:
            summary = to_text(e.content[0].value)
        elif "summary" in e:
            summary = to_text(e.summary)
        elif "description" in e:
            summary = to_text(e.description)

        # Dates: published -> updated -> None
        date = (
            to_text(getattr(e, "published", ""))
            or to_text(getattr(e, "updated", ""))
        )

        out.append({
            "title": html.unescape(title),
            "link": link,
            "summary": html.unescape(summary or ""),
            "date": date,
        })
    return out

def fetch_google(feed): return parse_any(http_get(feed["url"]))
def fetch_bing(feed):   return parse_any(http_get(feed["url"]))
def fetch_rss(feed):    return parse_any(http_get(feed["url"]))

def fetch_reddit(feed):
    # Reddit JSON API (already in your FEEDS)
    j = json.loads(to_text(http_get(feed["url"], headers={"User-Agent": "mmblite/1.0"})))
    out = []
    for c in j.get("data", {}).get("children", []):
        p = c.get("data", {})
        out.append({
            "title": p.get("title", ""),
            "link":  p.get("url", "") or ("https://reddit.com" + p.get("permalink", "")),
            "summary": p.get("selftext", ""),
            "date": datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc).isoformat(),
        })
    return out

FETCHERS = {
    "google": fetch_google,
    "bing":   fetch_bing,
    "rss":    fetch_rss,
    "reddit": fetch_reddit,
}

def hash_id(link, title):
    h = hashlib.sha1()
    h.update(to_text(link).encode("utf-8"))
    h.update(to_text(title).encode("utf-8"))
    return h.hexdigest()[:16]

# -------------------- FILTER: Men’s MBB (lenient, safe) --------------------

# Names we treat as strong MBB signals
PLAYERS = [
    "braden smith","fletcher loyer","trey kaufman","trey kaufman-renn","mason gillis",
    "caleb furst","myles colvin","camden heide","will berg","jack benter",
    "daniel jacobsen","levi cook","matt painter","zach edey","omer mayer","omas mayer"
]

RE_PU      = re.compile(r"\bpurdue\b|\bboilermakers?\b|\bboilers?\b", re.I)
RE_BBALL   = re.compile(r"\bbasketball\b|\bmbb\b", re.I)
RE_MEN     = re.compile(r"\bmen'?s\b|\bmbb\b|\bmen'?s\s+basketball\b", re.I)
RE_WOMEN   = re.compile(r"\bwomen'?s\b|\bwbb\b|\bwbk\b|\blady\b", re.I)
RE_PLAYER  = re.compile("|".join(re.escape(n) for n in PLAYERS), re.I)
RE_OTHERS  = re.compile(r"\bfootball\b|\bvolleyball\b|\bbaseball\b|\bsoccer\b|\bwrestling\b|\bsoftball\b|\btrack\b|\bgolf\b|\bswim", re.I)

def allow_item(title, summary, feed):
    """
    Strategy:
      1) If it explicitly says *women’s* and not men’s -> drop.
      2) Require Purdue-ish context OR a trusted feed name.
      3) Require hoops-ish context (basketball/mbb/player/Matt Painter).
      4) If it clearly mentions another sport and has no hoops signal -> drop.
    """
    blob = f"{to_text(title)}\n{to_text(summary)}"
    name = to_text(feed.get("name", ""))

    # 1) hard block explicit WBB when no men's signal
    if RE_WOMEN.search(blob) and not RE_MEN.search(blob):
        return False

    purdueish = RE_PU.search(blob) or RE_PLAYER.search(blob) or ("purdue" in name.lower()) or bool(feed.get("trust"))
    hoopsish  = RE_BBALL.search(blob) or RE_PLAYER.search(blob) or re.search(r"\bmatt\s+painter\b", blob, re.I)

    if not purdueish or not hoopsish:
        return False

    if RE_OTHERS.search(blob) and not (RE_BBALL.search(blob) or RE_PLAYER.search(blob)):
        return False

    return True

# -------------------- main collect --------------------

def collect():
    seen, out = set(), []
    per = {}

    for feed in FEEDS:
        name = to_text(feed.get("name", "Feed"))
        per[name] = 0
        try:
            fetcher = FETCHERS.get(feed.get("type", "rss"), fetch_rss)
            items = fetcher(feed)
        except Exception:
            # network/parse hiccup: skip this feed
            continue

        for it in items:
            title = to_text(it.get("title", "")).strip()
            link  = to_text(it.get("link", "")).strip()
            if not title or not link:
                continue
            summary = to_text(it.get("summary", ""))

            if not allow_item(title, summary, feed):
                continue

            uid = hash_id(link, title)
            if uid in seen:
                continue
            seen.add(uid)
            per[name] += 1
            out.append({
                "id": uid,
                "title": title,
                "link": link,
                "summary": summary,
                "source": name,
                "date": to_text(it.get("date", "")),
            })

    # Sort newest first (best-effort; feedparser already normalizes many)
    def when(x):
        d = to_text(x.get("date", ""))
        # Normalize common ISO 'Z'
        d = d.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(d)
        except Exception:
            # Last resort: push undated items to the bottom
            return datetime(1970, 1, 1, tzinfo=timezone.utc)

    out.sort(key=when, reverse=True)
    out = out[:MAX_ITEMS]

    meta = {
        "generated_at": now_iso(),
        "items_count": len(out),
        "items_mtime": now_iso(),
        "last_run": {
            "ok": True,
            "rc": 0,
            "final_count": len(out),
            "per_feed_counts": per,
            "ts": now_iso(),
        },
    }

    with open(ITEMS_PATH, "w", encoding="utf-8") as f:
        json.dump({"items": out, "meta": meta}, f, ensure_ascii=False)

    return len(out)

if __name__ == "__main__":
    n = collect()
    print(json.dumps({"ok": True, "count": n, "ts": now_iso()}))
