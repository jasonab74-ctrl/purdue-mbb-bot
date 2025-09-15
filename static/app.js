/* ---------- Fixed Purdue MBB sources (stable dropdown) ---------- */
const SOURCES = [
  { key: 'All sources',          label: 'All sources' },
  { key: 'Yahoo Sports',         label: 'Yahoo Sports' },
  { key: 'Google News',          label: 'Google News' },
  { key: 'Hammer and Rails',     label: 'Hammer and Rails' },
  { key: 'ESPN',                 label: 'ESPN' },
  { key: 'Sports Illustrated',   label: 'Sports Illustrated' },
  { key: 'Journal & Courier',    label: 'Journal & Courier' },
  { key: 'GoldandBlack',         label: 'GoldandBlack' },
  { key: 'The Athletic',         label: 'The Athletic' },
  { key: 'CBS Sports',           label: 'CBS Sports' },
  { key: 'Big Ten Network',      label: 'Big Ten Network' },
];

/* Optional: map labels to common hostnames for better filtering */
const DOMAIN_MAP = {
  'Yahoo Sports': 'yahoo.com',
  'Google News': 'news.google.com',
  'Hammer and Rails': 'hammerandrails.com',
  'ESPN': 'espn.com',
  'Sports Illustrated': 'si.com',
  'Journal & Courier': 'jconline.com',
  'GoldandBlack': 'goldandblack.com',
  'The Athletic': 'theathletic.com',
  'CBS Sports': 'cbssports.com',
  'Big Ten Network': 'btn.com',
};

/* ---------- DOM ---------- */
const feedEl     = document.getElementById('feed');
const sel        = document.getElementById('sourceSelect');
const updatedEl  = document.getElementById('updatedAt');
const songBtn    = document.getElementById('songBtn');
const fightAudio = document.getElementById('fightAudio');

/* ---------- Build dropdown once ---------- */
(function buildDropdown(){
  sel.innerHTML = '';
  for (const s of SOURCES){
    const o = document.createElement('option');
    o.value = s.key; o.textContent = s.label;
    sel.appendChild(o);
  }
  sel.value = 'All sources';
})();

/* ---------- Load items.json (cache-busted) ---------- */
async function loadItems(){
  const res = await fetch(`./items.json?cb=${Math.floor(Date.now()/60000)}`, { cache:'no-store' });
  if (!res.ok) throw new Error(`items.json HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : (data.items || []);
}

/* ---------- Date helpers ---------- */
function parseDate(d){
  if (!d) return null;
  const s = String(d).replace(/ at /i, ' ');
  const t = Date.parse(s);
  return Number.isNaN(t) ? null : new Date(t);
}
function formatDateUS(d){
  return d.toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });
}

/* ---------- Render ---------- */
let ALL = [];
function render(){
  const pick = sel.value;
  let items = ALL.slice();

  if (pick && pick !== 'All sources'){
    items = items.filter(it => {
      const source = (it.source || '').toLowerCase();
      const host = (()=>{ try { return new URL(it.link).hostname.replace(/^www\./,''); } catch { return ''; } })();
      if (source === pick.toLowerCase()) return true;
      const domain = DOMAIN_MAP[pick];
      return domain ? host.endsWith(domain) : false;
    });
  }

  items = items
    .map(it => ({ it, dt: parseDate(it.isoDate || it.date || it.pubDate || it.published) }))
    .filter(x => x.dt instanceof Date && !Number.isNaN(x.dt.getTime()))
    .sort((a,b) => b.dt - a.dt)
    .slice(0, 50);

  updatedEl.textContent = items[0]?.dt ? formatDateUS(items[0].dt) : '—';

  feedEl.innerHTML = '';
  for (const { it, dt } of items){
    const card = document.createElement('article');
    card.className = 'card';

    const h3 = document.createElement('h3');
    h3.className = 'item-title';
    const a = document.createElement('a');
    a.href = it.link; a.target = '_blank'; a.rel = 'noopener';
    a.textContent = it.title || 'Untitled';
    h3.appendChild(a);

    const meta = document.createElement('div');
    meta.className = 'meta';
    const src = document.createElement('span');
    src.textContent = it.source || '—';
    const dot = document.createElement('span'); dot.textContent = '•';
    const time = document.createElement('time');
    time.dateTime = dt ? dt.toISOString() : '';
    time.textContent = dt ? formatDateUS(dt) : '—';

    meta.append(src, dot, time);
    card.append(h3, meta);
    feedEl.appendChild(card);
  }
}

/* ---------- Init ---------- */
(async function(){
  try{
    ALL = await loadItems();
  }catch(err){
    console.error('Failed to load items.json', err);
    ALL = [];
  }
  render();
})();
sel.addEventListener('change', render);

/* ---------- Fight song play/pause (static/fight-song.mp3) ---------- */
songBtn.addEventListener('click', async () => {
  try{
    if (fightAudio.paused) {
      await fightAudio.play();
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
  }catch(err){
    alert('Could not play audio. On iPhone, ensure Silent Mode is off and tap again. Also verify static/fight-song.mp3 exists.');
    console.warn(err);
  }
});
