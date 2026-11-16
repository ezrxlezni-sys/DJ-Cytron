// ================= Music: a home page plus one page per platform =================
// Pages (panes in index.html, filled in here on first visit):
//   music  home: search across every platform, platform cards, shelves (trending, suggestions)
//   ytm    YouTube Music: songs, suggestions, trending
//   yt     YouTube: videos, live streams and podcasts (played as audio), video grid
//   sc     SoundCloud: remixes, DJ sets, independent artists
// Shared helpers come from app.js ($, el, api, ICON, paintArt, fmt, toast, emptyState, trackRow, pickPlaylist, go, isNow).
(() => {
  'use strict';

  // ---------- platforms ----------
  const BRAND = {
    ytm: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#ff0033"/><circle cx="12" cy="12" r="6" fill="none" stroke="#fff" stroke-width="1.6"/><path d="M10.2 9v6l5-3Z" fill="#fff"/></svg>',
    yt: '<svg viewBox="0 0 24 24"><rect x="1.5" y="5" width="21" height="14" rx="4.5" fill="#ff0000"/><path d="M10 9.2v5.6l5-2.8Z" fill="#fff"/></svg>',
    sc: '<svg viewBox="0 0 24 24"><g fill="#ff5500"><rect x="1.6" y="12.5" width="1.4" height="5" rx=".7"/><rect x="4" y="10.8" width="1.4" height="6.7" rx=".7"/><path d="M17.6 9.2a4.6 4.6 0 0 0-4.4 3.3A3 3 0 0 0 8 14.6V18h9.6a4.4 4.4 0 0 0 0-8.8Z"/></g></svg>',
    all: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/></g></svg>',
  };
  const PLATFORMS = {
    ytm: {name: 'YouTube Music', source: '', blurb: 'Songs and albums, trending charts and suggestions.', placeholder: 'Search songs, artists…', view: 'list', chips: []},
    yt: {name: 'YouTube', source: 'youtube', blurb: 'Videos, live streams and podcasts, played as audio.', placeholder: 'Search YouTube…', view: 'grid',
         chips: ['Lo-fi live radio', 'Podcasts', 'Live concerts', 'Chill mix', 'Workout music', 'News']},
    sc: {name: 'SoundCloud', source: 'soundcloud', blurb: 'Remixes, DJ sets and independent artists.', placeholder: 'Search SoundCloud…', view: 'list',
         chips: ['Lo-fi', 'Electronic', 'Hip hop', 'House', 'Indie', 'DJ mix', 'Remix', 'Ambient'],
         note: 'Songs from major labels are often only 30-second previews on SoundCloud, so they are hidden.'},
  };
  const KEYS = Object.keys(PLATFORMS);

  // ---------- remembered preferences ----------
  let recents = [], views = Object.fromEntries(KEYS.map(k => [k, PLATFORMS[k].view]));
  try { recents = JSON.parse(localStorage.getItem('cdj-recent') || '[]').filter(x => typeof x === 'string').slice(0, 8) } catch (e) {}
  try { const v = JSON.parse(localStorage.getItem('cdj-mview') || '{}'); for (const k of KEYS) if (v[k] === 'list' || v[k] === 'grid') views[k] = v[k] } catch (e) {}
  const saveRecents = () => { try { localStorage.setItem('cdj-recent', JSON.stringify(recents)) } catch (e) {} };
  const saveViews = () => { try { localStorage.setItem('cdj-mview', JSON.stringify(views)) } catch (e) {} };
  const remember = q => { recents = [q, ...recents.filter(x => x.toLowerCase() !== q.toLowerCase())].slice(0, 8); saveRecents() };

  // ---------- data ----------
  const ok = r => Array.isArray(r) ? r : [];
  const searchApi = (key, q) => api('search?q=' + encodeURIComponent(q) + '&type=songs' + (PLATFORMS[key].source ? '&source=' + PLATFORMS[key].source : ''))
    .catch(() => ({error: 'network error'}));
  const play = (items, i) => api('play', 'POST', {items: items.slice(i)});

  // ---------- building blocks ----------
  const trackActions = it => [[ICON.add, 'Add to queue', () => api('queue', 'POST', {items: [it]}).then(() => toast('Added to queue'))],
                              [ICON.pladd, 'Add to playlist', () => pickPlaylist([it])]];
  function trackList(items, desc, ranked) {                  // rows; tapping one plays from it to the end of the list
    const list = el('div', 'item-group');
    items.forEach((it, i) => {
      const row = trackRow(desc ? {...it, artist: desc(it)} : it, trackActions(it), ranked ? i : undefined);
      row.querySelector('.go').onclick = () => play(items, i);
      list.append(row);
    });
    return list;
  }
  function section(title, body, more) {
    const s = el('section', 'msec');
    if (!more) { s.append(el('h2', 'msec-title', title), body); return s }
    const head = el('div', 'sg-head'), b = el('button', 'sg-link', more[0]); b.type = 'button'; b.onclick = more[1];
    head.append(el('h2', 'msec-title', title), b); s.append(head, body); return s;
  }
  function card(it, items, i, wide) {                          // cover card used by shelves and the grid view
    const c = el('div', 'm-card' + (isNow(it) ? ' now' : ''));
    const go = el('button', 'm-go'); go.type = 'button';
    const art = el('div', 'm-art' + (wide ? ' wide' : '')); paintArt(art, it);
    if (it.duration) art.append(el('span', 'm-dur', fmt(it.duration)));
    go.append(art, el('span', 'm-title', it.title), el('span', 'm-sub', it.artist || ''));
    go.onclick = () => play(items, i);
    const add = el('button', 'm-add'); add.type = 'button'; add.innerHTML = ICON.add; add.title = 'Add to queue'; add.setAttribute('aria-label', 'Add to queue');
    add.onclick = ev => { ev.stopPropagation(); api('queue', 'POST', {items: [it]}).then(() => toast('Added to queue')) };
    c.append(go, add); return c;
  }
  const grid = (items, wide) => { const g = el('div', 'm-grid' + (wide ? ' wide' : '')); items.forEach((it, i) => g.append(card(it, items, i, wide))); return g };
  const results = (key, items) => views[key] === 'grid' ? grid(items, key === 'yt') : trackList(items);

  function skeleton(kind, wide) {
    if (kind === 'list') return skeletonList(4);
    const box = el('div', 'm-grid' + (wide ? ' wide' : ''));
    for (let i = 0; i < 8; i++) {
      const c = el('div', 'm-card sk'), a = el('div', 'm-art skeleton' + (wide ? ' wide' : ''));
      const t = el('div', 'skeleton'); t.style.cssText = 'height:12px;width:70%;margin-top:10px';
      c.append(a, t); box.append(c);
    }
    return box;
  }
  const loading = (title, kind, wide) => { const s = el('section', 'msec'); s.append(el('h2', 'msec-title', title), skeleton(kind, wide)); return s };

  function chipRow(list, onPick) {
    const row = el('div', 'm-chips');
    for (const q of list) { const b = el('button', 'm-chip', q); b.type = 'button'; b.onclick = () => onPick(q); row.append(b) }
    return row;
  }
  function recentsBlock(onPick, redraw) {
    if (!recents.length) return null;
    const clear = el('button', 'sg-link', 'Clear'); clear.type = 'button';
    clear.onclick = () => { recents = []; saveRecents(); redraw() };
    const head = el('div', 'sg-head'); head.append(el('h2', 'msec-title', 'Recent searches'), clear);
    const s = el('section', 'msec'); s.append(head, chipRow(recents, onPick)); return s;
  }

  // the header search pill (works the same on every page)
  function pill(placeholder, onSubmit, onEmpty) {
    const f = el('form', 'm-search'); f.setAttribute('role', 'search');
    const icon = el('span', 'm-search-icon'); icon.innerHTML = ICON.search;
    const i = el('input'); i.type = 'search'; i.placeholder = placeholder; i.autocomplete = 'off'; i.spellcheck = false;
    i.setAttribute('enterkeyhint', 'search'); i.setAttribute('aria-label', placeholder);
    const x = el('button', 'm-clear'); x.type = 'button'; x.innerHTML = ICON.x; x.hidden = true; x.setAttribute('aria-label', 'Clear search');
    const set = q => { i.value = q; x.hidden = !q };
    i.addEventListener('input', () => { x.hidden = !i.value; if (!i.value.trim()) onEmpty() });
    i.addEventListener('keydown', e => { if (e.key === 'Escape' && i.value) { set(''); onEmpty() } });
    x.onclick = () => { set(''); onEmpty(); i.focus() };
    f.onsubmit = e => { e.preventDefault(); const q = i.value.trim(); if (q) onSubmit(q) };
    f.append(icon, i, x);
    return {el: f, input: i, set};
  }
  function header(title, sub, key, controls) {
    const h = el('header', 'pane-head'), brand = el('div', 'head-brand'), text = el('div');
    if (key) {
      const back = el('button', 'btn ghost icon m-back'); back.type = 'button'; back.innerHTML = ICON.back;
      back.title = 'Music'; back.setAttribute('aria-label', 'Back to Music'); back.onclick = () => go('music'); brand.append(back);
      const ic = el('span', 'm-hicon'); ic.innerHTML = BRAND[key]; brand.append(ic);
    }
    text.append(el('h1', '', title), el('p', '', sub)); brand.append(text);
    const actions = el('div', 'actions m-actions'); actions.append(...controls);
    h.append(brand, actions); return h;
  }
  const blurIfTouch = () => { if (matchMedia('(pointer:coarse)').matches && document.activeElement) document.activeElement.blur() };

  // ---------- YouTube Music shelves (used by the home page and the YouTube Music page) ----------
  function musicShelves(body, alive, trendingN) {
    const slots = {};
    for (const [id, title] of [['trend', 'Trending now'], ['sugg', 'Suggested for you']]) {
      slots[id] = el('div'); slots[id].append(loading(title, 'list')); body.append(slots[id]);
    }
    const fill = (id, node) => { if (!alive()) return; node ? slots[id].replaceChildren(node) : slots[id].remove() };
    api('trending').then(r => fill('trend', ok(r).length ? section('Trending now', trackList(r.slice(0, trendingN), null, true)) : null)).catch(() => fill('trend', null));
    api('suggested').then(r => fill('sugg', ok(r).length ? section('Suggested for you', trackList(r.slice(0, 8))) : null)).catch(() => fill('sugg', null));
  }

  // ---------- pages ----------
  const pages = {};

  function makeHome() {
    const pane = $('#music'), st = {q: '', gen: 0, tab: 'all', found: {}, pending: new Set()};
    const P = pill('Search YouTube Music, YouTube and SoundCloud', q => search(q), () => { if (st.q) { st.q = ''; st.gen++; idle() } });
    const body = el('div', 'm-body');
    pane.replaceChildren(header('Music', 'Search every platform, or open one below.', null, [P.el]), body);

    const platformCards = () => {
      const row = el('div', 'm-platforms');
      for (const k of KEYS) {
        const b = el('button', 'm-pcard'); b.type = 'button';
        const ic = el('span', 'm-pcard-icon'); ic.innerHTML = BRAND[k];
        const tx = el('span', 'm-pcard-text'); tx.append(el('b', '', PLATFORMS[k].name), el('span', '', PLATFORMS[k].blurb));
        const arrow = el('span', 'm-pcard-go'); arrow.innerHTML = CHEV_R; b.append(ic, tx, arrow);
        b.onclick = () => window.go(k); row.append(b);
      }
      return row;
    };
    function idle() {
      const gen = ++st.gen; body.replaceChildren(platformCards());
      const r = recentsBlock(q => { P.set(q); search(q) }, idle); if (r) body.append(r);
      musicShelves(body, () => gen === st.gen && !st.q, 10);
    }
    function tabsBar() {
      const bar = el('div', 'm-tabs'); bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', 'Results from');
      for (const k of ['all', ...KEYS]) {
        const b = el('button', 'm-tab'); b.type = 'button'; b.setAttribute('aria-pressed', String(st.tab === k));
        const ic = el('span', 'm-tab-icon'); ic.innerHTML = BRAND[k]; b.append(ic, el('span', '', k === 'all' ? 'All' : PLATFORMS[k].name));
        if (k !== 'all' && !st.pending.has(k) && st.found[k]) b.append(el('em', '', String(ok(st.found[k]).length)));
        b.onclick = () => { st.tab = k; render() }; bar.append(b);
      }
      return bar;
    }
    function render() {
      body.replaceChildren(tabsBar());
      const want = st.tab === 'all' ? KEYS : [st.tab];
      let any = false;
      for (const k of want) {
        if (st.pending.has(k)) { body.append(loading(PLATFORMS[k].name, 'list')); any = true; continue }
        const items = ok(st.found[k]); if (!items.length) continue;
        any = true;
        body.append(st.tab === 'all'
          ? section(PLATFORMS[k].name, trackList(items.slice(0, 5)), ['Open ' + PLATFORMS[k].name + ' ›', () => openPlatform(k, st.q)])
          : section(PLATFORMS[k].name, results(k, items)));
      }
      if (any) return;
      const failed = want.every(k => st.found[k] && st.found[k].error);
      body.append(failed ? emptyState(ICON.search, 'Search failed', st.found[want[0]].error)
                         : emptyState(ICON.search, 'No results', `Nothing found for “${st.q}”${st.tab === 'all' ? '' : ' on ' + PLATFORMS[st.tab].name}.`));
    }
    async function search(q) {
      st.q = q; st.tab = 'all'; remember(q); P.set(q);                // every new search starts on "All"
      const gen = ++st.gen; st.found = {}; st.pending = new Set(KEYS); render();
      await Promise.all(KEYS.map(async k => {
        const r = await searchApi(k, q);
        if (gen !== st.gen) return;                            // a newer search replaced this one
        st.found[k] = r; st.pending.delete(k); render();
      }));
      if (gen === st.gen) blurIfTouch();
    }
    return {show(restoring) { if (!st.q) idle(); if (!restoring && matchMedia('(hover:hover)').matches) P.input.focus() },
            search, focus() { P.input.focus(); P.input.select() }};
  }

  function makePlatform(key) {
    const cfg = PLATFORMS[key], pane = $('#' + key), st = {q: '', gen: 0, items: null};
    const P = pill(cfg.placeholder, q => search(q), () => { if (st.q) { st.q = ''; st.gen++; st.items = null; idle() } });
    const seg = el('div', 'view-seg'); seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', 'Layout');
    const mk = (v, label, svg) => {
      const b = el('button'); b.type = 'button'; b.dataset.view = v; b.title = label; b.setAttribute('aria-label', label); b.innerHTML = svg; return b;
    };
    seg.append(
      mk('grid', 'Grid view', '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></g></svg>'),
      mk('list', 'List view', '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>'));
    const paintSeg = () => { for (const b of seg.children) b.setAttribute('aria-pressed', String(b.dataset.view === views[key])) };
    const body = el('div', 'm-body');
    pane.replaceChildren(header(cfg.name, cfg.blurb, key, [P.el, seg]), body);
    paintSeg();
    seg.onclick = ev => {
      const b = ev.target.closest('button[data-view]'); if (!b || views[key] === b.dataset.view) return;
      views[key] = b.dataset.view; saveViews(); paintSeg(); if (st.items) renderResults();
    };

    function idle() {
      const gen = ++st.gen; body.replaceChildren();
      const r = recentsBlock(q => search(q), idle); if (r) body.append(r);
      if (key === 'ytm') return musicShelves(body, () => gen === st.gen && !st.q, 20);
      const s = el('section', 'msec'); s.append(el('h2', 'msec-title', 'Try searching'), chipRow(cfg.chips, search));
      if (cfg.note) s.append(el('p', 'm-note', cfg.note));
      body.append(s);
    }
    function renderResults() {
      body.replaceChildren();
      const s = el('section', 'msec'); s.append(el('h2', 'msec-title', `${st.items.length} result${st.items.length === 1 ? '' : 's'} for “${st.q}”`), results(key, st.items));
      body.append(s);
    }
    async function search(q) {
      st.q = q; remember(q); P.set(q);
      const gen = ++st.gen; st.items = null; body.replaceChildren(loading('Searching…', views[key] === 'grid' ? 'grid' : 'list', key === 'yt'));
      const r = await searchApi(key, q);
      if (gen !== st.gen) return;                              // a newer search replaced this one
      if (r.error) body.replaceChildren(emptyState(ICON.search, 'Search failed', r.error));
      else if (!ok(r).length) body.replaceChildren(emptyState(ICON.search, 'No results', `Nothing found for “${q}” on ${cfg.name}.`));
      else { st.items = r; renderResults() }
      blurIfTouch();
    }
    return {show(restoring) { if (!st.q) idle(); if (!restoring && matchMedia('(hover:hover)').matches) P.input.focus() },
            search, focus() { P.input.focus(); P.input.select() }};
  }

  // ---------- wiring ----------
  const ensure = k => pages[k] || (pages[k] = k === 'music' ? makeHome() : makePlatform(k));
  function openPlatform(key, q) { window.go(key); ensure(key).search(q) }
  window.musicShow = (tab, restoring) => {
    if (tab !== 'music' && !PLATFORMS[tab]) return;
    ensure(tab).show(restoring);
  };
  window.musicFocus = () => { ensure('music').focus() };
  window.musicClearRecents = () => { recents = []; saveRecents() };      // Settings > Clear history (pages redraw on their next visit)
  const cur = document.querySelector('.pane.on'); if (cur && (cur.id === 'music' || PLATFORMS[cur.id])) window.musicShow(cur.id, true);
})();
