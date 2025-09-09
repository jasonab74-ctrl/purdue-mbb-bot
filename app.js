/* Hardened client that:
   - fetches ./items.json with cache-busting
   - filters out obvious football content
   - populates an 8–10 source dropdown
   - formats US dates
   - makes the fight-song button work on iOS (user gesture)
*/

const SOURCE_OPTIONS = [
  { key: 'all',        label: 'All sources' },
  { key: 'Hammer and Rails', label: 'Hammer and Rails' },
  { key: 'PurdueSports.com', label: 'PurdueSports.com' },
  { key: 'Journal & Courier', label: 'Journal & Courier' },
  { key: 'GoldandBlack.com', label: 'GoldandBlack.com' },
  { key: 'ESPN',       label: 'ESPN' },
  { key: 'Sports Illustrated', label: 'Sports Illustrated' },
  { key: 'Yahoo Sports', label: 'Yahoo Sports' },
  { key: 'CBS Sports', label: 'CBS Sports' },
  { key: 'Big Ten Network', label: 'Big Ten Network' },
];

const FOOTBALL_NEG = [
  'football','gridiron','ross-ade','qb','quarterback','touchdown',
  'field goal','ryan walters','walters','running back','linebacker',
  'safety','cornerback','wide receiver','nfl','big ten football','game at ross-ade'
];

const sel = (s) => document.querySelector(s);
const list = sel('#list');
const sourceSel = sel('#sourceSel');
const stamp = sel('#stamp');

function fillSources() {
  sourceSel.innerHTML = SOURCE_OPTIONS
    .map(o => `<option value="${o.key}">${o.label}</option>`)
    .join('');
  sourceSel.value = 'all';
}

function isBasketballish(text) {
  if (!text) return true;
  const t = text.toLowerCase();
  // exclude obvious football cues
  if (FOOTBALL_NEG.some(w => t.includes(w))) return false;
  // include neutral hoops hints
  const hoopsHints = ['basketball','mbb','m. basketball','men’s basketball','men\'s basketball','mackey'];
  if (hoopsHints.some(w => t.includes(w))) return true;
  // if headline mentions Purdue + opponent but no football terms, allow
  return true;
}

function formatUSDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit'
    });
  } catch { return iso || ''; }
}

function render(items) {
  list.innerHTML = '';
  if (!items?.length) {
    list.innerHTML = `<div class="stamp">No items found.</div>`;
    return;
  }
  const src = sourceSel.value;
  const filtered = items
    .filter(x => isBasketballish(`${x.title} ${x.source} ${x.summary || ''}`))
    .filter(x => src === 'all' ? true : (x.source || '').includes(src));

  if (!filtered.length) {
    list.innerHTML = `<div class="stamp">No items for that source.</div>`;
    return;
  }

  const html = filtered.map(x => `
    <article class="card">
      <a class="title" href="${x.link}" target="_blank" rel="noopener">
        ${x.title}
      </a>
      <div class="meta">
        <span>${x.source || '—'}</span>
        <span class="dot"></span>
        <span>${formatUSDate(x.published)}</span>
      </div>
    </article>
  `).join('');

  list.innerHTML = html;
}

async function load() {
  try {
    // cache-busting + explicit same-origin to avoid accidental CDN issues
    const res = await fetch(`./items.json?ts=${Date.now()}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // Expected shape: [{title, link, source, published, summary?}, ...]
    // stamp
    const latest = data?.[0]?.fetched_at || data?.[0]?.published || new Date().toISOString();
    stamp.textContent = `Updated: ${formatUSDate(latest)}`;
    render(data || []);
  } catch (err) {
    console.error('Failed to load items.json', err);
    stamp.textContent = 'Updated: (load error)';
    list.innerHTML = `
      <div class="card" style="background:#2a2a2a;color:#fff">
        <div class="title">Couldn’t load the news feed.</div>
        <div class="meta">Make sure <code>items.json</code> is at the repo root and is valid JSON.</div>
      </div>`;
  }
}

function wireAudio() {
  const btn = sel('#hailBtn');
  const audio = sel('#fightSong');

  let playing = false;

  const setLabel = () => btn.textContent = (playing ? '⏸︎' : '▶︎') + ' Hail Purdue';

  btn.addEventListener('click', async () => {
    try {
      if (!playing) {
        await audio.play(); // user gesture => allowed on iOS
        playing = true;
      } else {
        audio.pause();
        playing = false;
      }
      setLabel();
    } catch (e) {
      console.warn('Audio play blocked or missing file', e);
      alert('Could not play audio. Confirm static/hail-purdue.mp3 exists.');
    }
  });

  audio.addEventListener('ended', () => { playing = false; setLabel(); });
  setLabel();
}

fillSources();
wireAudio();
sourceSel.addEventListener('change', load);
load();

// Optional auto-refresh every 15 minutes without tearing UI
setInterval(load, 15 * 60 * 1000);