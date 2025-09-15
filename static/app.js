/* ====== Purdue MBB — front-end logic (stable) ====== */

/* ----- 8–10 fixed Purdue MBB sources for a stable dropdown ----- */
const SOURCES = [
  { key: 'All sources',        label: 'All sources' },
  { key: 'Yahoo Sports',       label: 'Yahoo Sports' },
  { key: 'Google News',        label: 'Google News' },
  { key: 'Hammer and Rails',   label: 'Hammer and Rails' },
  { key: 'ESPN',               label: 'ESPN' },
  { key: 'Sports Illustrated', label: 'Sports Illustrated' },
  { key: 'Journal & Courier',  label: 'Journal & Courier' },
  { key: 'GoldandBlack',       label: 'GoldandBlack' },
  { key: 'The Athletic',       label: 'The Athletic' },
  { key: 'CBS Sports',         label: 'CBS Sports' },
  { key: 'Big Ten Network',    label: 'Big Ten Network' }
];

/* ----- DOM ----- */
const feedEl     = document.getElementById('feed');
const sel        = document.getElementById('sourceSelect');
const updatedEl  = document.getElementById('updatedAt');
const songBtn    = document.getElementById('songBtn');
const fightAudio = document.getElementById('fightAudio');

/* Build dropdown once (fixed list; never “disappears”) */
(function buildDropdown () {
  if (!sel) return;
  sel.innerHTML = '';
  for (const s of SOURCES) {
    const opt = document.createElement('option');
    opt.value = s.key;
    opt.textContent = s.label;
    sel.appendChild(opt);
  }
  sel.value = 'All sources';
})();

/* Load items.json (cache-bust to dodge GH Pages caching) */
async function loadItems () {
  const cacheBust = `?v=${Date.now().toString().slice(0, 10)}`;
  const res = await fetch(`items.json${cacheBust}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : (data.items || []);
}

/* ---------- Robust date handling ---------- */

function parseEpochMaybe(value) {
  // Accept number or numeric string; detect seconds vs ms
  const n = typeof value === 'number' ? value : Number(String(value).trim());
  if (!Number.isFinite(n)) return null;
  const ms = n < 1e12 ? n * 1000 : n; // treat 10-digit as seconds
  const d = new Date(ms);
  return Number.isNaN(d.getTime()) ? null : d;
}

function parseDateString(value) {
  if (!value) return null;
  const s = String(value).replace(/\sat\s/i, ' '); // "Sep 9, 2025 at 4:04 PM" -> "Sep 9, 2025 4:04 PM"
  const t = Date.parse(s);
  if (!Number.isNaN(t)) return new Date(t);
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Try many common keys; support strings and epoch timestamps */
function getItemDate(it) {
  if (!it || typeof it !== 'object') return null;

  const candidates = [
    it.isoDate,
    it.date,
    it.pubDate,
    it.published,
    it.published_at,
    it.updated,
    it.created,
    it.time,
    it.timestamp
  ];

  for (const c of candidates) {
    if (c == null || c === '') continue;

    // Fast path for numbers or numeric strings (epoch)
    const ep = parseEpochMaybe(c);
    if (ep) return ep;

    // Otherwise try flexible string parsing
    const ds = parseDateString(c);
    if (ds) return ds;
  }

  return null;
}

/* Format like: Sep 9, 2025, 4:04 PM (US, no seconds) */
function formatLocal (d) {
  const date = d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
  const time = d.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit'
  });
  return `${date}, ${time}`;
}

/* ---------- Render ---------- */
let allItems = [];

function render () {
  if (!feedEl) return;

  const pick = sel ? sel.value : 'All sources';
  let items = allItems;

  if (pick && pick !== 'All sources') {
    const want = pick.toLowerCase();
    items = items.filter(it => (it.source || '').toLowerCase() === want);
  }

  // Sort newest → oldest using robust date getter
  items.sort((a, b) => {
    const da = getItemDate(a);
    const db = getItemDate(b);
    const ta = da ? da.getTime() : 0;
    const tb = db ? db.getTime() : 0;
    return tb - ta;
  });

  // Cap to most recent 50
  items = items.slice(0, 50);

  // Updated label = newest item date (fallback em dash)
  const newest = items.find(it => getItemDate(it));
  if (updatedEl) {
    updatedEl.textContent = newest ? formatLocal(getItemDate(newest)) : '—';
  }

  // Build cards
  feedEl.innerHTML = '';
  for (const it of items) {
    const card = document.createElement('article');
    card.className = 'card';

    const h3 = document.createElement('h3');
    h3.className = 'item-title';

    const a = document.createElement('a');
    a.href = it.link;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = it.title || 'Untitled';

    h3.appendChild(a);

    const meta = document.createElement('div');
    meta.className = 'meta';

    const src = document.createElement('span');
    src.textContent = it.source || '—';

    const dot = document.createElement('span');
    dot.textContent = ' • ';

    const when = document.createElement('time');
    const d = getItemDate(it);
    when.dateTime = d ? d.toISOString() : '';
    when.textContent = d ? formatLocal(d) : '—';

    meta.append(src, dot, when);
    card.append(h3, meta);
    feedEl.appendChild(card);
  }
}

/* ---------- Init ---------- */
(async function init () {
  try {
    allItems = await loadItems();
  } catch (e) {
    console.error('Failed to load items.json', e);
    allItems = [];
  }
  render();
})();

/* ---------- Interactions ---------- */
if (sel) sel.addEventListener('change', render);

/* Fight song: play / pause toggle (and allow pausing) */
if (songBtn && fightAudio) {
  songBtn.addEventListener('click', async () => {
    try {
      if (fightAudio.paused) {
        await fightAudio.play();
        songBtn.setAttribute('aria-pressed', 'true');
        const icon = songBtn.querySelector('.pill__icon');
        if (icon) icon.textContent = '❚❚';
        const label = songBtn.querySelector('.pill__label');
        if (label) label.textContent = 'Pause';
      } else {
        fightAudio.pause();
        fightAudio.currentTime = 0;
        songBtn.setAttribute('aria-pressed', 'false');
        const icon = songBtn.querySelector('.pill__icon');
        if (icon) icon.textContent = '►';
        const label = songBtn.querySelector('.pill__label');
        if (label) label.textContent = 'Hail Purdue';
      }
    } catch (err) {
      alert('Could not play audio. On iPhone, make sure Silent Mode is off and tap again. Also verify that static/fight-song.mp3 exists.');
      console.warn(err);
    }
  });
}
