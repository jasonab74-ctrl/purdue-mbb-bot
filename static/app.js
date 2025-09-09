// ========================
// Purdue MBB – front end
// Single script; keep it in /static and remove any other app.js
// All paths are RELATIVE so GitHub Pages subpaths work.
// ========================

const FEED_EL = document.getElementById('feed');
const SOURCE_SEL = document.getElementById('sourceSel');
const UPDATED_EL = document.getElementById('updatedTs');
const FIGHT_BTN = document.getElementById('fightBtn');
const FIGHT_AUDIO = document.getElementById('fightAudio');

// A stable, human list to keep the dropdown from ever being empty.
// These are display names paired with a simple id to match against item.source
const FALLBACK_SOURCES = [
  { id: 'Hammer and Rails', label: 'Hammer and Rails' },
  { id: 'Google News', label: 'Google News' },
  { id: 'ESPN', label: 'ESPN' },
  { id: 'Yahoo Sports', label: 'Yahoo Sports' },
  { id: 'Sports Illustrated', label: 'Sports Illustrated' },
  { id: 'Journal & Courier', label: 'Journal & Courier' },
  { id: 'GoldandBlack', label: 'GoldandBlack.com' },
  { id: 'The Athletic', label: 'The Athletic' },
  { id: 'CBS Sports', label: 'CBS Sports' },
  { id: 'Big Ten Network', label: 'Big Ten Network' },
];

function fmtDate(d){
  if(!(d instanceof Date) || isNaN(d)) return '—';
  const opts = { year:'numeric', month:'short', day:'numeric', hour:'numeric', minute:'2-digit' };
  return d.toLocaleString(undefined, opts);
}

// Try multiple typical date fields; fall back to "now" if totally invalid
function parseItemDate(raw){
  if(!raw) return new Date();
  const tryFields = [raw.isoDate, raw.pubDate, raw.published, raw.date, raw.updated, raw.time, raw];
  for(const v of tryFields){
    if(!v) continue;
    const d = new Date(v);
    if(!isNaN(d)) return d;
    const ts = Date.parse(v);
    if(!Number.isNaN(ts)) return new Date(ts);
  }
  return new Date();
}

function setUpdated(ts){
  UPDATED_EL.textContent = ts ? fmtDate(ts) : '—';
}

function render(items){
  FEED_EL.innerHTML = '';
  if(!items || !items.length){
    FEED_EL.innerHTML = `<div class="card"><h3>No articles yet</h3><div class="meta">Check back shortly.</div></div>`;
    return;
  }
  const frag = document.createDocumentFragment();
  for(const it of items){
    const d = parseItemDate(it);
    // Skip obviously wrong epoch dates (before 2000)
    if (d.getFullYear() < 2000) continue;

    const card = document.createElement('article');
    card.className = 'card';
    const src = it.source || it.site || it.publisher || '—';
    const href = it.link || it.url || '#';
    card.innerHTML = `
      <a href="${href}" target="_blank" rel="noopener">
        <h3>${it.title || '(untitled)'}</h3>
      </a>
      <div class="meta">
        <span>${src}</span>
        <span class="dot"></span>
        <span>${fmtDate(d)}</span>
      </div>
    `;
    frag.appendChild(card);
  }
  FEED_EL.appendChild(frag);
}

function populateSourcesFrom(items){
  const have = new Set();
  for(const it of items){
    const name = (it.source || it.site || it.publisher || '').trim();
    if(name) have.add(name);
  }
  // Merge with fallback set so we always show a solid list
  const merged = [...new Set([...have, ...FALLBACK_SOURCES.map(s=>s.id)])].slice(0, 12);

  // Reset the select but keep "All sources"
  SOURCE_SEL.length = 1;
  for(const name of merged){
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    SOURCE_SEL.appendChild(opt);
  }
}

async function loadFeed(){
  setUpdated(null);

  let items = [];
  let updated = null;

  try {
    // Cache-bust to avoid cached 404/old JSON on GH Pages edge nodes
    const res = await fetch(`items.json?cache=${Date.now()}`, { cache: 'no-store' });
    if(!res.ok){
      throw new Error(`items.json ${res.status}`);
    }
    const data = await res.json();

    // Accept a plain array or a wrapper {items:[…], updated:…}
    if(Array.isArray(data)) {
      items = data;
    } else if (data && Array.isArray(data.items)) {
      items = data.items;
      updated = data.updated || data.lastUpdated || data.generatedAt || null;
    }

  } catch (err){
    // Show a helpful note but DO NOT crash the page
    console.warn('Failed to load items.json:', err);
  }

  // If still empty, keep the page useful
  if (!Array.isArray(items)) items = [];
  populateSourcesFrom(items);

  const chosen = SOURCE_SEL.value;
  const filtered = (chosen === '__all__')
    ? items
    : items.filter(it => (it.source || it.site || it.publisher || '').trim() === chosen);

  render(filtered);
  setUpdated(updated ? new Date(updated) : new Date());
}

SOURCE_SEL.addEventListener('change', loadFeed);

// Fight song – play/pause with a user gesture, safe for iOS
FIGHT_BTN.addEventListener('click', async () => {
  try{
    // Ensure the file actually exists by poking its duration
    if (isNaN(FIGHT_AUDIO.duration)) {
      // NOP – iOS won’t resolve duration until after play() anyway
    }
    if (FIGHT_AUDIO.paused) {
      await FIGHT_AUDIO.play();
      FIGHT_BTN.querySelector('.play').textContent = '❚❚';
    } else {
      FIGHT_AUDIO.pause();
      FIGHT_AUDIO.currentTime = 0;
      FIGHT_BTN.querySelector('.play').textContent = '►';
    }
  }catch(err){
    alert("Could not play audio. On iPhone, make sure Silent Mode is off and tap again.\n\nAlso verify the file exists at static/hail-purdue.mp3");
    console.warn(err);
  }
});

// Initial load after DOM is ready
document.addEventListener('DOMContentLoaded', loadFeed);