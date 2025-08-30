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

from feeds import FEEDS  # your existing sources list

# ---- MEN'S MBB FILTER (lenient & safe) --------------------------------------

PLAYERS = [
  "braden smith","fletcher loyer","trey kaufman","trey kaufman-renn","mason gillis",
  "caleb furst","myles colvin","camden heide","will berg","jack benter",
  "daniel jacobsen","levi cook","matt painter","zach edey","omer mayer","omas mayer"
]

INCLUDE_HINTS = [
  r"\bpurdue\b", r"\bboilers?\b", r"\bboilermakers?\b",
  r"\bmen'?s?\s+basketball\b", r"\bmbb\b", r"\bmackey\b", r"\bbig ten\b",
] + [re.escape(n) for n in PLAYERS]

WOMENS_TERMS = [r"\bwomen'?s\b", r"\bwbb\b", r"\bwbk\b", r"\blady\b", r"\bwnba\b"]
NON_MBB = [
  r"\bfootball\b", r"\bvolleyball\b", r"\bbaseball\b", r"\bsoccer\b", r"\bwrestling\b",
  r"\bsoftball\b", r"\btrack\b", r"\bcross[- ]country\b", r"\bgolf\b", r"\bswim(ming)?\b",
]

INCLUDE_RE = re.compile("|".join(INCLUDE_HINTS), re.I)
WOMENS_RE  = re.compile("|".join(WOMENS_TERMS), re.I)
NON_MBB_RE = re.compile("|".join(NON_MBB), re.I)

def to_text(x):
  if not x: return ""
  return html.unescape(x if isinstance(x,str) else x.decode("utf-8","ignore"))

def men_only_ok(title, summary):
  """Allow Purdue MBB; exclude obvious other sports; be careful with WBB."""
  blob = f"{to_text(title)}\n{to_text(summary)}"
  # other sports out
  if NON_MBB_RE.search(blob): 
    return False
  # women's markers only block if no men/MBB signal is present
  if WOMENS_RE.search(blob) and not re.search(r"\bmen'?s?\b|\bmbb\b|\bmen'?s?\s+basketball\b", blob, re.I):
    return False
  # must be Purdue/MBB relevant
  return bool(INCLUDE_RE.search(blob))

def now_utc_iso():
  return datetime.now(timezone.utc).isoformat(timespec="seconds")

def http_get(url, headers=None, timeout=18):
  req = urllib.request.Request(url, headers=headers or {"User-Agent":"Mozilla/5.0"})
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read()

def parse_rss(xml_bytes):
  root = ET.fromstring(xml_bytes)
  out = []
  for it in root.findall(".//item"):
    out.append({
      "title": (it.findtext("title") or "").strip(),
      "link":  (it.findtext("link") or "").strip(),
      "summary": (it.findtext("description") or "").strip(),
      "date": (it.findtext("pubDate") or it.findtext("published") or "").strip(),
    })
  return out

def fetch_google(f): return parse_rss(http_get(f["url"]))
def fetch_bing(f):   return parse_rss(http_get(f["url"]))
def fetch_youtube(f):return parse_rss(http_get(f["url"]))  # titles vary; filter handles it
def fetch_reddit(f):
  j = json.loads(to_text(http_get(f["url"], headers={"User-Agent":"mmblite/1.0"})))
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
  "google": fetch_google,
  "bing":   fetch_bing,
  "youtube":fetch_youtube,
  "reddit": fetch_reddit,
  "rss":    lambda f: parse_rss(http_get(f["url"]))
}

def hash_id(link, title):
  h = hashlib.sha1()
  h.update(to_text(link).encode("utf-8"))
  h.update(to_text(title).encode("utf-8"))
  return h.hexdigest()[:16]

def collect():
  seen = set(); items_out = []; per_counts = {}
  for feed in FEEDS:
    name = feed.get("name","Feed")
    kind = feed.get("type","rss")
    per_counts[name] = 0
    try:
      raw = FETCHERS.get(kind, FETCHERS["rss"])(feed)
    except Exception:
      continue
    for it in raw:
      title = to_text(it.get("title","")).strip()
      link  = to_text(it.get("link","")).strip()
      summary = to_text(it.get("summary","")).strip()
      if not title or not link: 
        continue
      if not men_only_ok(title, summary):
        continue
      uid = hash_id(link, title)
      if uid in seen:
        continue
      seen.add(uid)
      per_counts[name] += 1
      items_out.append({
        "id": uid, "title": title, "link": link, "summary": summary,
        "source": name, "date": it.get("date","")
      })

  # newest first
  def sort_key(x):
    d = x.get("date","")
    try:
      return datetime.fromisoformat(d.replace("Z","+00:00"))
    except:
      for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"):
        try: return datetime.strptime(d, fmt)
        except: pass
      return datetime.now(timezone.utc)

  items_out.sort(key=sort_key, reverse=True)
  items_out = items_out[:MAX_ITEMS]

  meta = {
    "generated_at": now_utc_iso(),
    "items_count": len(items_out),
    "items_mtime": now_utc_iso(),
    "last_run": {"ok":True,"rc":0,"final_count":len(items_out),"per_feed_counts":per_counts,"ts":now_utc_iso()},
  }
  with open(ITEMS_PATH, "w", encoding="utf-8") as f:
    json.dump({"items":items_out, "meta":meta}, f, ensure_ascii=False)
  return len(items_out)

if __name__ == "__main__":
  n = collect()
  print(json.dumps({"ok":True,"count":n,"ts":now_utc_iso()}))
