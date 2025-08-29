# collect.py
import json, time, hashlib, re, os
from datetime import datetime, timezone
import requests, feedparser

from feeds import FEEDS_META, KEYWORDS_POSITIVE, SPORT_TOKENS, KEYWORDS_EXCLUDE, TOTAL_CAP

OUTFILE = "items.json"
TIMEOUT = (10, 15)  # (connect, read)

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def _ts(dt_struct, fallback=None) -> float:
    try:
        return datetime(*dt_struct[:6], tzinfo=timezone.utc).timestamp()
    except Exception:
        return fallback or time.time()

def _ok(item_text: str) -> bool:
    txt = item_text.lower()
    if any(bad in txt for bad in KEYWORDS_EXCLUDE):
        return False
    # Require at least one positive AND one sport token somewhere in title/body
    pos = any(tok in txt for tok in KEYWORDS_POSITIVE)
    sporty = any(tok in txt for tok in SPORT_TOKENS)
    return pos and sporty

def _hash(link: str, title: str) -> str:
    return hashlib.sha1((link or "").encode() + (title or "").encode()).hexdigest()[:12]

def _coerce_date(entry):
    ts = None
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, key, None)
        if val:
            ts = _ts(val)
            break
    return ts or time.time()

def fetch_feed(url: str):
    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent":"Mozilla/5.0 (news-collector)"})
    r.raise_for_status()
    return feedparser.parse(r.content)

def main():
    seen = set()
    items = []

    for meta in FEEDS_META:
        try:
            parsed = fetch_feed(meta["url"])
        except Exception as e:
            print(f"[collect] ERROR {meta['name']}: {e}")
            continue

        cap = int(meta.get("cap", 40))
        count = 0
        for e in parsed.entries:
            title = _norm(getattr(e, "title", ""))
            link = _norm(getattr(e, "link", ""))
            summary = _norm(getattr(e, "summary", "")) or _norm(getattr(e, "description", ""))
            body = f"{title} {summary}"
            if not title or not link:
                continue
            if not _ok(body):
                continue
            uid = _hash(link, title)
            if uid in seen:
                continue
            seen.add(uid)
            count += 1
            items.append({
                "id": uid,
                "title": title,
                "source": meta["name"],
                "link": link,
                "summary": summary[:400],
                "date_ts": _coerce_date(e),
            })
            if count >= cap:
                break

    # Newest first
    items.sort(key=lambda x: x["date_ts"], reverse=True)
    if len(items) > TOTAL_CAP:
        items = items[:TOTAL_CAP]

    payload = {
        "topic": "Purdue Men's Basketball",
        "generated_at": int(time.time()),
        "items": items
    }
    tmp = OUTFILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, OUTFILE)
    print(f"[collect] wrote {len(items)} items to {OUTFILE}")

if __name__ == "__main__":
    main()
