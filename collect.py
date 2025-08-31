
# collect.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, html, hashlib, time, tempfile
from datetime import datetime, timezone
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

def parse_rss(xml_bytes):
    """
    Very tolerant RSS/Atom parser (title/link/summary/date)
    """
    root = ET.fromstring(xml_bytes)
    # common namespaces we might need (content:encoded, etc.)
    ns = {"content":"http://purl.org/rss/1.0/modules/content/"}
    out = []
    for it in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = (it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link  = (it.findtext("link")  or it.findtext("{http://www.w3.org/2005/Atom}link")  or "").strip()
        # Atom link may be an element with href attr
        if not link:
            lnode = it.find("{http://www.w3.org/2005/Atom}link")
            if lnode is not None:
                link = (lnode.get("href") or "").strip()

        summary = (
            it.findtext("description")
            or (it.findtext("content") or "")
            or it.findtext("{http://www.w3.org/2005/Atom}summary")
            or it.findtext("content:encoded", namespaces=ns)
            or ""
        ).strip()

        date = (
            it.findtext("pubDate")
            or it.findtext("{http://www.w3.org/2005/Atom}updated")
            or it.findtext("published")
            or it.findtext("{http://www.w3.org/2005/Atom}published")
            or ""
        ).strip()

        out.append({"title": title, "link": link, "summary": summary, "date": date})
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
                "link":  p.get("url","") or ("https://reddit.com" + p.get("permalink","")),
                "summary": p.get("selftext",""),
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

# -------------------- MEN’S-ONLY filter (stricter) --------------------

PLAYERS = [
    "c.j. cox", "antione west", "fletcher loyer", "braden smith", "aaron fine", "jack lusk",
    "jack benter", "omer mayer", "gicarri harris", "jace rayl", "trey kaufman-renn", "liam murphy",
    "sam king", "raleigh burgess", "daniel jacobsen", "oscar cluff", "matt painter", "zach edey"
]

KEY_PURDUE_TERMS = [
    "purdue", "boilermaker", "boilermakers", "mackey", "west lafayette", "men of mackey"
]

MEN_SIGNALS     = re.compile(r"\bmen'?s\b|\bmbb\b|\bmen'?s?\s+basketball\b", re.I)
PURDUE_SIGNALS  = re.compile(r"\bpurdue\b|\bboilermakers?\b|\bboilers?\b|\bmackey\b|\bwest\s+lafayette\b", re.I)
BASKETBALL      = re.compile(r"\bbasketball\b", re.I)
PLAYER_SIG      = re.compile("|".join(re.escape(n) for n in PLAYERS), re.I)
WOMENS          = re.compile(r"\bwomen'?s\b|\bwbb\b|\bwbk\b|\blady\b", re.I)
OTHER_SPORTS    = re.compile(r"\bfootball\b|\bvolleyball\b|\bbaseball\b|\bsoccer\b|\bwrestling\b|\bsoftball\b|\btrack\b|\bgolf\b", re.I)

# Headlines we see that are rarely Purdue-specific unless Purdue is explicitly named
GENERIC_LISTY   = re.compile(r"\broster\b|\bschedule\b|\bteam rankings\b|\bcommits\b|\boffers\b|\bcrystal ball\b|\btop\s+\d+\b", re.I)

# Schools/teams that commonly pollute the Purdue feed via network/team hubs; block unless Purdue is present
OTHER_SCHOOLS_HINT = re.compile(
    r"\b(iowa|butler|jacksonville state|nicholls|virginia|duke|florida|memphis|north carolina|illinois|michigan state|michigan|ohio state|wisconsin|indiana)\b",
    re.I
)

TRUSTED_NAMES = None
def is_trusted(feed_name: str) -> bool:
    global TRUSTED_NAMES
    if TRUSTED_NAMES is None:
        TRUSTED_NAMES = {f["name"] for f in FEEDS if f.get("trust")}
    return feed_name in TRUSTED_NAMES

def clearly_purdue(blob: str) -> bool:
    return bool(PURDUE_SIGNALS.search(blob) or PLAYER_SIG.search(blob))

def allow_item(title, summary, feed):
    """
    STRICT Purdue Men's Basketball filter.
    Rules (ordered, fail-fast):
      1) Block explicit women's-only if no hoops context.
      2) If another sport is present, require hoops signal IN TITLE.
      3) Require Purdue-ish AND Hoops context overall.
      4) If title looks generic list/roster, require Purdue in title (not just feed name).
      5) If other school words appear, require Purdue in title OR a Purdue player/coach.
      6) 'Trusted' feeds do NOT bypass Purdue/hoops anymore; they only skip some generic checks.
    """
    name      = feed.get("name","")
    trusted   = is_trusted(name)

    title_t   = to_text(title)
    summary_t = to_text(summary)
    blob      = f"{title_t}\n{summary_t}"

    title_hoops = bool(BASKETBALL.search(title_t) or MEN_SIGNALS.search(title_t) or PLAYER_SIG.search(title_t))
    any_hoops   = title_hoops or bool(BASKETBALL.search(summary_t) or MEN_SIGNALS.search(summary_t) or PLAYER_SIG.search(summary_t))
    purdueish   = clearly_purdue(blob) or ("purdue" in name.lower())

    # 1) women's-only -> block
    if WOMENS.search(blob) and not any_hoops:
        return False

    # 2) other sports present -> require hoops in title
    if OTHER_SPORTS.search(title_t) and not title_hoops:
        return False
    if OTHER_SPORTS.search(blob) and not any_hoops:
        return False

    # 3) must be Purdue-ish AND hoops-ish
    if not (purdueish and any_hoops):
        return False

    # 4) generic list/roster/schedule headlines need Purdue IN TITLE specifically
    if GENERIC_LISTY.search(title_t) and not re.search(r"\bpurdue\b|\bboilermakers?\b|\bmackey\b", title_t, re.I):
        return False

    # 5) other schools keywords require Purdue in title OR Purdue player/coach explicitly
    if OTHER_SCHOOLS_HINT.search(blob):
        if not (re.search(r"\bpurdue\b|\bboilermakers?\b|\bmackey\b", title_t, re.I) or PLAYER_SIG.search(blob)):
            return False

    # 6) trusted feeds: do not loosen Purdue/hoops requirement; already enforced above.
    return True

# -------------------- date handling --------------------

DATE_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %z",   # RFC822 like: Fri, 29 Aug 2025 17:25:06 +0000
    "%a, %d %b %Y %H:%M:%S %Z",   # with GMT
    "%Y-%m-%dT%H:%M:%S%z",        # ISO with tz
    "%Y-%m-%dT%H:%M:%S",          # ISO without tz
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
)

def normalize_datetime_str(d: str):
    """
    Returns (display_rfc1123, ts_int)
    If parsing fails, uses current UTC time.
    """
    if not d:
        dt = datetime.now(timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT"), int(dt.timestamp())
    zz = d.strip().replace("Z", "+0000")
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(zz, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.strftime("%a, %d %b %Y %H:%M:%S GMT"), int(dt_utc.timestamp())
        except Exception:
            continue
    # last resort: now
    dt = datetime.now(timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT"), int(dt.timestamp())

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

            disp_date, ts = normalize_datetime_str(to_text(it.get("date","")))
            per[name] += 1
            out.append({
                "id": uid,
                "title": title,
                "link": link,
                "summary": summary,
                "source": name,
                "date": disp_date,  # nice RFC1123-style string for UI
                "ts": ts            # numeric timestamp for sorting/export
            })

        time.sleep(0.08)

    # Sort newest first using ts (stable)
    out.sort(key=lambda x: int(x.get("ts", 0)), reverse=True)
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
