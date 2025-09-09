/* Hardened frontend for GitHub Pages (no backend). */
/* Assumptions for items.json:
  [
    {
      "title": "string",
      "link": "https://…",
      "source": "Yahoo Sports",
      "published": "2025-09-08T20:09:32Z"  // ISO string OR Unix seconds OR Unix ms
    },
    …
  ]
  Optional top-level: { "generated_at": "…", "items":[…] }
*/

const CURATED_SOURCES = [
  "PurdueSports.com",
  "Journal & Courier",
  "GoldandBlack.com",
  "Hammer and Rails",
  "The Athletic",
  "ESPN",
  "Yahoo Sports",
  "Sports Illustrated",
  "CBS Sports",
  "Big Ten Network"
];

// Common aliases that appear in feeds → your desired labels
const SOURCE_ALIASES = {
  "purdue sports": "PurdueSports.com",
  "purduesports.com": "PurdueSports.com",
  "journal & courier": "Journal & Courier",
  "journal and courier": "Journal & Courier",
  "goldandblack.com": "GoldandBlack.com",
  "hammer and rails": "Hammer and Rails",
  "the athletic": "The Athletic",
  "espn": "ESPN",
  "yahoo sports": "Yahoo Sports",
  "sports illustrated": "Sports Illustrated",
  "cbs sports": "CBS Sports",
  "big ten network": "Big Ten Network",
  "google news": "Google News"
};

// Very light football filter to keep NFL/CFB out of MBB feed.
const FILTER_NON_BASKETBALL = true;
const FOOTBALL_TOKENS = [
  "football","nfl","ncaaf","saints","cardinals","colts","vikings","bears",
  "ravens","chiefs","dolphins","jets","patriots","chargers","raiders","browns",
  "cowboys","giants","packers","broncos","steelers","lions","falcons","panthers",
  "texans","jaguars","buccaneers","commanders","eagles" // ok to include; avoids NFL Eagles bleed
];

const $ = sel => document.querySelector(sel);

const els = {
  source: $("#source"),
  updated: $("#updated"),
  feed: $("#feed"),
  tpl: $("#item-tpl"),
  anthemBtn: $("#play-anthem"),
  anthem: $("#anthem")
};

// ---- Utilities -------------------------------------------------------------

function normalizeSource(name) {
  if (!name) return "";
  const k = String(name).trim().toLowerCase();
  return SOURCE_ALIASES[k] || SOURCE_ALIASES[k.replaceAll('—','-')] || capitalizeWords(k);
}

function capitalizeWords(s){
  return s.replace(/\b\w/g, c => c.toUpperCase());
}

function toDate(val) {
  if (val == null) return null;
  if (typeof val === "number") {
    // Seconds → ms
    if (val < 1e12) val = val * 1000;
    return new Date(val);
  }
  const d = new Date(String(val));
  return Number.isNaN(d.getTime()) ? null : d;
}

function fmtUS(d){
  return d.toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit"
  });
}

function isBasketball(title){
  if (!FILTER_NON_BASKETBALL || !title) return true;
  const t = title.toLowerCase();
  return !FOOTBALL_TOKENS.some(tok => t.includes(tok));
}

// ---- Sources (stable dropdown that never “rolls back”) ---------------------

function buildSourceMenu(extraSources) {
  const ALL = ["All sources", ...CURATED_SOURCES];
  const extras = (extraSources || [])
    .map(normalizeSource)
    .filter(x => x && !ALL.includes(x));
  const final = [...ALL, ...extras];

  els.source.innerHTML = "";
  for (const label of final) {
    const opt = document.createElement("option");
    opt.value = label;
    opt.textContent = label;
    els.source.appendChild(opt);
  }
}

// ---- Rendering -------------------------------------------------------------

let ALL_ITEMS = [];

function render() {
  const chosen = els.source.value || "All sources";
  els.feed.innerHTML = "";

  const items = ALL_ITEMS
    .filter(i => {
      if (!isBasketball(i.title)) return false;
      if (chosen !== "All sources") {
        return normalizeSource(i.source) === chosen;
      }
      return true;
    })
    .sort((a,b) => (b._ts - a._ts));

  if (items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "card";
    empty.textContent = "No articles yet from this source.";
    els.feed.appendChild(empty);
    return;
  }

  for (const it of items) {
    const node = document.importNode(els.tpl.content, true);
    const a = node.querySelector(".card-link");
    const h = node.querySelector(".card-title");
    const s = node.querySelector(".meta-source");
    const t = node.querySelector(".meta-date");

    a.href = it.link;
    h.textContent = it.title || "(untitled)";
    s.textContent = normalizeSource(it.source) || "—";
    t.textContent = it._date ? fmtUS(it._date) : "—";
    els.feed.appendChild(node);
  }
}

// ---- Fetch & hydrate ------------------------------------------------------

async function loadItems() {
  // Cache-bust query so GH Pages doesn’t serve stale JSON
  const url = `items.json?cb=${Date.now()}`;
  const resp = await fetch(url, {cache: "no-store"});
  const raw = await resp.json();

  const list = Array.isArray(raw) ? raw : (raw.items || []);
  const generated = Array.isArray(raw) ? null : (raw.generated_at || raw.updated_at);

  let newestTS = 0;
  const coll = [];

  for (const row of list) {
    const title = row.title || row.headline || "";
    const link = row.link || row.url || "#";
    const source = row.source || row.by || row.site || "";
    const published = (row.published ?? row.pubDate ?? row.date ?? row.time ?? null);

    const d = toDate(published);
    const ts = d ? d.getTime() : 0;
    if (ts > newestTS) newestTS = ts;

    coll.push({
      title, link, source,
      _date: d,
      _ts: ts
    });
  }

  // Keep a stable curated menu but also merge in any new sources present.
  const discovered = [...new Set(coll.map(i => normalizeSource(i.source)).filter(Boolean))];
  buildSourceMenu(discovered);

  ALL_ITEMS = coll;
  const updDate = toDate(generated) || (newestTS ? new Date(newestTS) : null);
  els.updated.textContent = updDate ? fmtUS(updDate) : "—";
  render();
}

// ---- Audio (fight song) ---------------------------------------------------

function wireAudio() {
  // iOS requires a user gesture. This button handler satisfies that.
  els.anthemBtn.addEventListener("click", async () => {
    try {
      // Always restart from the beginning
      els.anthem.pause();
      els.anthem.currentTime = 0;
      await els.anthem.play();
    } catch (err) {
      // Most common causes: silent/mute switch ON, or file path wrong.
      alert("Could not play audio. Make sure Silent Mode is OFF and tap again.");
    }
  }, {passive: true});
}

// ---- Init -----------------------------------------------------------------

function init() {
  wireAudio();
  els.source.addEventListener("change", render);
  loadItems().catch(err => {
    console.error(err);
    els.updated.textContent = "—";
    els.feed.innerHTML = `<div class="card">Couldn’t load items.json</div>`;
  });

  // Periodic refresh (hardened but gentle)
  setInterval(() => loadItems().catch(()=>{}), 5 * 60 * 1000);
}

document.addEventListener("DOMContentLoaded", init);