// ---------- CONFIG (easy to reuse for other teams) ----------
const ITEMS_URL = 'items.json';          // keep items.json in the repo root
const AUDIO_URL = 'static/hail-purdue.mp3'; // exact filename; no spaces/uppercase
const FOOTBALL_FILTER = /\bfootball|ross-ade|gridiron\b/i; // drop football posts

// ---------- AUDIO (user-gesture on iOS) ----------
const playBtn = document.getElementById('playBtn');
let audio;
playBtn?.addEventListener('click', async () => {
  try {
    if (!audio) audio = new Audio(AUDIO_URL);
    // iOS can fail if on silent — but a user gesture still required
    await audio.play();
  } catch (err) {
    alert('Could not play audio. On iPhone, ensure Silent Mode is off and tap again.\n\nAlso verify the file exists at static/hail-purdue.mp3');
  }
});

// ---------- DOM ELEMENTS ----------
const feedEl = document.getElementById('feed');
const selectEl = document.getElementById('sourceSelect');
const updatedEl = document.getElementById('updated');

// ---------- UTIL ----------
const fmtDate = (isoOrText) => {
  // Try ISO first; if it fails, try Date.parse; if still bad, return '—'
  let d = new Date(isoOrText);
  if (isNaN(d)) {
    const parsed = Date.parse(isoOrText);
    d = new Date(parsed);
  }
  if (isNaN(d)) return '—';
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute:'2-digit'
  });
};

const byRecency = (a,b) => {
  const da = Date.parse(a.date || a.pubDate || 0) || 0;
  const db = Date.parse(b.date || b.pubDate || 0) || 0;
  return db - da;
};

// Dedup by URL (keep latest)
const dedup = (items) => {
  const seen = new Map();
  for (const it of items) {
    const key = (it.link || it.url || '').trim();
    if (!key) continue;
    const prev = seen.get(key);
    if (!prev || byRecency(it, prev) < 0) seen.set(key, it);
  }
  return [...seen.values()];
};

// ---------- RENDER ----------
const render = (items, source='*') => {
  feedEl.innerHTML = '';
  let list = items.slice();

  // Filter out football cross-posts
  list = list.filter(it => !FOOTBALL_FILTER.test(it.title || ''));

  if (source && source !== '*') {
    list = list.filter(it => (it.source || '').toLowerCase() === source.toLowerCase());
  }

  list.sort(byRecency);

  for (const it of list) {
    const card = document.createElement('article');
    card.className = 'card';

    const title = (it.title || '').trim();
    const href  = (it.link || it.url || '').trim();

    const h3 = document.createElement('h3');
    h3.className = 'card-title';

    if (href) {
      const a = document.createElement('a');
      a.href = href;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = title || 'Untitled';
      h3.appendChild(a);
    } else {
      h3.textContent = title || 'Untitled';
    }

    const meta = document.createElement('div');
    meta.className = 'card-meta';
    const src = (it.source || it.outlet || '').trim() || '—';
    const when = fmtDate(it.date || it.pubDate || it.published || '');
    meta.innerHTML = `${src} <span class="dot"></span> ${when}`;

    card.append(h3, meta);
    feedEl.appendChild(card);
  }

  updatedEl.textContent = `Updated: ${fmtDate(new Date().toISOString())}`;
};

// ---------- LOAD ----------
(async function init(){
  try {
    const res = await fetch(ITEMS_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(`Failed to fetch ${ITEMS_URL}`);
    const data = await res.json();

    // Normalize structure – accept either {items:[...]} or [...]
    const raw = Array.isArray(data) ? data : (data.items || []);
    const clean = dedup(
      raw.map(x => ({
        title: x.title || x.headline || '',
        link:  x.link  || x.url || '',
        source: x.source || x.outlet || x.feed || '',
        date: x.date || x.pubDate || x.published || ''
      }))
    );

    // Populate source dropdown
    const sources = Array.from(new Set(clean
      .map(i => (i.source || '').trim())
      .filter(Boolean)
    )).sort((a,b)=>a.localeCompare(b));

    // Reset options safely
    selectEl.innerHTML = '<option value="*">All sources</option>';
    for (const s of sources) {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      selectEl.appendChild(opt);
    }

    // First paint
    render(clean, '*');

    // Interactions
    selectEl.addEventListener('change', () => {
      render(clean, selectEl.value);
    });

    // Light auto-refresh (client-side) every 15 min without breaking the UI
    setInterval(async () => {
      try {
        const r = await fetch(ITEMS_URL, { cache: 'no-store' });
        if (!r.ok) return;
        const d = await r.json();
        const nxt = Array.isArray(d) ? d : (d.items || []);
        const cleaned = dedup(nxt.map(x => ({
          title: x.title || x.headline || '',
          link:  x.link  || x.url || '',
          source: x.source || x.outlet || x.feed || '',
          date: x.date || x.pubDate || x.published || ''
        })));
        render(cleaned, selectEl.value);
      } catch {}
    }, 15 * 60 * 1000);

  } catch (err) {
    console.error(err);
    updatedEl.textContent = 'Updated: —';
    feedEl.innerHTML =
      '<div class="card"><h3 class="card-title">Couldn’t load items.json</h3><div class="card-meta">Make sure items.json is in the repo root and is valid JSON.</div></div>';
  }
})();