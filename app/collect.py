# app/collect.py
import time, re, html, hashlib
from typing import List, Dict, Any
import feedparser
import requests

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
REQ_TIMEOUT = (6, 15)

SOURCES: List[Dict[str, str]] = [
    {"name": "Google News", "url": "https://news.google.com/rss/search?q=%22Purdue%22%20%22men%27s%20basketball%22&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Hammer & Rails", "url": "https://www.hammerandrails.com/rss/index.xml"},
    {"name": "Reddit r/Boilermakers", "url": "https://www.reddit.com/r/Boilermakers/search.rss?q=men%27s%20basketball&restrict_sr=on&sort=new&t=month"},
    {"name": "Reddit r/PurdueBasketball", "url": "https://www.reddit.com/r/PurdueBasketball/.rss"},
]

POSITIVE = [
    "men's basketball","purdue basketball","purdue men's","boilermakers",
    "mackey","big ten","ncaa","matt painter","braden smith","fletcher loyer",
    "caleb furst","trey kaufman","will berg","jack benter"
]
REQUIRE_PURDUE = True

def _clean_text(s: str) -> str:
    if not s: return ""
    t = html.unescape(html.unescape(s))
    t = re.sub(r"<[^>]+>", " ", t, flags=re.S)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _epoch(e: Any) -> int:
    for k in ("published_parsed","updated_parsed","created_parsed"):
        v = e.get(k)
        if v:
            try: return int(time.mktime(v))
            except Exception: pass
    return int(time.time())

def _fetch_bytes(url: str) -> bytes:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        return r.content
    except Exception:
        return b""

def _parse_rss(url: str):
    blob = _fetch_bytes(url)
    if blob:
        return feedparser.parse(blob)
    return feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})

def _is_relevant(title: str, summary: str, source_name: str) -> bool:
    T = f"{title} {summary}".lower()
    source_is_purdue = any(sn in source_name.lower() for sn in ["hammer & rails","purduebasketball","boilermakers"])
    if REQUIRE_PURDUE and not source_is_purdue and "purdue" not in T:
        return False
    if any(k in T for k in POSITIVE): return True
    if "basketball" in T and "purdue" in T: return True
    return False

def collect_all() -> Dict[str, Any]:
    seen = set()
    items = []
    sources_state = []

    for src in SOURCES:
        name, url = src["name"], src["url"]
        kept = 0; fetched = 0
        try:
            d = _parse_rss(url)
            entries = d.entries or []
            fetched = len(entries)
            for e in entries:
                title = _clean_text(getattr(e,"title","") or e.get("title",""))
                link = (getattr(e,"link","") or e.get("link","") or "").strip()

                raw = e.get("summary","") or e.get("description","")
                if not raw and e.get("content"):
                    try: raw = e["content"][0].get("value","")
                    except Exception: pass
                summary_text = _clean_text(raw)  # ✅ no HTML

                if not link:
                    link = "about:blank#" + hashlib.md5((title+summary_text).encode("utf-8")).hexdigest()
                if not title and summary_text:
                    title = summary_text[:120] + "…"

                if not _is_relevant(title, summary_text, name):
                    continue

                key = (name, link)
                if key in seen: continue
                seen.add(key)

                items.append({
                    "title": title,
                    "link": link,
                    "source": name,
                    "summary_text": summary_text,  # cleaned
                    "published_ts": _epoch(e),
                })
                kept += 1
        except Exception:
            pass

        sources_state.append({"name": name, "url": url, "fetched": fetched, "kept": kept})

    items.sort(key=lambda x: x.get("published_ts",0), reverse=True)

    return {"count": len(items), "items": items, "sources": sources_state, "updated": int(time.time())}

def collect_debug() -> Dict[str, Any]:
    return collect_all()
