/* ----- 8–10 fixed Purdue MBB sources for dropdown ----- */
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

/* Build dropdown */
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

/* Load items.json */
async function loadItems(){
  const cacheBust = `?v=${Date.now().toString().slice(0,10)}`;
  const res = await fetch(`items.json${cacheBust}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const items = await res.json();
  return Array.isArray(items) ? items : (items.items || []);
}

/* Date parsing */
function parseDate(d){
  if (!d) return null;
  const cleaned = typeof d === 'string' ? d.replace(/\sat\s/i, ' ') : d;
  const t = Date.parse(cleaned);
  if (!Number.isNaN(t)) return new Date(t);
  try { return new Date(cleaned); } catch { return null; }
}

function formatLocal(d){
  // Example: Sep 9, 2025
  return d.toLocaleDateString(undefined, { year:'numeric', month:'short', day:'numeric' });
}

/* Render feed */
let allItems = [];
function render(){
  const pick = sel.value;
  let items = allItems;

  if (pick && pick !== 'All sources') {
    items = items.filter(it => (it.source || '').toLowerCase() === pick.toLowerCase());
  }

  items.sort((a,b) => (parseDate(b.isoDate || b.date) ?? 0) - (parseDate(a.isoDate || a.date) ?? 0));
  items = items.slice(0, 50);

  const newest = items.find(it => parseDate(it.isoDate || it.date));
  updatedEl.textContent = newest ? formatLocal(parseDate(newest.isoDate || newest.date)) : '—';

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
  try {
    allItems = await loadItems();
  } catch (e) {
    console.error('Failed to load items.json', e);
    allItems = [];
  }
  render();
})();

/* Events */
sel.addEventListener('change', render);

/* Fight song toggle */
songBtn.addEventListener('click', async () => {
  try{
    if (fightAudio.paused) {
      await fightAudio.play();
      songBtn.setAttribute('aria-pressed', 'true');
      songBtn.textContent = '❚❚ Pause';
    } else {
      fightAudio.pause();
      fightAudio.currentTime = 0;
      songBtn.setAttribute('aria-pressed', 'false');
      songBtn.textContent = '► Hail Purdue';
    }
  }catch(err){
    alert('Could not play audio. On iPhone, make sure Silent Mode is off. Verify static/fight-song.mp3 exists.');
    console.warn(err);
  }
});
