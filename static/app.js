/* Purdue MBB — front-end feed logic
   Drop-in replacement. Only requires:
   - <select id="sourceSelect"> in the page
   - <span id="updatedAt"> (optional)
   - <div id="feed"> container for cards
   - items.json at site root (GitHub Pages) updated by Actions
*/

(function () {
  const FEED_URL = `items.json?nocache=${Date.now()}`;
  const feedEl = document.getElementById('feed');
  const selectEl = document.getElementById('sourceSelect') || document.getElementById('source-select');
  const updatedEl = document.getElementById('updatedAt') || document.querySelector('[data-updated]');

  // Safeguard: light helpers
  const by = (s, r = document) => r.querySelector(s);
  const cr = (t, cls) => {
    const n = document.createElement(t);
    if (cls) n.className = cls;
    return n;
  };

  // ---- Date parsing hardened (prevents 1970) -------------------------------
  const parseDate = (item) => {
    const candidates = [
      item.isoDate,
      item.pubDate,
      item.published,
      item.date,
      item.updated,
      item.created
    ];

    for (const c of candidates) {
      if (!c) continue;
      const d = new Date(c);
      if (!Number.isNaN(d.getTime())) return d;
    }

    // some feeds store seconds since epoch
    if (typeof item.timestamp === 'number') {
      const d = new Date(
        item.timestamp > 1e12 ? item.timestamp : item.timestamp * 1000
      );
      if (!Number.isNaN(d.getTime())) return d;
    }

    // try to mine a date from the link string (rare)
    if (item.link && /\d{4}-\d{2}-\d{2}/.test(item.link)) {
      const m = item.link.match(/\d{4}-\d{2}-\d{2}/);
      const d = new Date(m[0]);
      if (!Number.isNaN(d.getTime())) return d;
    }

    return null; // unknown
  };

  const fmtDate = (d) =>
    d
      ? d.toLocaleString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit'
        })
      : '—';

  // ---- Sources list (always visible) --------------------------------------
  function extractSource(item) {
    // normalize likely fields across feeds
    return (
      item.source ||
      item.source_name ||
      item.site ||
      item.feed ||
      item.provider ||
      ''
    ).toString().trim();
  }

  function buildSources(items) {
    // Preferred order for Purdue hoops (edit this array to pin “top 10”)
    const preferred = [
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

    const seen = new Set();
    const fromData = [];

    for (const it of items) {
      const s = extractSource(it);
      if (!s) continue;
      if (!seen.has(s)) {
        seen.add(s);
        fromData.push(s);
      }
    }

    // ensure preferred ones appear (if present) and top-ordered
    const inData = new Set(fromData);
    const ordered = preferred.filter((p) => inData.has(p));
    // append any others alphabetically
    const extras = fromData.filter((s) => !ordered.includes(s)).sort();

    return ordered.concat(extras);
  }

  function populateSelect(sources) {
    if (!selectEl) return;
    // Clean slate
    selectEl.innerHTML = '';

    const optAll = cr('option');
    optAll.value = '';
    optAll.textContent = 'All sources';
    selectEl.appendChild(optAll);

    for (const s of sources) {
      const opt = cr('option');
      opt.value = s;
      opt.textContent = s;
      selectEl.appendChild(opt);
    }

    // Keep whatever user had selected if it still exists
    const saved = sessionStorage.getItem('purdue_source') || '';
    if ([...selectEl.options].some((o) => o.value === saved)) {
      selectEl.value = saved;
    } else {
      selectEl.value = '';
    }
  }

  // ---- Render --------------------------------------------------------------
  function render(items) {
    if (!feedEl) return;
    feedEl.innerHTML = '';

    const chosen = (selectEl && selectEl.value) || '';
    const filtered = chosen
      ? items.filter((it) => extractSource(it) === chosen)
      : items.slice();

    // sort newest first
    filtered.sort((a, b) => {
      const da = parseDate(a)?.getTime() ?? 0;
      const db = parseDate(b)?.getTime() ?? 0;
      return db - da;
    });

    for (const it of filtered) {
      const card = cr('article', 'news-card');

      const title = cr('a', 'news-title');
      title.href = it.link;
      title.target = '_blank';
      title.rel = 'noopener';
      title.textContent = (it.title || '').trim();

      const meta = cr('div', 'news-meta');
      const src = extractSource(it) || '—';
      const when = fmtDate(parseDate(it));
      meta.textContent = `${src} • ${when}`;

      card.appendChild(title);
      card.appendChild(meta);
      feedEl.appendChild(card);
    }

    if (updatedEl) {
      const newest = filtered[0] ? parseDate(filtered[0]) : null;
      updatedEl.textContent = newest ? fmtDate(newest) : '—';
    }
  }

  // ---- Bootstrap -----------------------------------------------------------
  let ALL_ITEMS = [];

  function handleSelectChange() {
    if (!selectEl) return;
    sessionStorage.setItem('purdue_source', selectEl.value || '');
    render(ALL_ITEMS);
  }

  async function init() {
    try {
      const res = await fetch(FEED_URL, { cache: 'no-store' });
      const data = await res.json();

      // Accept arrays or {items:[...]}
      const items = Array.isArray(data) ? data : (data.items || []);
      ALL_ITEMS = items;

      const sources = buildSources(items);
      populateSelect(sources);
      render(items);

      if (selectEl) selectEl.addEventListener('change', handleSelectChange);
    } catch (e) {
      console.error('Failed to load items.json', e);
      if (feedEl) {
        const msg = cr('div', 'news-error');
        msg.textContent = 'Unable to load articles.';
        feedEl.appendChild(msg);
      }
    }
  }

  // ---- Optional: fight song (no breakage) ---------------------------------
  // If you have a button with id="play-anthem" and a file at /static/hail-purdue.mp3
  // this will play on user tap. (Safari requires a user gesture.)
  const anthemBtn = by('#play-anthem');
  if (anthemBtn) {
    const audio = new Audio('/static/hail-purdue.mp3'); // no spaces, lowercase
    anthemBtn.addEventListener('click', async () => {
      try {
        await audio.play();
      } catch (err) {
        alert(
          'Could not play audio. On iPhone, make sure Silent Mode is off and tap again.\n\nAlso verify the file exists at static/hail-purdue.mp3'
        );
      }
    });
  }

  // go!
  init();
})();