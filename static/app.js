/* =========================================================
   Purdue MBB – minimal, hardened client logic
   Fixes:
     1) Fight song playback on iOS / odd filenames
     2) Articles list rendering & bad (1970) dates
   ========================================================= */

/* ---------- Adjustable selectors (match your DOM) ---------- */
const SELECTORS = {
  fightSongButton: '#fightSongBtn, [data-fight-song], .fight-song-btn', // your button already works; we try a few
  itemsList: '#items, #feed, .items, [data-list]',                      // container for article cards
  updatedAt: '#updatedAt, [data-updated], .updated-at',                 // “Updated:” text target
  sourceSelect: '#sourceSelect, #source, select[name="source"]'         // the Sources <select>
};

/* ---------- Utilities ---------- */
const $ = (sel) => document.querySelector(sel);

function toast(msg) {
  let t = document.getElementById('toaster');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toaster';
    Object.assign(t.style, {
      position: 'fixed', left: '50%', bottom: '18px', transform: 'translateX(-50%)',
      background: 'rgba(0,0,0,.8)', color: '#fff', padding: '10px 14px', borderRadius: '10px',
      fontSize: '14px', zIndex: 99999, maxWidth: '92%', textAlign: 'center'
    });
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.opacity = '1';
  setTimeout(() => (t.style.opacity = '0'), 2600);
}

const fmt = new Intl.DateTimeFormat('en-US', {
  month: 'short', day: 'numeric', year: 'numeric',
  hour: 'numeric', minute: '2-digit'
});

function toDate(val) {
  if (!val) return null;
  // numeric seconds or ms
  if (typeof val === 'number') {
    const ms = val < 1e12 ? val * 1000 : val;
    const d = new Date(ms);
    return isNaN(d) ? null : d;
  }
  // strings
  const d = new Date(val);
  return isNaN(d) ? null : d;
}

function normalizeDate(item) {
  const keys = ['isoDate', 'pubDate', 'published', 'date', 'updated', 'created'];
  for (const k of keys) {
    if (item[k]) {
      const d = toDate(item[k]);
      if (d) return d;
    }
  }
  return null;
}

function americanDate(d) {
  return d ? fmt.format(d) : '—';
}

/* ---------- Fight song (robust path + iOS gesture) ---------- */
const CANDIDATE_MP3S = [
  'static/hail-purdue.mp3',
  'static/fight song.MP3',
  'static/fight%20song.MP3',
  'static/fight%20song.mp3',
  'static/fight-song.mp3'
];

async function resolveAudioSrc() {
  for (const path of CANDIDATE_MP3S) {
    try {
      const res = await fetch(path, { method: 'HEAD', cache: 'no-store' });
      if (res.ok) return path;
    } catch { /* ignore */ }
  }
  return null;
}

function initFightSong() {
  const btn = document.querySelector(SELECTORS.fightSongButton);
  if (!btn) return;

  let resolved = null;

  btn.addEventListener('click', async () => {
    try {
      if (!resolved) resolved = await resolveAudioSrc();
      if (!resolved) {
        toast('Can’t find fight song in /static (try hail-purdue.mp3).');
        return;
      }
      // Must create & play inside the user gesture callback for iOS
      const a = new Audio(resolved);
      a.play().catch(() => {
        toast('Could not play audio. Ensure Silent Mode is off and tap again.');
      });
    } catch {
      toast('Could not play audio. Ensure Silent Mode is off and tap again.');
    }
  });
}

/* ---------- Articles ---------- */
const ITEMS_URL = `./items.json?v=${Date.now()}`; // cache-buster for GitHub Pages

let allItems = [];
let activeSource = 'All sources';

function renderItems() {
  const list = document.querySelector(SELECTORS.itemsList);
  if (!list) return;

  // clear
  list.innerHTML = '';

  const items = activeSource && activeSource !== 'All sources'
    ? allItems.filter(i => {
        const src = (i.source || i.site || i.feed || '').toString().trim();
        return src.toLowerCase().includes(activeSource.toLowerCase());
      })
    : allItems;

  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = 'No stories right now.';
    list.appendChild(empty);
    return;
  }

  for (const it of items) {
    const d = normalizeDate(it);
    const card = document.createElement('a');
    card.className = 'card';
    card.href = it.link || it.url || '#';
    card.target = '_blank';
    card.rel = 'noopener';

    card.innerHTML = `
      <div class="card__title">${(it.title || 'Untitled').trim()}</div>
      <div class="card__meta">
        <span>${(it.source || it.site || '—').toString()}</span>
        <span class="dot">•</span>
        <span>${americanDate(d)}</span>
      </div>
    `;
    list.appendChild(card);
  }

  // updated stamp = newest item date
  const newest = items.map(normalizeDate).filter(Boolean).sort((a,b)=>b-a)[0];
  const upEl = document.querySelector(SELECTORS.updatedAt);
  if (upEl) upEl.textContent = newest ? americanDate(newest) : '—';
}

async function loadItems() {
  try {
    const res = await fetch(ITEMS_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Accept either {items: [...]} or plain array
    const arr = Array.isArray(data) ? data : (data.items || []);
    // Normalize & sort (desc)
    allItems = arr
      .map(x => ({ ...x }))
      .sort((a, b) => {
        const da = normalizeDate(a);
        const db = normalizeDate(b);
        if (!da && !db) return 0;
        if (!da) return 1;
        if (!db) return -1;
        return db - da;
      });

    renderItems();
  } catch (e) {
    console.error('Failed to load items.json', e);
    toast('Could not load stories (items.json).');
  }
}

function initSourceSelect() {
  const sel = document.querySelector(SELECTORS.sourceSelect);
  if (!sel) return;

  // If your HTML already has <option>s, we don’t rebuild it.
  // We just react to changes.
  sel.addEventListener('change', (e) => {
    activeSource = e.target.value || 'All sources';
    renderItems();
  });
}

/* ---------- Boot ---------- */
document.addEventListener('DOMContentLoaded', () => {
  initFightSong();
  initSourceSelect();
  loadItems();
});
