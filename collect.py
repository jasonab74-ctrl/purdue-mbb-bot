#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, html, hashlib, time, tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from json import JSONDecodeError

ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")
MAX_ITEMS  = int(os.environ.get("MAX_ITEMS", "500"))
TIMEOUT    = 18

from feeds import FEEDS

# -------------------- helpers --------------------

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def http_get(url, headers=None, timeout=TIMEOUT):
    req = Request(url, headers=headers or {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) MBBFeedBot/1.4"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()

def to_text(x):
    if not x: return ""
    return html.unescape(x if isinstance(x,str) else x.decode("utf-8","ignore"))

_TAG_RE   = re.compile(r"<[^>]+>")
_WS_RE    = re.compile(r"\s+")
def strip_html(s: str) -> str:
    """Remove all HTML tags and collapse whitespace."""
    if not s: return ""
    s = to_text(s)
    s = _TAG_RE.sub(" ", s)              # drop tags
    s = html.unescape(s)                 # decode entities
    s = _WS_RE.sub(" ", s).strip()       # tidy spaces/newlines
    return s

def tidy_summary(raw: str, limit: int = 300) -> str:
    """Plain-text summary, trimmed; no <a href=...> junk."""
    txt = strip_html(raw)
    # common boilerplate endings
    for bad in ("Continue reading", "Read more", "The post", "Originally appeared on"):
        txt = re.sub(rf"{re.escape(bad)}.*$", "", txt, flags=re.I).strip()
    if len(txt) > limit:
        txt = txt[:limit].rsplit(" ", 1)[0].rstrip() + "…"
    return txt

def normalize_link(link: str) -> str:
    """
    Keep links stable, but if it's a Google News redirect with a 'url=' param,
    expose the destination for a cleaner preview.
    """
    if not link: return ""
    try:
        u = urlparse(link)
        if ("news.google." in u.netloc) and ("url=" in link):
            qs = parse_qs(u.query)
            dest = qs.get("url", [None])[0]
            if dest: return dest
    except Exception:
        pass
    return link

def parse_rss(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        link  = (it.findtext("link")  or "").strip()
        desc  = (it.findtext("description") or it.findtext("content") or "").strip()
        pub   = (it.findtext("pubDate") or it.findtext("published") or "").strip()
        out.append({
            "title": title,
            "link":  normalize_link(link),
            "summary": tidy_summary(desc),
            "date": pub
        })
    return out

def fetch_google(f):  return parse_rss(http_get(f["url"]))
def fetch_bing(f):    return parse_rss(http_get(f["url"]))
def fetch_rss(f):     return parse_rss(http_get(f["url"]))

def fetch_reddit(f):
    """
    Support both JSON and RSS endpoints; never propagate exceptions.
    """
    url = f["url"]
    try:
        if url.endswith(".rss"):
            return parse_rss(http_get(url, headers={"User-Agent":"mmblite/1.0"}))
        raw = http_get(url, headers={"User-Agent":"mmblite/1.0"})
        j = json.loads(to_text(raw))
        out = []
        for c in j.get("data",{}).get("children",[]):
            p = c.get("data",{})
            out.append({
                "title": p.get("title",""),
                "link":  normalize_link(p.get("url","") or ("https://reddit.com" + p.get("permalink",""))),
                "summary": tidy_summary(p.get("selftext","")),
                "date": datetime.fromtimestamp(p.get("created_utc",0), tz=timezone.utc).isoformat(),
            })
        return out
    except (JSONDecodeError, ET.ParseError, Exception):
        try:
            return parse_rss(http_get(url, headers={"User-Agent":"mmblite/1.0"}))
        except Exception:
            return []

FETCHERS = {"google": fetch_google, "bing": fetch_bing, "rss": fetch_rss, "reddit": fetch_reddit}

def hash_id(link, title):
    h = hashlib.sha1()
    h.update(to_text(link).encode("utf-8"))
    h.update(to_text(title).encode("utf-8"))
    return h.hexdigest()[:16]

# -------------------- MEN’S-ONLY filter --------------------

PLAYERS = [
    "c.j. cox", "antione west", "fletcher loyer", "braden smith", "aaron fine", "jack lusk",
    "jack benter", "omer mayer", "gicarri harris", "jace rayl", "trey kaufman-renn", "liam murphy",
    "sam king", "raleigh burgess", "daniel jacobsen", "oscar cluff", "matt painter"
]

MEN_SIGNALS     = re.compile(r"\bmen'?s\b|\bmbb\b|\bmen'?s?\s+basketball\b", re.I)
PURDUE_SIGNALS  = re.compile(r"\bpurdue\b|\bboilermakers?\b|\bboilers?\b", re.I)
BASKETBALL      = re.compile(r"\bbasketball\b", re.I)
PLAYER_SIG      = re.compile("|".join(re.escape(n) for n in PLAYERS), re.I)
WOMENS          = re.compile(r"\bwomen'?s\b|\bwbb\b|\bwbk\b|\blady\b", re.I)
OTHER_SPORTS    = re.compile(r"\bfootball\b|\bvolleyball\b|\bbaseball\b|\bsoccer\b|\bwrestling\b|\bsoftball\b|\btrack\b|\bgolf\b", re.I)

TRUSTED_NAMES = None
def is_trusted(feed_name: str) -> bool:
    global TRUSTED_NAMES
    if TRUSTED_NAMES is None:
        TRUSTED_NAMES = {f["name"] for f in FEEDS if f.get("trust")}
    return feed_name in TRUSTED_NAMES

def allow_item(title, summary, feed):
    """
    Men's Purdue basketball only.
    - If the TITLE mentions another sport, require hoops signal IN THE TITLE.
    - Block explicit women's unless hoops is also clearly present.
    """
    title_t   = to_text(title)
    summary_t = to_text(summary)
    blob      = f"{title_t}\n{summary_t}"
    name      = feed.get("name","")
    trusted   = is_trusted(name)

    title_hoops = bool(BASKETBALL.search(title_t) or MEN_SIGNALS.search(title_t) or PLAYER_SIG.search(title_t))
    any_hoops   = title_hoops or bool(BASKETBALL.search(summary_t) or MEN_SIGNALS.search(summary_t) or PLAYER_SIG.search(summary_t))

    if WOMENS.search(blob) and not any_hoops: return False
    if OTHER_SPORTS.search(title_t) and not title_hoops: return False
    if OTHER_SPORTS.search(blob) and not any_hoops: return False

    if trusted:
        return bool(PURDUE_SIGNALS.search(blob) or PLAYER_SIG.search(blob) or any_hoops or "purdue" in name.lower())

    purdueish = PURDUE_SIGNALS.search(blob) or PLAYER_SIG.search(blob) or "purdue" in name.lower()
    return bool(purdueish and any_hoops)

# -------------------- collect --------------------

def collect():
    seen = set()
    out = []
    per = {}

    for feed in FEEDS:
        name = feed.get("name","Feed")
        per[name] = 0
        try:
            fetcher = FETCHERS.get(feed.get("type","rss"), fetch_rss)
            data = fetcher(feed)
        except Exception:
            continue

        for it in data:
            title = to_text(it.get("title","")).strip()
            link  = to_text(it.get("link","")).strip()
            if not title or not link:
                continue
            summary = to_text(it.get("summary",""))
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
                "summary": summary,   # already plain text from tidy_summary()
                "source": name,
                "date": it.get("date","")
            })

        time.sleep(0.1)

    # Sort newest first
    def sort_key(x):
        d = x.get("date","")
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(d.replace("Z","+0000"), fmt)
            except Exception:
                pass
        return datetime.now(timezone.utc)

    out.sort(key=sort_key, reverse=True)
    out = out[:MAX_ITEMS]

    meta = {
        "generated_at": now_iso(),
        "items_count": len(out),
        "items_mtime": now_iso(),
        "last_run": {"ok": True, "rc": 0, "final_count": len(out),
                     "per_feed_counts": per, "ts": now_iso()}
    }

    # ATOMIC WRITE
    payload = json.dumps({"items": out, "meta": meta}, ensure_ascii=False)
    dirn = os.path.dirname(ITEMS_PATH) or "."
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dirn, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name
    os.replace(tmp_path, ITEMS_PATH)

    return len(out)

if __name__ == "__main__":
    n = collect()
    print(json.dumps({"ok": True, "count": n, "ts": now_iso()}))
