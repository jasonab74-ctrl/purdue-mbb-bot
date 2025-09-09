<script>
/* ---------------------------
   Purdue MBB – front-end only
   Fixes: stable sources list, US dates, clean titles (no underline)
   --------------------------- */

const ITEMS_URL = 'items.json';

/** A hard, stable list so the dropdown never goes empty.
 * We merge this with whatever appears in items.json. */
const FIXED_SOURCES = [
  'Yahoo Sports',
  'Google News',
  'Hammer and Rails',
  'ESPN',
  'Sports Illustrated',
  'Journal & Courier',
  'GoldandBlack',
  'The Athletic',
  'CBS Sports',
  'Big Ten Network'
];

const els = {
  select:  document.getElementById('source-select'),
  updated: document.getElementById('updated-at'),
  list:    document.getElementById('items-list'),
};

// ---- Utilities -------------------------------------------------------------

function formatUS(date) {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit'
    }).format(date);
  } catch {
    return '';
  }
}

/** iOS Safari is picky about non-ISO strings. Prefer isoDate; otherwise
 * parse common “Sep 8, 2025 at 2:09 PM” style manually. */
function toDate(obj) {
  if (obj.isoDate) {
    const d = new Date(obj.isoDate);
    if (!isNaN(d)) return d;
  }
  if (obj.published || obj.pubDate) {
    const s = String(obj.published || obj.pubDate);
    // Try adding timezone if missing
    let d = new Date(s);
    if (!isNaN(d)) return d;

    // Manual US parser: "Sep 8, 2025 at 2:09 PM" or "Sep 8, 2025, 2:09 PM"
    const re = /([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4}).*?(\d{1,2}):(\d{2})\s*(AM|PM)/i;
    const m = s.match(re);
    if (m) {
      const months = {
        January:0, February:1, March:2, April:3, May:4, June:5,
        July:6, August:7, September:8, October:9, November:10, December:11,
        Jan:0, Feb:1, Mar:2, Apr:3, Jun:5, Jul:6, Aug:7, Sep:8, Sept:8, Oct:9, Nov:10, Dec:11
      };
      const mon = months[m[1]];
      if (mon != null) {
        let hr = Number(m[4]) % 12;
        if (m[6].toUpperCase() === 'PM') hr += 12;
        const dt = new Date(
          Number(m[3]), mon, Number(m[2]),
          hr, Number(m[5]), 0
        );
        if (!isNaN(dt)) return dt;
      }
    }
  }
  return null;
}

function unique(arr) {
  return Array.from(new Set(arr.filter(Boolean)));
}

// ---- Rendering -------------------------------------------------------------

function buildCard(item) {
  const a = document.createElement('article');
  a.className = 'news-card';

  const title = document.createElement('h3');
  title.className = 'item-title';
  const link  = document.createElement('a');
  link.href = item.link;
  link.target = '_blank';
  link.rel = 'noopener';
  link.textContent = item.title || '(untitled)';
  title.appendChild(link);

  const meta = document.createElement('div');
  meta.className = 'item-meta';
  const src = document.createElement('span');
  src.className = 'meta-source';
  src.textContent = item.source || '—';
  const dot = document.createElement('span');
  dot.textContent = ' • ';
  const time = document.createElement('time');
  if (item._date) time.textContent = formatUS(item._date);

  meta.appendChild(src);
  meta.appendChild(dot);
  meta.appendChild(time);

  a.appendChild(title);
  a.appendChild(meta);

  return a;
}

function render(items, sourceFilter) {
  els.list.innerHTML = '';
  const filtered = sourceFilter && sourceFilter !== 'All sources'
    ? items.filter(i => (i.source || '').toLowerCase() === sourceFilter.toLowerCase())
    : items;

  filtered.forEach(i => els.list.appendChild(buildCard(i)));
}

// ---- Bootstrap -------------------------------------------------------------

async function main() {
  let data = [];
  try {
    const resp = await fetch(ITEMS_URL, {cache: 'no-store'});
    data = await resp.json();
  } catch (e) {
    console.error('items.json fetch failed', e);
    data = [];
  }

  // Normalize items
  const items = (data || []).map(x => {
    const obj = {
      title: x.title ?? x.headline ?? '',
      link:  x.link  ?? x.url      ?? '#',
      source: x.source ?? x.site ?? x.feed ?? '',
    };
    obj._date = toDate(x);
    return obj;
  });

  // Updated stamp: show the newest good date if present,
  // otherwise use "just now" so it never says 1970.
  const newest = items
    .map(i => i._date)
    .filter(Boolean)
    .sort((a,b) => b - a)[0];
  els.updated.textContent = newest ? formatUS(newest) : 'just now';

  // Stable sources list = FIXED_SOURCES ∪ discovered
  const discovered = unique(items.map(i => i.source));
  const allSources = unique(['All sources', ...FIXED_SOURCES, ...discovered]);

  // Populate dropdown once, in order
  els.select.innerHTML = '';
  for (const s of allSources) {
    const opt = document.createElement('option');
    opt.value = opt.textContent = s;
    els.select.appendChild(opt);
  }

  // Keep previous selection if still present
  const saved = localStorage.getItem('sourceFilter');
  if (saved && allSources.includes(saved)) els.select.value = saved;

  // Initial render
  render(items, els.select.value);

  // Wire up changes
  els.select.addEventListener('change', () => {
    localStorage.setItem('sourceFilter', els.select.value);
    render(items, els.select.value);
  });

  // Expose minimal hook for the play button (non-breaking)
  window.__playHailPurdue = async function() {
    const candidates = [
      'static/fight song.mp3',      // your file name (with space)
      'static/fight%20song.mp3',    // URL-encoded fallback
      'static/hail-purdue.mp3',     // conventional name fallback
    ];
    const src = await (async () => {
      for (const url of candidates) {
        try {
          const r = await fetch(url, {method: 'HEAD', cache: 'no-store'});
          if (r.ok) return url;
        } catch {}
      }
      return null;
    })();

    if (!src) {
      alert('Could not play audio. Make sure the MP3 exists in /static (e.g., "fight song.mp3" or "hail-purdue.mp3").');
      return;
    }

    const audio = new Audio(src);
    audio.play().catch(() => {
      alert('Could not play audio. On iPhone, make sure Silent Mode is off and tap again.');
    });
  };
}

document.addEventListener('DOMContentLoaded', main);
</script>