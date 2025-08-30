#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, time, hashlib, html
from datetime import datetime, timezone
from urllib.parse import urlencode
import urllib.request
import xml.etree.ElementTree as ET

ITEMS_PATH = os.environ.get("ITEMS_PATH", "items.json")
FRESH_DAYS  = int(os.environ.get("FRESH_DAYS", "365"))
MAX_ITEMS   = int(os.environ.get("MAX_ITEMS", "400"))

# --------------------------------------------------------------------
# Feeds config is imported (your existing file with sources & playlists)
# --------------------------------------------------------------------
from feeds import FEEDS   # list of dicts: {name, type, url, kind, ...}

# --------------------------------------------------------------------
# Keywords (MEN ONLY filter done carefully)
# --------------------------------------------------------------------
PLAYERS = [
  # core/current + recent Purdue MBB names (extend as needed)
  "braden smith","fletcher loyer","trey kaufman","trey kaufman-renn","mason gillis",
  "caleb furst","myles colvin","camden heide","will berg","jack benter",
  "daniel jacobsen","levi cook","omas mayer","omer mayer","zach edey","matt painter"
]

INCLUDE_HINTS = [
  r"\bpurdue\b", r"\bboilers?\b", r"\bboilermakers?\b",
  r"\bmen'?s?\s+basketball\b", r"\bmbb\b", r"\bbig ten\b", r"\bmackey\b",
] + [re.escape(n) for n in PLAYERS]

# Strong women-only markers
WOMENS_TERMS = [
  r"\bwomen'?s\b", r"\bwbb\b", r"\bwbk\b", r"\blady\b", r"\bwnba\b",
]

# Non-MBB sports to exclude
NON_MBB = [
  r"\bfootball\b", r"\bvolleyball\b", r"\bbaseball\b", r"\bsoccer\b", r"\bwrestling\b",
  r"\bsoftball\b", r"\btrack\b", r"\bcross[- ]country\b", r"\bgolf\b", r"\bswim(ming)?\b",
]

INCLUDE_RE = re.compile("|".join(INCLUDE_HINTS), re.I)
WOMENS_RE  = re.compile("|".join(WOMENS_TERMS), re.I)
NON_MBB_RE = re.compile("|".join(NON_MBB), re.I)

def now_utc_iso():
  return datetime.now(timezone.utc).isoformat(timespec="seconds")

def http_get(url, headers=None, timeout=18):
  req = urllib.request.Request(url, headers=headers or {"User-Agent":"Mozilla/5.0"})
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read()

def to_text(x):
  if not x: return ""
  return html.unescape(x if isinstance(x,str) else x.decode("utf-8","ignore"))

def article_ok(title, summary):
  """Return True for Purdue MBB items only, with safe women filter."""
  t = to_text(title)
  s = to_text(summary)
  blob = f"{t}\n{s}"

  # Hard exclude other sports
  if NON_MBB_RE.search(blob): 
    return False

  # If it clearly mentions women's-only markers AND does NOT contain men/MBB signals, drop it.
  if WOMENS_RE.search(blob):
    if not re.search(r"\bmen'?s?\b|\bmbb\b|\bmen'?s?\s+basketball\b", blob, re.I):
      return False  # women's only

  # Require general Purdue/MBB relevance
  if not INCLUDE_RE.search(blob):
    return False

  return True

def hash_id(link, title):
  h = hashlib.sha1()
  h.update(to_text(link).encode("utf-8"))
  h.update(to_text(title).encode("utf-8"))
  return h.hexdigest()[:16]

# --------------------------------------------------------------------
# Feed readers (Google/Bing News RSS, YouTube RSS, Reddit JSON, generic RSS)
# --------------------------------------------------------------------

def parse_rss(xml_bytes):
  root = ET.fromstring(xml_bytes)
  ns = {"content":"http://purl.org/rss/1.0/modules/content/"}
  items = []
  for it in root.findall(".//item"):
    title = (it.findtext("title") or "").strip()
    link  = (it.findtext("link") or "").strip()
    desc  = (it.findtext("description") or "").strip()
    pub   = (it.findtext("pubDate") or it.findtext("published") or "").strip()
    items.append({"title":title, "link":link, "summary":desc, "date":pub})
  return items

def fetch_google_news(feed):
  data = http_get(feed["url"])
  return parse_rss(data)

def fetch_bing_news(feed):
  data = http_get(feed["url"])
  return parse_rss(data)

def fetch_youtube(feed):
  data = http_get(feed["url"])
  items = parse_rss(data)
  # YouTube titles sometimes lack Purdue—let filter decide
  return items

def fetch_reddit(feed):
  data = http_get(feed["url"], headers={"User-Agent":"mmblite/1.0"})
  j = json.loads(to_text(data))
  out = []
  for c in j.get("data",{}).get("children",[]):
    p = c.get("data",{})
    out.append({
      "title": p.get("title",""),
      "link":  p.get("url",""),
      "summary": p.get("selftext",""),
      "date": datetime.fromtimestamp(p.get("created_utc",0), tz=timezone.utc).isoformat()
    })
  return out

FETCHERS = {
  "google": fetch_google_news,
  "bing":   fetch_bing_news,
  "youtube":fetch_youtube,
  "reddit": fetch_reddit,
  "rss":    lambda f: parse_rss(http_get(f["url"])),
}

# --------------------------------------------------------------------
# Collect
# --------------------------------------------------------------------

def collect():
  seen = set()
  out = []
  per_feed_counts = {}
  debug_titles = {"kept_titles":{}, "seen_titles":{}}

  for f in FEEDS:
    name = f.get("name","Unknown")
    ftype = f.get("type","rss")
    per_feed_counts[name] = 0
    debug_titles["kept_titles"].setdefault(name, [])
    debug_titles["seen_titles"].setdefault(name, [])

    try:
      items = FETCHERS.get(ftype, FETCHERS["rss"])(f)
    except Exception as e:
      continue

    for it in items:
      title = to_text(it.get("title","")).strip()
      link  = to_text(it.get("link","")).strip()
      summ  = to_text(it.get("summary","")).strip()

      if not title or not link: 
        continue

      debug_titles["seen_titles"][name].append(title)

      if not article_ok(title, summ):
        continue

      uid = hash_id(link, title)
      if uid in seen: 
        continue
      seen.add(uid)

      per_feed_counts[name] += 1
      debug_titles["kept_titles"][name].append(title)

      out.append({
        "id": uid,
        "title": title,
        "link": link,
        "summary": summ,
        "source": name,
        "date": it.get("date",""),
      })

  # Sort newest first (ISO or readable dates—fallback to now)
  def sort_key(x):
    d = x.get("date","")
    try:
      return datetime.fromisoformat(d.replace("Z","+00:00"))
    except:
      try: return datetime.strptime(d[:25], "%a, %d %b %Y %H:%M:%S")
      except: return datetime.now(timezone.utc)

  out.sort(key=sort_key, reverse=True)
  out = out[:MAX_ITEMS]

  # Write items.json
  meta = {
    "generated_at": now_utc_iso(),
    "items_count": len(out),
    "items_mtime": now_utc_iso(),
    "last_run": {
      "ok": True, "rc": 0, "final_count": len(out),
      "per_feed_counts": per_feed_counts,
      "debug_titles": debug_titles,
      "ts": now_utc_iso()
    }
  }

  with open(ITEMS_PATH, "w", encoding="utf-8") as f:
    json.dump({"items":out, "meta":meta}, f, ensure_ascii=False)

  return len(out)

if __name__ == "__main__":
  n = collect()
  print(json.dumps({"ok":True,"count":n,"ts":now_utc_iso()}))
