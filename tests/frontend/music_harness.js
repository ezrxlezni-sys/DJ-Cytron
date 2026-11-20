// Runs the real music.js against a tiny fake DOM and a fake API, then drives the pages and checks what they render.
const fs = require('fs'), vm = require('vm'), path = require('path');
const SRC = fs.readFileSync(path.join(__dirname, '../../piplayer/static/js/music.js'), 'utf8');

// ---------- fake DOM ----------
const tokens = s => String(s || '').split(/\s+/).filter(Boolean);
function matcher(sel) {
  const m = sel.match(/^([a-z0-9]+)?((?:\.[\w-]+)*)(?:\[([\w-]+)(?:=([^\]]+))?\])?$/i);
  if (!m) throw new Error('unsupported selector ' + sel);
  const [, tag, cls, attr, val] = m, classes = tokens((cls || '').replace(/\./g, ' '));
  return n => (!tag || n.tag === tag) && classes.every(c => n.classList.contains(c)) && (!attr || (attr.startsWith('data-') ? n.dataset[attr.slice(5)] !== undefined && (val === undefined || n.dataset[attr.slice(5)] === val.replace(/"/g, '')) : n.attrs[attr] !== undefined));
}
class El {
  constructor(tag) {
    this.tag = tag; this.children = []; this.parent = null; this.attrs = {}; this.dataset = {}; this.style = {};
    this.className = ''; this.hidden = false; this.value = ''; this._text = ''; this.listeners = {}; this._html = '';
    const self = this;
    this.classList = {
      contains: c => tokens(self.className).includes(c),
      add: c => { if (!self.classList.contains(c)) self.className = (self.className + ' ' + c).trim() },
      remove: c => { self.className = tokens(self.className).filter(x => x !== c).join(' ') },
      toggle: (c, f) => { const on = f === undefined ? !self.classList.contains(c) : !!f; on ? self.classList.add(c) : self.classList.remove(c); return on },
    };
  }
  append(...nodes) { for (const n of nodes) { if (n == null) continue; if (typeof n === 'object') { if (n.parent) n.parent.children = n.parent.children.filter(c => c !== n); n.parent = this; this.children.push(n) } else this.children.push({text: String(n), parent: this}) } }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes) }
  replaceWith(...nodes) { const p = this.parent; if (!p) return; const i = p.children.indexOf(this); p.children.splice(i, 1, ...nodes); nodes.forEach(n => n.parent = p) }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); this.parent = null }
  set textContent(v) { this.children = []; this._text = String(v) }
  get textContent() { return this._text + this.children.map(c => c.text !== undefined ? c.text : c.textContent).join(' ') }
  set innerHTML(v) { this._html = v; this.children = [] }
  get innerHTML() { return this._html }
  setAttribute(k, v) { this.attrs[k] = String(v) }
  getAttribute(k) { return this.attrs[k] }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f) }
  fire(t, ev = {}) { for (const f of this.listeners['on' + t] || []) f(ev); for (const f of this.listeners[t] || []) f(ev); if (this['on' + t]) this['on' + t](ev) }
  walk(fn) { for (const c of this.children) if (c.tag) { if (fn(c) === false) return false; if (c.walk(fn) === false) return false } }
  all(sel) { const m = matcher(sel), out = []; this.walk(n => { if (m(n)) out.push(n) }); return out }
  querySelector(sel) { return this.all(sel)[0] || null }
  closest(sel) { const m = matcher(sel); for (let n = this; n; n = n.parent) if (n.tag && m(n)) return n; return null }
  focus() { ctx.__focused = this } select() {} blur() {}
}
const panes = {};
for (const id of ['music', 'ytm', 'yt', 'sc']) { panes[id] = new El('section'); panes[id].className = 'pane' }

// ---------- fake app.js helpers + API ----------
const calls = [], goCalls = [];
const song = (id, n, extra = {}) => ({kind: 'ytm', id, title: 'Song ' + n, artist: 'Artist ' + n, duration: 180 + n, thumb: 't' + n, art: 'a' + n, ...extra});
const FIX = {
  history: {recent: [song('r1', 1), song('r2', 2)], top: [song('t1', 3, {plays: 5})]},
  trending: Array.from({length: 20}, (_, i) => song('tr' + i, 10 + i)),
  suggested: Array.from({length: 9}, (_, i) => song('s' + i, 40 + i)),
};
let overrides = {};
function fakeApi(path, method, body) {
  calls.push([path, method, body]);
  return new Promise((res, rej) => setTimeout(() => {
    const key = Object.keys(overrides).find(k => path.includes(k));
    if (key) { const v = overrides[key]; return v === 'THROW' ? rej(new Error('net')) : res(v) }
    if (path.startsWith('search')) {
      const src = /source=(\w+)/.exec(path); const q = decodeURIComponent(/q=([^&]*)/.exec(path)[1]);
      if (!src) return res(Array.from({length: 20}, (_, i) => song('y' + i, i, {title: q + ' ytm ' + i})));
      if (src[1] === 'youtube') return res(Array.from({length: 12}, (_, i) => ({kind: 'yt', id: 'v'.repeat(11 - String(i).length) + i, title: q + ' video ' + i, artist: 'Chan', duration: null, thumb: 'th', art: 'ar'})));
      return res(Array.from({length: 7}, (_, i) => ({kind: 'sc', id: String(100 + i), title: q + ' sc ' + i, artist: 'DJ', duration: 200, url: 'https://soundcloud.com/u/t' + i})));
    }
    if (FIX[path]) return res(FIX[path]);
    res({ok: true});
  }, 5));
}
const store = {};
const ctx = {
  console, setTimeout, Promise, Object, Array, String, JSON, Set, Error,
  window: null, document: {querySelector: sel => (sel === '.pane.on' ? null : null)},
  localStorage: {getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v) }},
  matchMedia: () => ({matches: false}),
  $: sel => (sel.startsWith('#') && panes[sel.slice(1)]) || null,
  el: (tag, cls, txt) => { const e = new El(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e },
  api: fakeApi,
  ICON: new Proxy({}, {get: (_, k) => '<svg data-icon="' + String(k) + '"/>'}),
  CHEV_R: '<svg chev/>', fmt: s => Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'),
  toast: m => calls.push(['toast', m]), isNow: () => false, paintArt: (box, it) => { box.dataset.art = it.thumb || '' },
  pickPlaylist: items => calls.push(['pick', items.length]),
  emptyState: (icon, title, sub) => { const e = new El('div'); e.className = 'empty'; e.textContent = title + ' | ' + sub; return e },
  skeletonList: n => { const e = new El('div'); e.className = 'item-group skeleton-list'; return e },
  trackRow: (it, actions, idx) => {
    const r = new El('div'); r.className = 'item'; const g = new El('button'); g.className = 'go'; g.textContent = (idx != null ? idx + 1 + ' ' : '') + it.title; r.append(g);
    for (const a of actions) { const b = new El('button'); b.title = a[1]; b.onclick = a[2]; r.append(b) }
    return r;
  },
};
ctx.window = ctx; ctx.go = tab => goCalls.push(tab);
vm.createContext(ctx);
process.on('unhandledRejection', e => { console.log('UNHANDLED REJECTION', e); process.exitCode = 1 });
vm.runInContext(SRC, ctx);

// ---------- tiny test runner ----------
let failed = 0;
const check = (name, cond, extra = '') => { console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + extra)); if (!cond) failed++ };
const tick = (ms = 60) => new Promise(r => setTimeout(r, ms));
const text = n => n.textContent.replace(/\s+/g, ' ');
const submit = (pane, q) => { const form = pane.querySelector('form.m-search'), input = form.querySelector('input'); input.value = q; form.fire('submit', {preventDefault() {}}) };

(async () => {
  // ----- home -----
  ctx.musicShow('music', true); await tick();
  const home = panes.music, ht = text(home);
  check('home: title', /Music/.test(text(home.querySelector('h1'))));
  check('home: 3 platform cards', home.all('button.m-pcard').length === 3, home.all('button.m-pcard').length);
  check('home: shelves', ['Trending now', 'Suggested for you'].every(s => ht.includes(s)) && !/Continue listening|Mostly played/.test(ht), ht.slice(0, 400));
  check('home: trending ranked 1..10', home.all('div.item').filter(r => /^1 Song 10/.test(text(r))).length === 1 && !ht.includes('Song 20'));
  check('home: no back button text issue', !!home.querySelector('button.m-back') === false);
  home.all('button.m-pcard')[1].fire('click'); check('home: card opens YouTube page', goCalls.at(-1) === 'yt', goCalls);

  // ----- home search -----
  submit(home, 'lofi'); await tick();
  const tabs = home.all('button.m-tab');
  check('search: 4 tabs', tabs.length === 4, tabs.length);
  check('search: all three platforms listed', ['YouTube Music', 'YouTube', 'SoundCloud'].every(n => home.all('h2.msec-title').some(h => text(h) === n)), home.all('h2').map(text));
  check('search: top 5 per platform', home.all('div.item').length === 15, home.all('div.item').length);
  check('search: recents saved', JSON.parse(store['cdj-recent'])[0] === 'lofi');
  const openBtn = home.all('button.sg-link').find(b => /Open SoundCloud/.test(text(b)));
  check('search: "Open SoundCloud" link', !!openBtn);
  tabs[3].fire('click'); await tick(5);
  check('search: SoundCloud tab shows all 7', home.all('div.item').length === 7 && home.all('button.m-tab')[3].getAttribute('aria-pressed') === 'true', home.all('div.item').length);
  tabs[1].fire('click'); check('search: YouTube Music tab shows 20 rows', home.all('div.item').length === 20, home.all('div.item').length);
  // empty search returns to the idle home
  const inp = home.querySelector('input'); inp.value = ''; inp.fire('input'); await tick();
  check('search: clearing returns to platform cards', home.all('button.m-pcard').length === 3);

  // ----- partial failure keeps the other sources -----
  overrides = {'source=soundcloud': {error: 'boom'}};
  submit(home, 'jazz'); await tick();
  const titles = home.all('h2.msec-title').map(text);
  check('failure: sc hidden, others shown', titles.includes('YouTube Music') && titles.includes('YouTube') && !titles.includes('SoundCloud'), titles);
  overrides = {'source=soundcloud': 'THROW', 'source=youtube': 'THROW', 'type=songs': {error: 'down'}};
  submit(home, 'x'); await tick();
  check('failure: all sources failing shows an error', /Search failed/.test(text(home)), text(home).slice(0, 200));
  overrides = {'search?': []};
  submit(home, 'nothing'); await tick();
  check('empty: no results message', /No results/.test(text(home)), text(home).slice(0, 200));
  overrides = {};

  // ----- YouTube page -----
  ctx.musicShow('yt', true); await tick();
  const yt = panes.yt;
  check('yt: title + icon', /YouTube/.test(text(yt.querySelector('h1'))) && !!yt.querySelector('span.m-hicon'));
  check('yt: has back button for phones', !!yt.querySelector('button.m-back'));
  check('yt: idle shows try-searching chips', yt.all('button.m-chip').length >= 6, yt.all('button.m-chip').length);
  yt.all('button.m-chip')[0].fire('click'); await tick();
  check('yt: chip runs a search into the 16:9 grid', !!yt.querySelector('div.m-grid') && yt.querySelector('div.m-grid').classList.contains('wide') && yt.all('div.m-card').length === 12, yt.all('div.m-card').length);
  check('yt: result heading', /12 results for/.test(text(yt)), text(yt).slice(0, 120));
  check('yt: grid is the default view', yt.querySelector('.view-seg').querySelector('button[data-view=grid]').getAttribute('aria-pressed') === 'true');
  yt.querySelector('.view-seg').fire('click', {target: yt.querySelector('.view-seg').querySelector('button[data-view=list]')});
  check('yt: list view switch', !yt.querySelector('div.m-grid') && yt.all('div.item').length === 12 && JSON.parse(store['cdj-mview']).yt === 'list', yt.all('div.item').length);
  // card interactions
  yt.querySelector('.view-seg').fire('click', {target: yt.querySelector('.view-seg').querySelector('button[data-view=grid]')});
  const card1 = yt.all('div.m-card')[2];
  card1.querySelector('button.m-go').fire('click');
  const playCall = calls.filter(c => c[0] === 'play').at(-1);
  check('yt: clicking a card plays from it to the end', playCall && playCall[2].items.length === 10 && playCall[2].items[0].title.endsWith('video 2'), JSON.stringify(playCall).slice(0, 120));
  card1.querySelector('button.m-add').fire('click', {stopPropagation() {}}); await tick(10);
  check('yt: add button queues one item', calls.some(c => c[0] === 'queue' && c[2].items.length === 1));

  // ----- SoundCloud page -----
  ctx.musicShow('sc', true); await tick();
  const sc = panes.sc;
  check('sc: note about previews', /30-second previews/.test(text(sc)));
  submit(sc, 'ambient'); await tick();
  check('sc: list is the default view with 7 rows', sc.all('div.item').length === 7 && !sc.querySelector('div.m-grid'), sc.all('div.item').length);

  // ----- YouTube Music page -----
  ctx.musicShow('ytm', true); await tick();
  const ytm = panes.ytm;
  check('ytm: shelves + 20 trending', ['Trending now', 'Suggested for you'].every(s => text(ytm).includes(s)) && !/Continue listening|Mostly played/.test(text(ytm)) && text(ytm).includes('Song 29'));
  submit(ytm, 'hello'); await tick();
  check('ytm: search results (20)', ytm.all('div.item').length === 20, ytm.all('div.item').length);
  // leaving and returning with an active query keeps the results
  ctx.musicShow('ytm', false); await tick();
  check('ytm: results kept when you return', ytm.all('div.item').length === 20);
  // a stale search never overwrites a newer one
  overrides = {};
  submit(ytm, 'first'); submit(ytm, 'second'); await tick(80);
  check('ytm: newest search wins', /for “second”/.test(text(ytm)) && !/for “first”/.test(text(ytm)), text(ytm).slice(0, 100));

  // ----- the grid / list toggle also re-lays-out the START page (before any search) -----
  const toStart = pane => { const i = pane.querySelector('form.m-search').querySelector('input'); i.value = ''; i.fire('input') };
  const setView = async (pane, v) => { const seg = pane.querySelector('.view-seg'); seg.fire('click', {target: seg.querySelector('button[data-view=' + v + ']')}); await tick(150) };
  const shape = pane => ({shelves: pane.all('div.m-shelf').length, rows: pane.all('div.item').length, cards: pane.all('div.m-card').length, grids: pane.all('div.m-grid').filter(g => g.all('div.m-card').length > 0).length});
  toStart(yt); await tick(150);
  let sh = shape(yt);
  check('yt start: grid view = 5 scrolling cover shelves', sh.shelves === 5 && sh.rows === 0, JSON.stringify(sh));
  await setView(yt, 'list'); sh = shape(yt);
  check('yt start: list view = rows, 5 per topic', sh.shelves === 0 && sh.rows === 25, JSON.stringify(sh));
  await setView(yt, 'grid');
  toStart(sc); await tick(150);
  sh = shape(sc);
  check('sc start: list view = rows, 5 per topic', sh.shelves === 0 && sh.rows === 25, JSON.stringify(sh));
  await setView(sc, 'grid'); sh = shape(sc);
  check('sc start: grid view = 5 scrolling cover shelves', sh.shelves === 5 && sh.rows === 0, JSON.stringify(sh));
  await setView(sc, 'list');
  toStart(ytm); await tick(150);
  sh = shape(ytm);
  check('ytm start: list view = Trending (20) + Suggested (8) rows', sh.rows === 28 && sh.cards === 0, JSON.stringify(sh));
  await setView(ytm, 'grid'); sh = shape(ytm);
  check('ytm start: grid view = covers, no rows', sh.rows === 0 && sh.cards === 28, JSON.stringify(sh));
  check('ytm start: shelves keep their titles', ['Trending now', 'Suggested for you'].every(t => text(ytm).includes(t)));
  await setView(ytm, 'list');

  // ----- misc -----
  check('focus helper', typeof ctx.musicFocus === 'function'); ctx.musicFocus();
  check('unknown tab ignored', (() => { try { ctx.musicShow('radio'); return true } catch (e) { return false } })());
  console.log(failed ? `\n${failed} FAILED` : '\nALL PASSED');
  process.exit(failed ? 1 : 0);
})().catch(e => { console.log('HARNESS ERROR', e); process.exit(2) });
