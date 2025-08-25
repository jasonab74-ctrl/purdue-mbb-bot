import time
import re
import html
from typing import List, Dict, Any, Tuple
import requests
import feedparser

# --- Tunables ---------------------------------------------------------------
REQUEST_TIMEOUT = 12            # seconds per HTTP GET
TOTAL_COLLECT_BUDGET = 40       # hard cap for one full refresh
MAX_ITEMS = 200                 # keep it reasonable
USER_AGENT = "purdue-mbb-bot/1.0 (+https://github.com/yourrepo)"

# Sources (RSS/Atom) — add/remove freely. Filters below keep only MBB.
SOURCES: List[Tuple[str, str]] = [
    ("Hammer & Rails", "https://www.hammerandrails.com/rss/index.xml"),
    ("Journal & Courier Purdue", "https://rss.app/feeds/2iN67Qv7t9C1p7dS.xml"),  # fallback feed; fine if 404/slow; we'll skip.
    ("Sports Illustrated (Purdue)", "https://www.si.com/college/purdue/.rss"),
    ("Purdue Exponent", "https://www.purdueexponent.org/search/?f=atom&c=news%2Csports&t=article"),
    ("GoldandBlack", "https://www.on3.com/feeds/goldandblack/purdue/"),  # many sites block; skip on error
    # Reddit: search inside r/Boilermakers (we’ll be respectful + skip on 429)
    ("Reddit r/Boilermakers",
     "https://www.reddit.com/r/Boilermakers/search.rss?q=Purdue%20men%27s%20basketball&restrict_sr=on&sort=new&t=month"),
]

# --- Helpers ----------------------------------------------------------------

def _http_get(url: str) -> str | None:
    """Fetch text with UA + timeout. Returns response.text or None."""
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        # handle “Too Many Requests” from Reddit or others without blowing up:
        if r.status_code == 429:
            return None
        r.raise_for_status()
        ct = r.headers.get("content-type","").lower()
        # feedparser is fine with XML/Atom/HTML as text
        r.encoding = r.encoding or ("utf-8" if "charset" not in ct else None)
        return r.text
    except Exception:
        return None

def parse_rss(url: str) -> List[Dict[str, Any]]:
    """Best-effort parse of a feed URL."""
    text = _http_get(url)
    if not text:
        return []
    d = feedparser.parse(text)
    items = []
    for e in d.entries[:100]:
        title = html.unescape(getattr(e, "title", "").strip())
        link = getattr(e, "link", "").strip()
        summary = html.unescape(getattr(e, "summary", getattr(e, "description", ""))).strip()
        # Normalize published date if present
        published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
        source = getattr(d.feed, "title", "") or url
        items.append({
            "title": title, "link": link, "summary": summary,
            "published": published, "source": source
        })
    return items

# Strong “MBB-only” filter.
_NEG = re.compile(r"\b(women|wbb|football|soccer|volleyball|baseball|softball|wrestling|track|golf|tennis|swim|minors?)\b", re.I)
_POS_ANY = re.compile(r"\b(basketball|mbb|m\.?b\.?b\.?|march madness|mackey|big ten|b1g)\b", re.I)
_PURDUE = re.compile(r"\b(purdue|boilermakers?|boilers)\b", re.I)

def is_mbb(item: Dict[str, Any]) -> bool:
    text = f"{item.get('title','')} {item.get('summary','')} {item.get('link','')}"
    if _NEG.search(text):
        return False
    if _PURDUE.search(text) and _POS_ANY.search(text):
        return True
    # Allow some known sources to pass with “basketball” only
    if _POS_ANY.search(text) and any(k in (item.get("source","").lower()) for k in ("hammer & rails","journal","si.com","goldandblack","exponent")):
        return True
    return False

def collect_all() -> Dict[str, Any]:
    """Fetch from all sources with a total time budget and return curated items."""
    started = time.monotonic()
    all_items: List[Dict[str, Any]] = []
    per_source = []

    for name, url in SOURCES:
        if time.monotonic() - started > TOTAL_COLLECT_BUDGET:
            per_source.append({"name": name, "url": url, "error": "budget_exceeded"})
            break
        try:
            batch = parse_rss(url)
            kept = [x | {"source": name} for x in batch if is_mbb(x | {"source": name})]
            all_items.extend(kept)
            per_source.append({"name": name, "url": url, "fetched": len(batch), "kept": len(kept)})
        except Exception as e:
            per_source.append({"name": name, "url": url, "error": str(e)})

    # de-dup by link, keep most recent first by published text (not perfect but fine)
    seen = set()
    unique = []
    for item in all_items:
        link = item.get("link","")
        if link in seen: 
            continue
        seen.add(link)
        unique.append(item)

    # simple recency sort on string (feeds vary; we just keep the list stable)
    unique = unique[:MAX_ITEMS]
    return {
        "updated": int(time.time()),
        "count": len(unique),
        "items": unique,
        "sources": per_source,
    }

def collect_debug() -> Dict[str, Any]:
    sample = collect_all()
    return {
        "updated": sample["updated"],
        "count": sample["count"],
        "sources": sample["sources"],
        "example": sample["items"][:3],
    }
