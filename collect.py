#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, html, hashlib, time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")
MAX_ITEMS  = int(os.environ.get("MAX_ITEMS", "500"))
TIMEOUT    = 18

from feeds import FEEDS

# -------------------- helpers --------------------

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def http_get(url, headers=None, timeout=TIMEOUT):
    req = Request(url, headers=headers or {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) MBBFeedBot/1.2"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()

def to_text(x):
    if not x: return ""
    return html.unescape(x if isinstance(x,str) else x.decode("utf-8","ignore"))

def parse_rss(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.findall(".//item"):
        out.append({
            "title": (it.findtext("title") or "").strip(),
            "link":  (it.findtext("link") or "").strip(),
            "summary": (it.findtext("description") or it.findtext("content") or "").strip(),
            "date": (it.findtext("pubDate") or it.findtext("published") or "").strip(),
        })
    return out

def fetch_google(f):  return parse_rss(http_get(f["url"]))
def fetch_bing(f):    return parse_rss(http_get(f["url"]))
def fetch_rss(f):     return parse_rss(http_get(f["url"]))
def fetch_reddit(f):
    # Only used if a feed has type "reddit" (JSON). Our current reddit feeds are RSS, which go through fetch_rss.
    j = json.loads(to_text(http_get(f["url"], headers={"User-Agent":"mmblite/1.0"})))
    out = []
    for c in j.get("data",{}).get("children",[]):
        p = c.get("data",{})
        out.append({
            "title": p.get("title",""),
            "link":  p.get("url","") or ("https://reddit.com" + p.get("permalink","")),
            "summary": p.get("selftext",""),
            "date": datetime.fromtimestamp(p.get("created_utc",0), tz=timezone.utc).isoformat(),
        })
    return out

FETCHERS = {"google": fetch_google, "bing": fetch_bing, "rss": fetch_rss, "reddit": fetch_reddit}

def hash_id(link, title):
    h = hashlib.sha1()
    h.update(to_text(link).encode("utf-8"))
    h.update(to_text(title).encode("utf-8"))
    return h.hexdigest()[:16]

# -------------------- MEN’S-ONLY filter (balanced) --------------------

PLAYERS = [
    "c.j. cox","antione west","fletcher loyer","braden smith","aaron fine","jack lusk",
    "jack benter","omer mayer","gicarri harris","jace rayl","trey kaufman-renn","liam murphy",
    "sam king","raleigh burgess","daniel jacobsen","oscar cluff","matt painter"
]

MEN_SIG        = re.compile(r"\bmen'?s\b|\bmbb\b|\bmen'?s?\s+basketball\b", re.I)
PURDUE_SIG     = re.compile(r"\bpurdue\b|\bboilermakers?\b|\bboilers?\b", re.I)
BASKETBALL     = re.compile(r"\bbasketball\b", re.I)
PLAYER_SIG     = re.compile("|".join(re.escape(n) for n in PLAYERS), re.I)
WOMENS         = re.compile(r"\bwomen'?s\b|\bwbb\b|\bwbk\b|\blady\b", re.I)
OTHER_SPORTS   = re.compile(r"\bfootball\b|\bvolleyball\b|\bbaseball\b|\bsoccer\b|\bwrestling\b|\bsoftball\b|\btrack\b|\bgolf\b", re.I)

TRUSTED_NAMES = None
def is_trusted(feed_name: str) -> bool:
    global TRUSTED_NAMES
    if TRUSTED_NAMES is None:
        TRUSTED_NAMES = {f["name"] for f in FEEDS if f.get("trust")}
    return feed_name in TRUSTED_NAMES

def allow_item(title, summary, feed):
    """
    Pass only Purdue men's basketball content.
    Rules:
      - Hard-block explicit women’s markers.
      - If the TITLE mentions another sport, require a hoops signal IN THE TITLE.
      - Otherwise require: (Purdue-ish) AND (Hoops-ish) somewhere in title+summary or feed name.
      - Trusted feeds can pass with weaker hoops check, but still must be Purdue-ish and not another sport title.
    """
    name = feed.get("name","")
    lname = name.lower()

    title_t   = to_text(title)
    summary_t = to_text(summary)
    blob      = f"{title_t}\n{summary_t}"

    purdueish = bool(PURDUE_SIG.search(blob) or PLAYER_SIG.search(blob) or "purdue" in lname)
    hoopsish_title = bool(BASKETBALL.search(title_t) or MEN_SIG.search(title_t) or PLAYER_SIG.search(title_t) or "mbb" in lname)
    hoopsish_any   = bool(BASKETBALL.search(blob) or MEN_SIG.search(blob) or PLAYER_SIG.search(blob) or "mbb" in lname)

    # 1) explicit women's → reject
    if WOMENS.search(blob):
        return False

    # 2) title says another sport → only pass if title is clearly hoops too
    if OTHER_SPORTS.search(title_t) and not hoopsish_title:
        return False

    # 3) trusted feeds: lighter requirement but still Purdue-ish and not off-sport
    if is_trusted(name):
        return purdueish and (hoopsish_any or hoopsish_title)

    # 4) default requirement
    return purdueish and hoopsish_any

# -------------------- collect --------------------

def collect():
    seen = set()
    out = []
    per = {}

    for feed in FEEDS:
        name = feed.get("name","Feed")
        per[name] = 0
        try:
            data = FETCHERS.get(feed.get("type","rss"), fetch_rss)(feed)
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
                "id": uid, "title": title, "link": link, "summary": summary,
                "source": name, "date": it.get("date","")
            })

        time.sleep(0.1)

    # sort newest first (best-effort)
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
        "last_run": {"ok": True, "rc": 0, "final_count": len(out), "per_feed_counts": per, "ts": now_iso()}
    }
    with open(ITEMS_PATH, "w", encoding="utf-8") as f:
        json.dump({"items": out, "meta": meta}, f, ensure_ascii=False)
    return len(out)

if __name__ == "__main__":
    n = collect()
    print(json.dumps({"ok": True, "count": n, "ts": now_iso()}))
