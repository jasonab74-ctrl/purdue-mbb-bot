/* ----- 8–10 fixed Purdue MBB sources for a stable dropdown ----- */
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
  { key: 'Big Ten Network', label: 'Big Ten Network' }
];

/* DOM */
const feedEl        = document.getElementById('feed');
const sel           = document.getElementById('sourceSelect');
const updatedEl     = document.getElementById('updatedAt');
const songBtn       = document.getElementById('songBtn');
const fightAudio    = document.getElementById('fightAudio');

/* Build dropdown once */
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

/* Load items.json (cache-bust to avoid GitHub Pages stale cache) */
async function loadItems(){
  try {
    const cacheBust = `?v=${Date.now().toString().slice(0,10)}`;
    const res = await fetch(`items.json${cacheBust}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  } catch (err) {
    console.error("Failed to fetch items.json", err);
    return [];
  }
}

/* Robust date parsing */
function parseDate(d){
  if (!d) return null;
  const cleaned = typeof d === 'string' ? d.replace(/\sat\s/i, ' ') : d;
  const t = Date.parse(cleaned);
  if (!Number.isNaN(t)) return new Date(t);
  try { return new Date(cleaned); } catch { return null; }
}

function formatLocal(d){
  const opts = { year:'numeric', month:'short', day:'numeric' };
  return d.toLocaleDateString(undefined, opts);
}

/* Render feed cards */
let allItems = [];
function render(){
  const pick = sel.value;
  let items = allItems;

  if (pick && pick !== 'All sources') {
    items = items.filter(it => (it.source || '').toLowerCase() === pick.toLowerCase());
  }

  // Sort newest first
  items.sort((a,b) => (parseDate(b.isoDate || b.date) ?? 0) - (parseDate(a.isoDate || a.date) ?? 0));
  items = items.slice(0, 50);

  // Updated time
  const newest = items.find(it => parseDate(it.isoDate || it.date));
  updatedEl.textContent = newest ? formatLocal(parseDate(newest.isoDate || newest.date)) : '—';

  // Render
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
    const dt = parseDate(it.isoDate || it.date || it.pubDate);
    when.textContent = dt ? formatLocal(dt) : '—';

    meta.append(src, dot, when);
    card.append(h3, meta);
    feedEl.appendChild(card);
  }
}

/* Init */
(async function(){
  allItems = await loadItems();
  render();
})();

/* Events */
sel.addEventListener('change', render);

/* Fight song play/pause toggle */
songBtn.addEventListener('click', async () => {
  try {
    if (fightAudio.paused) {
      await fightAudio.play();
      songBtn.textContent = '❚❚ Pause';
    } else {
      fightAudio.pause();
      fightAudio.currentTime = 0;
      songBtn.textContent = '► Hail Purdue';
    }
  } catch (err) {
    alert('Could not play audio. On iPhone, make sure Silent Mode is off and tap again. Also verify static/fight-song.mp3 exists.');
  }
});
