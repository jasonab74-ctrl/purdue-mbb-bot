/* ------------- HARDENED FRONTEND (no flip-flop) -----------------
   - Reads items.json (your Action keeps updating it)
   - Curated, stable source dropdown (8–10 Purdue MBB outlets)
   - Basketball-first filter; lightly excludes football spillover
   - US date/time; no underlines; gold cards, dark text
------------------------------------------------------------------ */

const FEED_URL = 'items.json?cache=' + Date.now();
const feedEl = document.getElementById('feed');
const updatedEl = document.getElementById('updatedTime');
const selectEl = document.getElementById('sourceSelect');
const refreshBtn = document.getElementById('refreshBtn');

/* Stable curated list shown in the dropdown, regardless of what’s inside items.json */
const CURATED_SOURCES = [
  'Hammer and Rails',
  'Journal & Courier',
  'GoldandBlack.com',
  'The Athletic',
  'ESPN',
  'Yahoo Sports',
  'Sports Illustrated',
  'CBS Sports',
  'Big Ten Network',
  '247Sports',
  'Rivals'
];

/* football-ish words we want to skip when we can */
const FOOTBALL_NO = [
  'football','qb','quarterback','touchdown','wide receiver','running back',
  'ross-ade','gridiron','nfl','colts'
];

/* basketball-ish words we’re happy to see */
const HOOPS_YES = [
  'basketball','mbb','boilers','boilermakers','purdue','big ten','painter',
  'paint crew','mackey','boiler','kenpom','ncaa tournament','bracket'
];

const audio = document.getElementById('fightSong');
const songBtn = document.getElementById('songBtn');
songBtn.addEventListener('click', async () => {
  try{
    if (audio.paused) { await audio.play(); songBtn.setAttribute('aria-pressed','true'); songBtn.querySelector('.pill-dot').textContent='⏸'; }
    else { audio.pause(); songBtn.setAttribute('aria-pressed','false'); songBtn.querySelector('.pill-dot').textContent='▶'; }
  }catch(e){ /* ignore autoplay blockers */ }
});
audio.addEventListener('ended', ()=>{ songBtn.setAttribute('aria-pressed','false'); songBtn.querySelector('.pill-dot').textContent='▶'; });

refreshBtn.addEventListener('click', () => load());

selectEl.addEventListener('change', () => {
  if (window._items) render(window._items);
});

function usTime(iso){
  const d = new Date(iso);
  if (Number.isNaN(+d)) return '—';
  return d.toLocaleString('en-US', { month:'short', day:'numeric', year:'numeric', hour:'numeric', minute:'2-digit' });
}

function looksFootball(t){
  const s = (t||'').toLowerCase();
  return FOOTBALL_NO.some(k => s.includes(k));
}
function looksHoops(t){
  const s = (t||'').toLowerCase();
  return HOOPS_YES.some(k => s.includes(k));
}

/* Gentle basketball filter:
   - Always keep if the source is one of our curated hoops outlets
   - Else keep if it looks like hoops AND not obviously football
*/
function keepItem(item){
  const src = (item.source || '').trim();
  const title = (item.title || '').trim();
  if (CURATED_SOURCES.includes(src)) return !looksFootball(title);
  return looksHoops(title) && !looksFootball(title);
}

function buildDropdown(items){
  // “All sources” + curated list (only include those that appear at least once)
  const seen = new Set(items.map(i => i.source));
  const chosen = CURATED_SOURCES.filter(s => seen.has(s));

  const opts = ['All sources', ...chosen];
  selectEl.innerHTML = opts.map(s =>
    `<option value="${s}">${s}</option>`
  ).join('');
  selectEl.value = 'All sources';
}

function render(items){
  const filter = selectEl.value;
  const list = items
    .filter(keepItem)
    .filter(i => filter === 'All sources' ? true : i.source === filter)
    .sort((a,b)=> new Date(b.published) - new Date(a.published));

  feedEl.innerHTML = list.map(i => `
    <article class="card">
      <h3><a href="${i.link}" target="_blank" rel="noopener">${i.title}</a></h3>
      <div class="meta">
        <span>${i.source || '—'}</span>
        <span class="dot">•</span>
        <time>${usTime(i.published)}</time>
      </div>
    </article>
  `).join('');

  const newest = list[0]?.published || items[0]?.published;
  updatedEl.textContent = newest ? usTime(newest) : '—';
}

async function load(){
  try{
    const res = await fetch(FEED_URL, {cache:'no-store'});
    const items = await res.json();         // expects array: [{title, link, source, published}, ...]
    window._items = items;
    buildDropdown(items);
    render(items);
  }catch(err){
    updatedEl.textContent = '—';
    feedEl.innerHTML = `<div class="card"><h3>Couldn’t load items.json</h3><div class="meta"><span>Check GitHub Pages & Action</span></div></div>`;
  }
}

load();