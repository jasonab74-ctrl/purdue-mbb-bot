/* --------------- HARDENED FRONTEND ----------------
   Fixes:
   1) Fight song button works reliably on iOS/Safari (user gesture).
   2) Dates never show 1970 — robust, defensive parsing.
   3) Source dropdown will NOT “roll back”: we merge known sources
      with whatever appears in items.json without removing yours.
---------------------------------------------------*/

// ---- Fight song ----
(function wireFightSong() {
  const btn = document.getElementById('fightBtn');
  const icon = document.getElementById('fightIcon');
  const audio = document.getElementById('fightSong');

  // Extra hardening: verify the file is reachable
  // (preload=auto + this probe helps avoid silent failures)
  fetch(audio.currentSrc || audio.src, { method: 'HEAD', cache: 'no-store' })
    .catch(() => { /* ignore; button will show error if needed */ });

  let playing = false;

  async function togglePlay() {
    try {
      if (!playing) {
        // iOS requires play() from a direct click handler (this is one)
        await audio.play();
        playing = true;
        btn.setAttribute('aria-pressed', 'true');
        icon.textContent = '⏸';
      } else {
        audio.pause();
        playing = false;
        btn.setAttribute('aria-pressed', 'false');
        icon.textContent = '▶︎';
      }
    } catch (err) {
      // Most common cause on iOS is Silent mode or a bad path
      alert("Could not play audio. If you’re on iPhone, make sure Silent Mode is OFF and tap again.");
      console.error('Audio play error:', err);
    }
  }

  btn.addEventListener('click', togglePlay);
  audio.addEventListener('ended', () => {
    playing = false;
    btn.setAttribute('aria-pressed', 'false');
    icon.textContent = '▶︎';
  });
})();

// ---- Date parsing (never 1970) ----
function parseSafeDate(any) {
  if (!any) return null;
  // Accept millis, seconds, or date strings
  if (typeof any === 'number') {
    // If it's seconds, convert to ms
    if (any < 1e12) any = any * 1000;
    const d = new Date(any);
    return isNaN(d.getTime()) ? null : d;
  }
  if (typeof any === 'string') {
    // Some feeds give ISO strings; some give RFC2822
    const d = new Date(any);
    if (!isNaN(d.getTime())) return d;

    // Try to parse integers inside strings
    const n = Number(any);
    if (!Number.isNaN(n)) return parseSafeDate(n);
  }
  return null;
}

function formatUS(dt) {
  return dt.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit'
  });
}

// ---- Render list ----
const listEl = document.getElementById('list');
const updatedEl = document.getElementById('updatedAt');
const sourceSelect = document.getElementById('sourceSelect');

// Cache-bust items.json on GH Pages
const ITEMS_URL = `items.json?v=${Date.now()}`;

let ITEMS = [];

function addMissingSourcesFromItems(items) {
  const have = new Set([...sourceSelect.options].map(o => o.textContent.trim()));
  items.forEach(it => {
    const src = (it.source || it.site || it.by || '').toString().trim();
    if (src && !have.has(src)) {
      const opt = document.createElement('option');
      opt.textContent = src;
      sourceSelect.appendChild(opt);
      have.add(src);
    }
  });
}

function render() {
  const filter = sourceSelect.value;
  listEl.innerHTML = '';

  // Show updated time = newest item date we can find; fallback to now
  const dates = [];

  ITEMS
    .filter(it => {
      if (filter === '*') return true;
      const src = (it.source || it.site || it.by || '').toString().trim();
      return src === filter;
    })
    .sort((a,b) => {
      const da = parseSafeDate(a.published || a.pubDate || a.isoDate || a.date || a.time || a.timestamp) || 0;
      const db = parseSafeDate(b.published || b.pubDate || b.isoDate || b.date || b.time || b.timestamp) || 0;
      return (db - da);
    })
    .forEach(it => {
      const d =
        parseSafeDate(it.published) ||
        parseSafeDate(it.pubDate)   ||
        parseSafeDate(it.isoDate)   ||
        parseSafeDate(it.date)      ||
        parseSafeDate(it.time)      ||
        parseSafeDate(it.timestamp);

      if (d) dates.push(d);

      const when = d ? formatUS(d) : '—';

      const card = document.createElement('article');
      card.className = 'card';
      card.innerHTML = `
        <a class="card__title" href="${it.link}" target="_blank" rel="noopener">${it.title}</a>
        <div class="card__meta">
          <span class="meta__source">${(it.source || it.site || it.by || '—')}</span>
          <span class="dot">•</span>
          <time>${when}</time>
        </div>
      `;
      listEl.appendChild(card);
    });

  const newest = dates.sort((a,b)=>b-a)[0] || new Date();
  updatedEl.textContent = formatUS(newest);
}

async function boot() {
  try {
    const r = await fetch(ITEMS_URL, { cache: 'no-store' });
    const raw = await r.json();

    // Expect either array or {items:[...]}
    const arr = Array.isArray(raw) ? raw : Array.isArray(raw.items) ? raw.items : [];
    ITEMS = arr.map(x => ({
      title: x.title || x.headline || 'Untitled',
      link:  x.link  || x.url      || '#',
      source: (x.source || x.site || x.by || x.feed || '').toString().trim(),
      published: x.published ?? x.pubDate ?? x.isoDate ?? x.date ?? x.time ?? x.timestamp ?? null
    }));

    // Harden sources: merge, never delete your preset list
    addMissingSourcesFromItems(ITEMS);

    render();
  } catch (e) {
    console.error('Failed to load items.json:', e);
    updatedEl.textContent = '—';
  }
}

sourceSelect.addEventListener('change', render);
boot();