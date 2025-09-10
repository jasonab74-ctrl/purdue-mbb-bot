/* ===== Fixed Purdue MBB sources for a stable dropdown ===== */
const SOURCES = [
  { key: 'All sources', label: 'All sources' },
  { key: 'Yahoo Sports', label: 'Yahoo Sports' },
  { key: 'Google News', label: 'Google News' },
  { key: 'Hammer and Rails', label: 'Hammer and Rails' },
  { key: 'ESPN', label: 'ESPN' },
  { key: 'Sports Illustrated', label: 'Sports Illustrated' },
  { key: 'Journal & Courier', label: 'Journal & Courier' },
  { key: 'GoldandBlack', label: 'GoldandBlack' },
  { key: 'The Athletic', label: 'The Athletic' },
  { key: 'CBS Sports', label: 'CBS Sports' },
  { key: 'Big Ten Network', label: 'Big Ten Network' },
];

/* ——— Aliases so filtering works even if feed text varies slightly ——— */
const SOURCE_ALIASES = {
  'Yahoo Sports':      [/^yahoo/i],
  'Google News':       [/^google/i],
  'Hammer and Rails':  [/hammer\s*and\s*rails/i, /hammer\s*&\s*rails/i],
  'ESPN':              [/^espn/i],
  'Sports Illustrated':[/sports\s*illustrated/i, /^si\b/i],
  'Journal & Courier': [/journal/i, /courier/i],
  'GoldandBlack':      [/gold.*black/i],
  'The Athletic':      [/athletic/i],
  'CBS Sports':        [/cbs/i],
  'Big Ten Network':   [/big\s*ten.*network/i, /\bbttn?\b/i]
};

function matchesSource(itemSource, pickKey) {
  if (!itemSource) return false;
  if (pickKey === 'All sources') return true;
  const src = String(itemSource).trim();
  const tests = SOURCE_ALIASES[pickKey] || [];
  return tests.some(re => re.test(src));
}

/* ===== DOM ===== */
const feedEl     = document.getElementById('feed');
const sel        = document.getElementById('sourceSelect');
const updatedEl  = document.getElementById('updatedAt');
const songBtn    = document.getElementById('songBtn');
const fightAudio = document.getElementById('fightAudio');

/* ===== Build dropdown (never “rolls back”) ===== */
(function buildDropdown(){
  sel.innerHTML = '';
  for (const s of SOURCES) {
    const opt = document.createElement('option');
    opt.value = s.key;
    opt.textContent = s.label;
    sel.appendChild(opt);
  }
  sel.value = 'All sources';
})();

/* ===== Load items.json (cache-busted so GH Pages doesn’t serve old data) ===== */
async function loadItems(){
  const cacheBust = `?v=${Date.now().toString().slice(0,10)}`;
  const res = await fetch(`items.json${cacheBust}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : (data.items || []);
}

/* ===== Robust date parsing (kills the 1970 bug) ===== */
function parseDate(raw){
  if (!raw) return null;

  // normalize things like "Sep 9, 2025 at 4:04 PM" → "Sep 9, 2025 4:04 PM"
  const s = typeof raw === 'string' ? raw.replace(/\sat\s/i, ' ') : raw;
  const t = Date.parse(s);
  if (!Number.isNaN(t)) return new Date(t);

  try { return new Date(s); } catch { return null; }
}

/* ===== Format date: simple US style (no time) ===== */
function formatDateUS(d){
  return d.toLocaleDateString(undefined, { month:'short', day:'numeric', year:'numeric' });
}

/* ===== Render ===== */
let ALL = [];

function render(){
  const pick = sel.value;
  let items = ALL.slice();

  // Filter by selected source
  if (pick && pick !== 'All sources') {
    items = items.filter(it => matchesSource(it.source, pick));
  }

  // Sort newest first; drop anything without a valid date
  items = items
    .map(it => ({ it, dt: parseDate(it.isoDate || it.date || it.pubDate) }))
    .filter(x => x.dt instanceof Date && !Number.isNaN(x.dt.getTime()))
    .sort((a,b) => b.dt - a.dt)
    .slice(0, 50);

  // Updated = newest item date (fallback “—”)
  updatedEl.textContent = items[0]?.dt ? formatDateUS(items[0].dt) : '—';

  // Paint
  feedEl.innerHTML = '';
  for (const { it, dt } of items) {
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
    dot.textContent = '•';

    const when = document.createElement('time');
    when.dateTime = dt.toISOString();
    when.textContent = formatDateUS(dt);

    meta.append(src, dot, when);
    card.append(h3, meta);
    feedEl.appendChild(card);
  }
}

/* ===== Init ===== */
(async function(){
  try {
    ALL = await loadItems();
  } catch (e) {
    console.error('Failed to load items.json', e);
    ALL = [];
  }
  render();
})();

sel.addEventListener('change', render);

/* ===== Fight song play/pause (uses static/fight-song.mp3) ===== */
songBtn.addEventListener('click', async () => {
  try {
    if (fightAudio.paused) {
      await fightAudio.play();                     // iOS requires user tap
      songBtn.setAttribute('aria-pressed', 'true');
      songBtn.querySelector('.pill__icon').textContent = '❚❚';
      songBtn.lastElementChild.textContent = 'Pause';
    } else {
      fightAudio.pause();
      fightAudio.currentTime = 0;
      songBtn.setAttribute('aria-pressed', 'false');
      songBtn.querySelector('.pill__icon').textContent = '►';
      songBtn.lastElementChild.textContent = 'Hail Purdue';
    }
  } catch (err) {
    alert('Could not play audio. On iPhone, ensure Silent Mode is off and tap again.\nAlso verify the file is at static/fight-song.mp3');
    console.warn(err);
  }
});