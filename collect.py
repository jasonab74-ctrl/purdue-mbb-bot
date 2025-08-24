# collect.py
# Aggregates Purdue Men's Basketball news & reddit only.
# Dependencies: feedparser, requests (already in requirements.txt)

from __future__ import annotations

import os
import re
import time
import json
import math
import html
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, quote_plus

import feedparser
import requests

# ---------- Tunables ----------
MAX_ITEMS = 200
MAX_AGE_DAYS = 14

# Sources:
# - Google News RSS queries scoped to Purdue men's basketball
# - Hammer & Rails (SBNation) RSS (filtering keeps just MBB)
GOOGLE_NEWS = [
    # core queries
    "https://news.google.com/rss/search?q=Purdue%20men%27s%20basketball&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=%22Purdue%20Boilermakers%22%20men%27s%20basketball&hl=en-US&gl=US&ceid=US:en",
    # official site / beat sites via GNews
    "https://news.google.com/rss/search?q=site%3Apurduesports.com%20%22Men%27s%20Basketball%22&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=site%3Ahammerandrails.com%20Purdue%20basketball&hl=en-US&gl=US&ceid=US:en",
]

FEEDS_RSS = [
    "https://www.hammerandrails.com/rss/index.xml",  # Purdue SBNation (all sports; we filter)
]

# Reddit, no API keys required (RSS search). We still try to use a UA if provided.
REDDIT_SUBS = [
    "Purdue",
    "Boilermakers",    # exists
    "CollegeBasketball"
]

REDDIT_QUERY = "Purdue men%27s basketball OR Purdue basketball OR Boilermakers basketball"
# --------------------------------

UA = os.getenv("REDDIT_USER_AGENT") or os.getenv("USER_AGENT") or "mbb-news-bot/1.0 (+https://purdue-mbb-api.onrender.com)"
HTTP_TIMEOUT = 12

def http_get(url: str) -> requests.Response | None:
    try:
        return requests.get(url, headers={"User-Agent": UA}, timeout=HTTP_TIMEOUT)
    except Exception:
        return None

def parse_rss(url: str) -> list[dict]:
    # Prefer requests (better headers) then feedparser
    resp = http_get(url)
    if resp is None or resp.status_code != 200:
        d = feedparser.parse(url)  # feedparser will try on its own
    else:
        d = feedparser.parse(resp.content)

    items = []
    for e in d.entries:
        title = html.unescape(getattr(e, "title", "") or "").strip()
        link = (getattr(e, "link", "") or "").strip()
        summary = html.unescape(getattr(e, "summary", "") or getattr(e, "description", "") or "").strip()
        # published
        ts = None
        if getattr(e, "published_parsed", None):
            ts = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
        elif getattr(e, "updated_parsed", None):
            ts = datetime.fromtimestamp(time.mktime(e.updated_parsed), tz=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        site = clean_site(link)
        items.append({
            "title": title,
            "url": link,
            "site": site,
            "summary": strip_html(summary)[:600],
            "published": ts.isoformat(),
            "kind": "news",
        })
    return items

def reddit_search_rss(sub: str, query: str) -> str:
    # Sorted new, restricted to subreddit
    q = quote_plus(query)
    return f"https://www.reddit.com/r/{sub}/search.rss?q={q}&restrict_sr=1&sort=new"

def clean_site(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # unwrap Google News redirect if present
        if "news.google." in netloc and "url=" in url:
            # best-effort pull original link
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(url).query)
            if "url" in qs and qs["url"]:
                netloc = urlparse(qs["url"][0]).netloc.lower()
                if netloc.startswith("www."):
                    netloc = netloc[4:]
        return netloc or "unknown"
    except Exception:
        return "unknown"

def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s or "").replace("&nbsp;", " ").strip()

# ------------------ Filtering ------------------

INCLUDE_PATTS = [
    r"\bpurdue\b.*\b(basketball|boilermakers)\b",
    r"\bboilermakers\b.*\bbasketball\b",
    r"\bmen'?s?\s+basketball\b.*\bpurdue\b",
    r"\bmatt\s+painter\b",
    r"\bmackey\s+arena\b",
]

EXCLUDE_PATTS = [
    r"\bfootball\b",
    r"\bwomen'?s?\b",  # women's sports
    r"\bsoccer\b",
    r"\bvolleyball\b",
    r"\bbaseball\b",
    r"\bsoftball\b",
    r"\bwrestling\b",
    r"\btrack\b",
    r"\bcross\s*country\b",
    r"\bgolf\b",
    r"\bswim|min g\b",
    r"\btennis\b",
    r"\bhockey\b",
    r"\besports\b",
    # other Purdue campuses / unrelated
    r"\bPurdue\s+(Fort\s*Wayne|North\s*west|Calumet|Global)\b",
    r"\bFort\s*Wayne\b",
    r"\bPurdue\s*Northwest\b",
]

INC_COMP = [re.compile(p, re.I) for p in INCLUDE_PATTS]
EXC_COMP = [re.compile(p, re.I) for p in EXCLUDE_PATTS]

def is_mbb_relevant(title: str, summary: str, site: str) -> bool:
    text = f"{title} {summary}".lower()
    if any(p.search(text) for p in EXC_COMP):
        return False
    # Always allow obvious sites even with short titles
    priority_hosts = {"hammerandrails.com", "purduesports.com"}
    if site in priority_hosts and ("basketball" in text or "purdue" in text or "boilermaker" in text):
        return True
    return any(p.search(text) for p in INC_COMP)

def within_age(published_iso: str) -> bool:
    try:
        dt = datetime.fromisoformat(published_iso)
        return (datetime.now(timezone.utc) - dt) <= timedelta(days=MAX_AGE_DAYS)
    except Exception:
        return True

def dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for it in sorted(items, key=lambda x: x.get("published", ""), reverse=True):
        sig = (normalize_url(it.get("url", "")) or "") + "|" + (it.get("title", "").strip().lower())
        h = hashlib.sha1(sig.encode("utf-8")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append(it)
    return out[:MAX_ITEMS]

def normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        core = f"{p.scheme}://{p.netloc}{p.path}"
        return core.lower()
    except Exception:
        return u.lower()

# ------------------ Public API ------------------

def collect_all() -> list[dict]:
    """
    Returns an array of dicts: {title, url, site, published, kind, summary}
    """
    items: list[dict] = []
    stats = {"rss": {"ok": 0}, "reddit": {"ok": 0}}

    # Google News + RSS feeds
    for u in GOOGLE_NEWS + FEEDS_RSS:
        try:
            batch = parse_rss(u)
            stats["rss"]["ok"] += len(batch)
            items.extend(batch)
        except Exception:
            pass

    # Reddit search RSS
    for sub in REDDIT_SUBS:
        try:
            url = reddit_search_rss(sub, REDDIT_QUERY)
            batch = parse_rss(url)
            for b in batch:
                b["kind"] = "reddit"
                # reddit often puts HTML in summary; keep it short
                b["summary"] = (b.get("summary") or "")[:300]
            stats["reddit"]["ok"] += len(batch)
            items.extend(batch)
        except Exception:
            pass

    # Filter for Purdue MBB only and recent
    kept: list[dict] = []
    for it in items:
        if not within_age(it.get("published", "")):
            continue
        if is_mbb_relevant(it.get("title", ""), it.get("summary", ""), it.get("site", "")):
            kept.append(it)

    kept = dedupe(kept)
    return kept

def collect_debug() -> dict:
    """
    Debug payload to help /api/debug
    """
    files = []
    try:
        files = sorted(os.listdir("."))
    except Exception:
        pass

    # small sample run for counts (don’t pull everything to keep it quick)
    sample = collect_all()
    return {
        "cwd": os.getcwd(),
        "env": {"PYTHONPATH": os.environ.get("PYTHONPATH")},
        "files_in_app": files,
        "sample_count": len(sample),
        "sample_preview": sample[:5],
        "rules": {
            "include": INCLUDE_PATTS,
            "exclude": EXCLUDE_PATTS,
            "max_age_days": MAX_AGE_DAYS,
        },
    }


# Local smoke test
if __name__ == "__main__":
    data = collect_all()
    print(json.dumps({"count": len(data), "first": data[:3]}, indent=2))
