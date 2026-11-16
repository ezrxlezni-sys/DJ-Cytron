/* Cytron DJ — frontend */
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const svg = (d, extra = '') => `<svg viewBox="0 0 24 24" ${extra.includes('fill=') ? '' : 'fill="currentColor"'} ${extra}>${d}</svg>`;
const stroke = d => svg(d, 'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"');
// Lucide icons (ISC) — the set ReUI/shadcn use. Play/pause are filled; the rest are 2px outlines.
const ICON = {
  play: '<svg viewBox="0 0 24 24"><path fill="currentColor" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></svg>',
  pause: '<svg viewBox="0 0 24 24"><g fill="currentColor" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><rect width="5" height="18" x="14" y="3" rx="1"/><rect width="5" height="18" x="5" y="3" rx="1"/></g></svg>',
  load: '<svg viewBox="0 0 24 24" class="spin"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 6L6 18M6 6l12 12"/></svg>',
  pen: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497zM15 5l4 4"/></svg>',
  add: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 5H3m8 7H3m13 7H3M18 9v6m3-3h-6"/></svg>',
  sun: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></g></svg>',
  moon: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"/></svg>',
  search: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="m21 21l-4.34-4.34"/><circle cx="11" cy="11" r="8"/></g></svg>',
  radio: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M16.247 7.761a6 6 0 0 1 0 8.478m2.828-11.306a10 10 0 0 1 0 14.134m-14.15 0a10 10 0 0 1 0-14.134m2.828 11.306a6 6 0 0 1 0-8.478"/><circle cx="12" cy="12" r="2"/></g></svg>',
  check: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 6L9 17l-5-5"/></svg>',
  vol: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298zM16 9a5 5 0 0 1 0 6m3.364 3.364a9 9 0 0 0 0-12.728"/></svg>',
  mute: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4.702a.7.7 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.7.7 0 0 0 11 19.298zm5.5 9.798l5-5m-5 0l5 5"/></svg>',
  pladd: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 7v6m3-3H9m8-7a2 2 0 0 1 2 2v15a1 1 0 0 1-1.496.868l-4.512-2.578a2 2 0 0 0-1.984 0l-4.512 2.578A1 1 0 0 1 5 20V5a2 2 0 0 1 2-2z"/></svg>',
  plist: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M16 5H3m8 7H3m8 7H3m18-3V5"/><circle cx="18" cy="16" r="3"/></g></svg>',
  back: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m12 19l-7-7l7-7m7 7H5"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 11v6m4-6v6m5-11v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
  repeat: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="m17 2l4 4l-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4l4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></g></svg>',
  repeat1: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="m17 2l4 4l-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4l4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3m8-8h1v4"/></g></svg>',
  list: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M16 5H3m8 7H3m8 7H3m18-3V5"/><circle cx="18" cy="16" r="3"/></g></svg>',
};
const EQ = '<i class="eq"><u></u><u></u><u></u></i>';

let S = {queue: [], index: -1}, stations = [], playlists = [], openPl = null, editing = false, editId = null, tickBase = {t: 0, pos: 0}, dragging = false;

const api = (path, method = 'GET', body) => fetch('/api/' + path, {
  method, headers: body ? {'Content-Type': 'application/json'} : {}, body: body && JSON.stringify(body)
}).then(r => r.json().catch(() => ({error: 'Server error ' + r.status})));     // a non-JSON reply (500 page) becomes {error}
const ctl = (a, b) => api('control/' + a, 'POST', b);
const fmt = s => { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0') };
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e };
const fill = r => r.style.setProperty('--p', (r.value - r.min) / (r.max - r.min) * 100 + '%');
const isNow = it => S.current && it.kind === S.current.kind && it.id === S.current.id;
const thumbOf = it => it.thumb || (it.kind === 'radio' && (stations.find(x => x.id === it.id) || {}).thumb) || '';
const isLogo = it => it.kind === 'radio' && !!thumbOf(it);

// Sonner-style toast
let toastT;
function toast(msg) {
  const t = $('#toast'); t.innerHTML = ICON.check; t.append(msg); t.classList.remove('on'); void t.offsetWidth; t.classList.add('on');   // reflow restarts the entrance for back-to-back toasts
  clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 3200);
}

/** Fills a container with artwork (image or initial) and sets its logo/cover style. */
function paintArt(box, it) {
  box.classList.toggle('logo', !!it && isLogo(it));
  const src = it && (box.classList.contains('big') && it.art ? it.art : thumbOf(it));   // big player uses the hi-res cover
  const key = src || (it ? 'T' + (it.title || '?')[0] : 'note');
  if (box.dataset.art === key) return;           // same cover: leave the <img> alone (re-creating it flashes)
  box.dataset.art = key;
  box.replaceChildren();
  if (src) { const i = el('img'); i.decoding = 'async'; i.onload = () => i.classList.add('in'); i.src = src; i.alt = ''; box.append(i) }
  else box.textContent = it ? (it.title || '?')[0] : '♪';
}

// ---- theme (.dark class, like shadcn) ----
function applyTheme(t) {
  const root = document.documentElement;
  if (t) { root.classList.toggle('dark', t === 'dark'); try { localStorage.setItem('cdj-theme', t) } catch (e) {} }
  const dark = root.classList.contains('dark');
  $$('.theme').forEach(b => b.innerHTML = dark ? ICON.sun : ICON.moon);
  document.querySelector('meta[name=theme-color]').content = dark ? '#09090b' : '#ffffff';
  return dark;
}
$$('.theme').forEach(b => b.onclick = () => applyTheme(applyTheme() ? 'light' : 'dark'));
applyTheme();

// ---- Select (ReUI/shadcn style): styled trigger + popover list; the native <select> stays as the value holder ----
const CHEV = '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m7 15l5 5l5-5M7 9l5-5l5 5"/></svg>';
const TICK = '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 6L9 17l-5-5"/></svg>';
function closeSelects(except) {
  $$('.sel.open').forEach(w => { if (w !== except) w.close() });
}
function enhanceSelect(native) {
  const wrap = el('div', 'sel');
  native.before(wrap); wrap.append(native); native.hidden = true; native.tabIndex = -1;
  const btn = el('button', 'input sel-btn'); btn.type = 'button';
  btn.setAttribute('aria-haspopup', 'listbox'); btn.setAttribute('aria-expanded', 'false');
  const lab = el('span'); btn.append(lab); btn.insertAdjacentHTML('beforeend', CHEV);
  wrap.append(btn);
  let pop = null;
  const text = () => (native.selectedOptions[0] || {}).text || '';
  wrap.sync = () => { lab.textContent = text() };
  wrap.close = () => {
    if (!pop) return;
    const gone = pop; pop = null; gone.classList.add('closing'); setTimeout(() => gone.remove(), 110);
    wrap.classList.remove('open'); btn.setAttribute('aria-expanded', 'false');
  };
  const pick = o => { native.value = o.value; wrap.sync(); native.dispatchEvent(new Event('change', {bubbles: true})); wrap.close(); btn.focus() };
  wrap.open = () => {
    closeSelects(wrap);
    pop = el('div', 'sel-pop'); pop.setAttribute('role', 'listbox');
    [...native.options].forEach(o => {
      const it = el('button', 'sel-item' + (o.value === native.value ? ' on' : ''));
      it.type = 'button'; it.setAttribute('role', 'option'); it.setAttribute('aria-selected', o.value === native.value);
      it.append(el('span', '', o.text)); it.insertAdjacentHTML('beforeend', TICK);
      it.onclick = () => pick(o); pop.append(it);
    });
    wrap.append(pop); wrap.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
    const r = btn.getBoundingClientRect();
    wrap.classList.toggle('up', innerHeight - r.bottom < 280 && r.top > innerHeight - r.bottom);   // flip above when short of room
    const on = pop.querySelector('.on'); if (on) { pop.scrollTop = on.offsetTop - pop.clientHeight / 2 + on.offsetHeight / 2; on.focus({preventScroll: true}) }
  };
  btn.onclick = () => pop ? wrap.close() : wrap.open();
  btn.onkeydown = e => { if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); if (!pop) wrap.open() } };
  wrap.addEventListener('keydown', e => {
    if (!pop) return;
    const items = [...pop.children], i = items.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.stopPropagation(); wrap.close(); btn.focus() }
    else if (e.key === 'ArrowDown') { e.preventDefault(); items[Math.min(items.length - 1, i + 1)].focus() }
    else if (e.key === 'ArrowUp') { e.preventDefault(); items[Math.max(0, i - 1)].focus() }
    else if (e.key === 'Home') { e.preventDefault(); items[0].focus() }
    else if (e.key === 'End') { e.preventDefault(); items[items.length - 1].focus() }
    else if (e.key === 'Tab') wrap.close();
  });
  wrap.sync();
}
document.addEventListener('click', e => { if (!e.target.closest('.sel')) closeSelects() });

// ---- settings: restroom door sensors (state arrives in S.doors with the normal state stream) ----
const doorForm = $('#doorform');
const pad2 = n => String(n).padStart(2, '0');
const HALF_HOURS = Array.from({length: 48}, (_, i) => {
  const h = i >> 1, m = i % 2 * 30;
  return [pad2(h) + ':' + pad2(m), ((h + 11) % 12 + 1) + ':' + pad2(m) + ' ' + (h < 12 ? 'AM' : 'PM')];
});
for (const sel of [doorForm.from, doorForm.to]) { HALF_HOURS.forEach(([v, t]) => sel.append(new Option(t, v))); enhanceSelect(sel) }
for (const s of [0, 3, 5, 10, 15, 30, 60]) doorForm.fade.append(new Option(s ? s + ' seconds' : 'Off', String(s)));
enhanceSelect(doorForm.fade);
for (const s of [0, 1, 2, 3, 5, 10, 15]) doorForm.fadeout.append(new Option(s ? s + (s === 1 ? ' second' : ' seconds') : 'Off', String(s)));
enhanceSelect(doorForm.fadeout);
for (const [v, t] of [[100, 'No dip'], [70, 'Slightly lower (70%)'], [50, 'Half (50%)'], [30, 'Quiet (30%)'], [15, 'Very quiet (15%)'], [0, 'Silent']]) doorForm.duck.append(new Option(t, String(v)));
for (const s of [0, 1, 2, 4, 8]) doorForm.rise.append(new Option(s ? s + (s === 1 ? ' second' : ' seconds') : 'Instantly', String(s)));
enhanceSelect(doorForm.duck); enhanceSelect(doorForm.rise); enhanceSelect(doorForm.voice);
// "en_GB-alan-medium" -> "Alan (en GB, medium)"; "" is the automatic choice
const voiceName = v => v === 'espeak-ng' ? 'Robotic (espeak-ng)' : (m => m ? (n => n[0].toUpperCase() + n.slice(1))(m[2].replace(/_/g, ' ')) + ' (' + m[1].replace('_', ' ') + ', ' + m[3] + ')' : v)(/^([a-z]{2}_[A-Z]{2})-(.+)-(x_low|low|medium|high)$/.exec(v));
function paintVoices(d) {
  const sel = doorForm.voice, key = (d.voices || []).join('|');
  if (sel.dataset.key !== key) {                              // rebuild only when the installed voices change
    sel.dataset.key = key; sel.replaceChildren(new Option('Automatic (best available)', ''), ...(d.voices || []).map(v => new Option(voiceName(v), v)));
  }
  sel.value = (d.voices || []).includes(d.voice) ? d.voice : '';
}
function showDoorErr(msg) { const e = $('#doorerr'); e.textContent = msg || ''; e.hidden = !msg }
const hoursDim = () => {
  ['#hoursrow', '#faderow', '#fadeoutrow'].forEach(id => $(id).classList.toggle('off', !doorForm.autoplay.checked));
  ['#welcomerow', '#reminderrow', '#voicerow', '#duckrow', '#risesrow'].forEach(id => $(id).classList.toggle('off', !doorForm.announce.checked));
};
doorForm.autoplay.addEventListener('change', hoursDim);
doorForm.announce.addEventListener('change', hoursDim);
function paintDoors(force) {
  const d = S.doors, f = doorForm;
  if (!d) return;
  const n = d.active.length, g = $('#gpiostate');
  g.textContent = d.error ? 'Sensor error' : n ? n + ' of 2 sensors active' : 'No sensors';
  g.className = 'badge ' + (d.error ? 'destructive-light' : n ? 'success-light' : 'outline');
  $('#gpioerr').textContent = d.error || ''; $('#gpioerr').hidden = !d.error;
  if (!force && f.contains(document.activeElement)) return;          // never overwrite what's being typed
  f.male.value = d.pins.male ?? ''; f.female.value = d.pins.female ?? '';
  f.autoplay.checked = d.autoplay; f.from.value = d.from; f.to.value = d.to; f.fade.value = String(d.fade ?? 5); f.fadeout.value = String(d.fadeout ?? 3);
  paintVoices(d); f.duck.value = String(d.duck ?? 30); f.rise.value = String(d.rise ?? 2);
  f.announce.checked = d.announce !== false; f.welcome.value = d.welcome ?? ''; f.reminder.value = d.reminder ?? '';
  $('#speecherr').hidden = d.speech !== false;                   // shown only while the speech engine is missing
  hoursDim();
  $$('.sel').forEach(s => s.sync());
}
// auto-save: selects/switch save at once, pin numbers once you leave the field (debounced)
let saveTimer = 0, saveSeq = 0;
async function saveDoors() {
  clearTimeout(saveTimer);
  const f = doorForm, num = v => v === '' ? null : Number(v), seq = ++saveSeq;
  showDoorErr();
  const r = await api('doors', 'POST', {pins: {male: num(f.male.value), female: num(f.female.value)},
    autoplay: f.autoplay.checked, from: f.from.value, to: f.to.value, fade: Number(f.fade.value), fadeout: Number(f.fadeout.value), duck: Number(f.duck.value), rise: Number(f.rise.value), voice: f.voice.value,
    announce: f.announce.checked, welcome: f.welcome.value, reminder: f.reminder.value}).catch(() => ({error: 'Request failed'}));
  if (seq !== saveSeq) return;                                       // a newer save is in flight
  if (r.error) return showDoorErr(r.error);
  toast('Saved');
}
const queueSave = () => { clearTimeout(saveTimer); saveTimer = setTimeout(saveDoors, 450) };
doorForm.addEventListener('change', queueSave);
doorForm.onsubmit = e => { e.preventDefault(); saveDoors() };
// preview buttons: save what is typed first, then speak the saved message on the Pi's speakers
$$('[data-say]').forEach(b => b.onclick = async () => {
  await saveDoors();
  const r = await api('doors/announce', 'POST', {which: b.dataset.say}).catch(() => ({error: 'Request failed'}));
  if (r && r.error) toast(r.error);
});

// ---- clear history (Settings) ----
$('#clearhist').onclick = async () => {
  if (!confirm('Clear the play history?\n\nThis forgets what was played on this Pi and your recent searches in this browser.')) return;
  const r = await api('history', 'DELETE').catch(() => ({error: 'Request failed'}));
  if (r && r.error) return toast(r.error);
  if (window.musicClearRecents) window.musicClearRecents();
  toast('History cleared');
};

// ---- power (shut down / reboot) ----
const pdlg = $('#pdlg');
let powerAct = null;
const POWER = {
  shutdown: ['Shut down?', 'The Pi will power off. You will need to switch it back on by hand.', 'Shut down', 'Shutting down…'],
  reboot: ['Reboot?', 'The Pi will restart. Playback stops and the page reconnects in about a minute.', 'Reboot', 'Rebooting…']};
$$('[data-power]').forEach(b => b.onclick = () => {
  powerAct = b.dataset.power; const p = POWER[powerAct];
  $('#pdlgtitle').textContent = p[0]; $('#pdlgmsg').textContent = p[1]; $('#pgo').textContent = p[2];
  pdlg.showModal();
});
$('#pcancel').onclick = () => pdlg.close();
pdlg.addEventListener('click', e => { if (e.target === pdlg) pdlg.close() });
$('#pgo').onclick = async () => {
  const act = powerAct; pdlg.close();
  const r = await fetch('/api/system/' + act, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}).then(x => x.json()).catch(() => ({error: 'Request failed'}));
  toast(r.error || POWER[act][3]);
};

// ---- navigation ----
function go(tab, restoring) {
  const inMusic = tab === 'ytm' || tab === 'yt' || tab === 'sc';       // platform pages light up Music in the phone tab bar
  $$('[data-tab]').forEach(x => x.classList.toggle('on', x.dataset.tab === tab || (inMusic && x.dataset.tab === 'music' && !!x.closest('#tabbar'))));
  $$('.pane').forEach(x => x.classList.toggle('on', x.id === tab));
  $('main').scrollTop = 0;
  if (tab === 'settings') paintDoors(true);
  if (tab === 'queue') loadPlaylists();
  if (typeof musicShow === 'function') musicShow(tab, restoring);     // music.js: build/refresh the Music pages
  try { localStorage.setItem('cdj-tab', tab) } catch (e) {}          // remembered across refreshes
}
try { const t = localStorage.getItem('cdj-tab'); if (t && document.getElementById(t)?.classList.contains('pane')) go(t, true) } catch (e) {}
document.addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) go(b.dataset.tab) });

/** ReUI Empty: icon tile + title + description (+ optional action). */
const emptyState = (icon, title, sub, action) => {
  const e = el('div', 'empty');
  const t = el('div', 'tile'); t.innerHTML = icon;
  const d = el('div'); d.append(el('div', 'empty-title', title), el('div', 'empty-desc', sub));
  e.append(t, d);
  if (action) { const b = el('button', 'btn outline sm', action[0]); b.onclick = action[1]; e.append(b) }
  return e;
};
const skeletonList = n => {
  const l = el('div', 'item-group');
  for (let i = 0; i < n; i++) {
    const r = el('div', 'item sk'), ln = el('div', 'sk-lines');
    const a = el('div', 'skeleton'), b = el('div', 'skeleton');
    a.style.cssText = 'height:14px;width:55%'; b.style.cssText = 'height:12px;width:30%';
    ln.append(a, b); r.append(el('div', 'item-media'), ln); l.append(r);
  }
  return l;
};

// ---- radio ----
let stationSig = '';
function renderStations() {
  const g = $('#stations');
  $('#c-radio').textContent = stations.length || '';
  const sig = JSON.stringify(stations.map(s => [s.id, s.title, s.thumb, s.url, s.category]));
  if (sig !== stationSig || !stations.length) {          // the list itself changed: rebuild once
    stationSig = sig; g.replaceChildren();
    if (!stations.length) {
      return g.append(emptyState(ICON.radio, 'No stations yet', 'Add a stream URL to start listening.', ['Add station', () => openDlg(null)]));
    }
    // group by category, in order of first appearance; stations without one go last under "My stations"
    const cats = new Map();
    for (const st of stations) { const k = st.category || 'My stations'; if (!cats.has(k)) cats.set(k, []); cats.get(k).push(st) }
    const ordered = [...cats].sort((a, b) => (a[0] === 'My stations') - (b[0] === 'My stations'));
    for (const [cat, list] of ordered) {
      const h = el('h2', 'cat-head', cat); h.append(el('em', 'count', String(list.length))); g.append(h);
      for (const st of list) {
      const c = el('div', 'card'); c.tabIndex = 0; c.setAttribute('role', 'button'); c.dataset.id = st.id; c.dataset.q = (st.title + ' ' + (st.category || '')).toLowerCase();
      const a = el('div', 'art' + (st.thumb ? ' logo' : ''), st.thumb ? null : st.title[0]);
      if (st.thumb) { const im = el('img'); im.src = st.thumb; im.alt = ''; im.loading = 'lazy'; im.decoding = 'async'; im.onload = () => im.classList.add('in'); a.append(im) }
      const ph = el('span', 'playhint'), sub = el('div', 's');
      const txt = el('div', 'txt'); txt.append(el('div', 't', st.title), sub);
      const foot = el('div', 'foot'); foot.append(txt, ph);
      c.append(a, foot);
      const play = () => editing ? openDlg(st) : isNow({kind: 'radio', id: st.id}) && S.playing ? ctl('toggle') : api('play', 'POST', {station: st.id});
      c.onclick = play;
      c.onkeydown = ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); play() } };
      const pen = el('span', 'pen'); pen.innerHTML = ICON.pen; c.append(pen); g.append(c);
      }
    }
  }
  if (typeof applyStFilter === 'function') applyStFilter();   // keep an active search applied after a rebuild
  // cheap in-place update of the live bits only (no images or animations are recreated)
  for (const c of g.children) {
    if (!c.dataset.id) continue;
    const now = isNow({kind: 'radio', id: c.dataset.id}), on = now && S.playing && !S.paused;
    c.classList.toggle('now', now);
    const phk = S.loading && now ? 'load' : on ? 'pause' : 'play', ph = c.querySelector('.playhint');
    if (ph.dataset.k !== phk) { ph.dataset.k = phk; ph.innerHTML = ICON[phk] }
    const sub = c.querySelector('.s'), sk = now ? (on ? 'eq:' : ':') + (S.loading ? 'Connecting…' : S.paused ? 'Paused' : 'On air') : '';
    if (sub.dataset.k !== sk) {
      sub.dataset.k = sk; sub.classList.toggle('on', now);
      if (now) sub.innerHTML = (on ? EQ : '') + (S.loading ? 'Connecting…' : S.paused ? 'Paused' : 'On air');
      else sub.textContent = '';
    }
  }
}

// ---- radio search + grid/list view ----
const stSearch = $('#stsearch'), stClear = $('#stclear'), viewSeg = $('#viewseg');
let stView = 'grid';
try { if (localStorage.getItem('cdj-stview') === 'list') stView = 'list' } catch (e) {}
function applyStView() {
  $('#stations').classList.toggle('list', stView === 'list');
  for (const b of viewSeg.children) b.setAttribute('aria-pressed', String(b.dataset.view === stView));
}
function applyStFilter() {
  const q = stSearch.value.trim().toLowerCase(), words = q.split(/\s+/).filter(Boolean);
  let head = null, n = 0, total = 0;
  for (const c of $('#stations').children) {
    if (c.classList.contains('cat-head')) { if (head) head.hidden = !n; head = c; n = 0; continue }
    const show = words.every(w => (c.dataset.q || '').includes(w));
    c.hidden = !show; if (show) { n++; total++ }
  }
  if (head) head.hidden = !n;
  $('#stnone').hidden = !q || total > 0 || !stations.length;
  stClear.hidden = !stSearch.value; stSearch.parentElement.classList.toggle('has-q', !!stSearch.value);
}
stSearch.oninput = applyStFilter;
stSearch.onkeydown = ev => { if (ev.key === 'Escape' && stSearch.value) { stSearch.value = ''; applyStFilter() } };
stClear.onclick = () => { stSearch.value = ''; applyStFilter(); stSearch.focus() };
viewSeg.onclick = ev => {
  const b = ev.target.closest('button[data-view]'); if (!b) return;
  stView = b.dataset.view; try { localStorage.setItem('cdj-stview', stView) } catch (e) {} applyStView();
};
applyStView();

// edit mode: cards are only editable while on
$('#editbtn').onclick = () => {
  editing = !editing;
  $('#radio').classList.toggle('editing', editing);
  $('#editbtn span').textContent = editing ? 'Done editing' : 'Edit stations';
  $('#moremenu').classList.toggle('on', editing);
};

// add / edit station dialog
const dlg = $('#dlg'), addErr = $('#adderr'), form = $('#addst');
function openDlg(st) {
  editId = st ? st.id : null;
  form.reset(); addErr.hidden = true;
  if (st) { form.title.value = st.title; form.url.value = st.url }
  $('#dlgtitle').textContent = st ? 'Edit station' : 'Add station';
  $('#savebtn').textContent = st ? 'Save changes' : 'Add station';
  $('#rmbtn').hidden = !st;
  dlg.showModal(); form.title.focus();
}
$('#addbtn').onclick = () => openDlg(null);
// "..." dropdown menu (Add / Edit)
const moreBtn = $('#moremenu'), moreMenu = $('#radiomenu');
const menuOpen = o => { moreMenu.hidden = !o; moreBtn.setAttribute('aria-expanded', o) };
moreBtn.onclick = e => { e.stopPropagation(); menuOpen(moreMenu.hidden) };
moreMenu.addEventListener('click', () => menuOpen(false));
document.addEventListener('click', e => { if (!moreMenu.hidden && !e.target.closest('.menu-wrap')) menuOpen(false) });
document.addEventListener('keydown', e => { if (e.key === 'Escape') menuOpen(false) });
$('#cancel').onclick = $('#dlgx').onclick = () => dlg.close();
dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close() });
$('#rmbtn').onclick = async () => {
  const st = stations.find(x => x.id === editId); if (!st) return;
  if (!confirm('Remove ' + st.title + '?')) return;
  stations = await api('stations/' + editId, 'DELETE'); renderStations(); dlg.close(); toast('Station removed');
};
form.onsubmit = async e => {
  e.preventDefault();
  const body = {title: form.title.value, url: form.url.value};
  const r = editId ? await api('stations/' + editId, 'PUT', body) : await api('stations', 'POST', body);
  if (Array.isArray(r)) { stations = r; renderStations(); dlg.close(); toast(editId ? 'Station updated' : 'Station added') }
  else { addErr.textContent = r.error || 'Could not save station'; addErr.hidden = false }
};

// ---- lists (search + queue): ReUI Item ----
function trackRow(it, actions, idx) {
  const r = el('div', 'item' + (isNow(it) ? ' now' : ''));
  const g = el('button', 'go');
  if (idx != null) g.append(el('span', 'idx', idx + 1));
  const th = el('div', 'item-media'); paintArt(th, it);
  const m = el('div', 'item-body');
  m.append(el('span', 'item-title', it.title), el('span', 'item-desc', [it.artist, it.duration && fmt(it.duration)].filter(Boolean).join(' · ')));
  g.append(th, m); r.append(g);
  for (const [icon, title, fn] of actions) {
    const b = el('button', 'btn ghost icon muted'); b.innerHTML = icon; b.title = title; b.setAttribute('aria-label', title); b.onclick = fn; r.append(b);
  }
  return r;
}

const CHEV_R = '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m9 18l6-6l-6-6"/></svg>';
// (Music lives in music.js)

// ---- queue ----
const GRIP = '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><circle cx="9" cy="12" r="1"/><circle cx="9" cy="5" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="19" r="1"/></g></svg>';
let qDrag = null, qSig = '', playedOpen = false, playedAnim = false;
const qDur = list => {
  const s = list.reduce((a, t) => a + (t.duration || 0), 0), m = Math.round(s / 60);
  return !s ? '' : m < 60 ? m + ' min' : Math.floor(m / 60) + ' h ' + (m % 60) + ' min';
};
function qRow(it, i, upcoming) {
  const r = trackRow({...it, artist: it.artist || (it.kind === 'radio' ? 'Live radio' : '')},
    [[ICON.x, 'Remove from queue', () => api('queue/' + i, 'DELETE')]]);
  r.dataset.i = i;
  r.querySelector('.go').onclick = () => api('play', 'POST', {index: i});
  if (upcoming) { const h = el('button', 'drag'); h.type = 'button'; h.innerHTML = GRIP; h.setAttribute('aria-label', 'Drag to reorder'); r.prepend(h); attachDrag(h, r) }
  else r.classList.add('played');
  return r;
}
// drag a row by its handle (pointer events: works with mouse and touch); other rows slide aside, the row settles, then POST /queue/move
function attachDrag(handle, row) {
  handle.onpointerdown = e => {
    e.preventDefault(); handle.setPointerCapture(e.pointerId);
    const rows = [...row.parentElement.children], me = rows.indexOf(row), first = +rows[0].dataset.i, from = +row.dataset.i, y0 = e.clientY;
    const pitch = rows.length > 1 ? rows[1].getBoundingClientRect().top - rows[0].getBoundingClientRect().top : row.offsetHeight;
    const lo = -me * pitch, hi = (rows.length - 1 - me) * pitch, slotOf = dy => Math.round(Math.min(hi, Math.max(lo, dy)) / pitch);
    qDrag = from; row.classList.add('dragging');
    rows.forEach(r => r !== row && r.classList.add('shift'));
    const place = slot => rows.forEach((r, j) => {
      if (r === row) return;
      r.style.transform = slot > 0 && j > me && j <= me + slot ? `translateY(${-pitch}px)` : slot < 0 && j < me && j >= me + slot ? `translateY(${pitch}px)` : '';
    });
    handle.onpointermove = ev => {
      const dy = ev.clientY - y0;
      row.style.transform = `translateY(${Math.min(hi, Math.max(lo, dy))}px)`;
      place(slotOf(dy));
    };
    const end = (ev, cancelled) => {
      handle.onpointermove = handle.onpointerup = handle.onpointercancel = null;
      const slot = cancelled ? 0 : slotOf(ev.clientY - y0), to = first + me + slot;
      row.classList.replace('dragging', 'settle'); row.style.transform = slot ? `translateY(${slot * pitch}px)` : '';
      setTimeout(() => {                                                 // let the settle finish, then commit
        qDrag = null; qSig = '';
        if (to !== from) api('queue/move', 'POST', {from, to}); else renderQueue();
      }, matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 190);
    };
    handle.onpointerup = ev => end(ev, false);
    handle.onpointercancel = ev => end(ev, true);
  };
}
function renderQueue() {
  const n = S.queue.length, cur = S.index;
  $('#c-queue').textContent = n || ''; $('#c-queue2').textContent = n || '';
  const upcoming = S.queue.slice(cur + 1), left = [S.queue[cur], ...upcoming].filter(Boolean);
  if (qview === 'queue') $('#qsub').textContent = n ? [`${n} track${n > 1 ? 's' : ''}`, qDur(left) && qDur(left) + ' left'].filter(Boolean).join(' · ') : 'Nothing queued.';
  ['qsave', 'qclearall'].forEach(id => $('#' + id).disabled = !n); $('#qclearnext').disabled = !upcoming.length;
  if (qDrag != null) return;                                            // don't rebuild under a drag
  const playing = !!(S.playing && !S.paused);
  const sig = JSON.stringify([S.queue.map(t => t.id), cur, playing, !!S.loading, !!S.paused, playedOpen]);
  if (sig === qSig) return;                                             // nothing visible changed: keep the DOM (no flicker)
  qSig = sig;
  const b = $('#qlist'); b.replaceChildren();
  if (!n) return b.append(emptyState(ICON.list, 'Queue is empty', 'Play a station or add tracks from Music.', ['Browse radio', () => go('radio')]));
  const now = S.queue[cur];
  if (now) {                                                            // NOW PLAYING card
    b.append(el('div', 'qlabel', 'Now playing'));
    const card = el('button', 'qnow'); card.type = 'button';
    const art = el('div', 'np-art qnow-art'); paintArt(art, now);
    const meta = el('div', 'qnow-meta');
    const status = el('span', 'qnow-status');
    status.innerHTML = (playing ? EQ : '') + (S.loading ? 'Connecting…' : S.paused ? 'Paused' : 'Playing');
    meta.append(el('span', 'item-title', now.title), el('span', 'item-desc', now.artist || (now.kind === 'radio' ? 'Live radio' : '')), status);
    card.append(art, meta);
    card.onclick = () => ctl('toggle');
    b.append(card);
  }
  b.append(el('div', 'qlabel', upcoming.length ? `Next up · ${upcoming.length}` : 'Next up'));
  if (!upcoming.length) b.append(el('div', 'qempty', 'Nothing after this. Add songs from Music or Playlists.'));
  else {
    const list = el('div', 'item-group qnext');
    upcoming.forEach((it, k) => list.append(qRow(it, cur + 1 + k, true)));
    b.append(list);
  }
  const played = S.queue.slice(0, Math.max(cur, 0));
  if (played.length) {                                                  // PLAYED history (collapsed)
    const t = el('button', 'qplayed-toggle' + (playedOpen ? ' open' : '')); t.type = 'button';
    t.innerHTML = CHEV_R; t.append(el('span', '', `Played · ${played.length}`));
    t.onclick = () => { playedOpen = !playedOpen; playedAnim = playedOpen; qSig = ''; renderQueue() };
    b.append(t);
    if (playedOpen) { const list = el('div', 'item-group' + (playedAnim ? ' qplayed-rows' : '')); playedAnim = false; played.forEach((it, i) => list.append(qRow(it, i, false))); b.append(list) }
  }
  applyQFilter();
}
// filter the queue rows by title / artist (rows are hidden in place, so playback and drag order are untouched)
const qFilter = $('#qfilter'), qClr = $('#qclr');
function applyQFilter() {
  const words = qFilter.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  let shown = 0, total = 0;
  const root = qview === 'queue' ? $('#qlist') : $('#pllist');
  for (const r of root.querySelectorAll('.item-group > *')) {
    const ok = words.every(w => r.textContent.toLowerCase().includes(w)); r.hidden = !ok; total++; if (ok) shown++;
  }
  $('#qnone').textContent = qview === 'queue' ? 'No tracks match your filter.' : 'Nothing matches your filter.';
  $('#qnone').hidden = !words.length || shown > 0 || !total;
  qClr.hidden = !qFilter.value; qFilter.parentElement.classList.toggle('has-q', !!qFilter.value);
}
qFilter.oninput = applyQFilter;
qFilter.onkeydown = ev => { if (ev.key === 'Escape' && qFilter.value) { qFilter.value = ''; applyQFilter() } };
qClr.onclick = () => { qFilter.value = ''; applyQFilter(); qFilter.focus() };
// queue "⋮" menu
(function () {
  const btn = $('#qmore'), menu = $('#qmenu');
  const open = o => { menu.hidden = !o; btn.setAttribute('aria-expanded', o) };
  btn.onclick = e => { e.stopPropagation(); open(menu.hidden) };
  menu.addEventListener('click', () => open(false));
  document.addEventListener('click', e => { if (!menu.hidden && !e.target.closest('#qmenuwrap')) open(false) });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') open(false) });
  $('#qclearnext').onclick = () => api('queue/clear', 'POST', {scope: 'upcoming'}).then(() => toast('Cleared up next'));
  $('#qclearall').onclick = () => { if (confirm('Clear the whole queue and stop playback?')) api('queue/clear', 'POST', {scope: 'all'}).then(() => toast('Queue cleared')) };
})();

// ---- playlists ----
const plDlg = $('#pldlg'), plForm = $('#plform'), pickDlg = $('#pickdlg'), pickForm = $('#pickform');
let plEdit = null, qview = 'queue';
function setQView(v) {
  qview = v;
  $('#segq').classList.toggle('on', v === 'queue'); $('#segp').classList.toggle('on', v === 'playlists');
  $('#qlist').hidden = v !== 'queue'; $('#pllist').hidden = v !== 'playlists';
  $('#plnew').hidden = v !== 'playlists'; for (const id of ['qsave', 'qclearnext', 'qclearall']) $('#' + id).hidden = v !== 'queue'; qFilter.placeholder = qFilter.ariaLabel = v === 'queue' ? 'Filter queue' : 'Filter playlists'; qFilter.value = ''; applyQFilter();
  if (v === 'queue') { qSig = ''; renderQueue() } else $('#qsub').textContent = 'Your saved lists.';
}
$('#segq').onclick = () => setQView('queue');
$('#segp').onclick = () => { setQView('playlists'); loadPlaylists() };
async function loadPlaylists() { const r = await api('playlists'); if (Array.isArray(r)) { playlists = r; renderPlaylists() } }
const plCount = p => `${p.items.length} track${p.items.length === 1 ? '' : 's'}`;
function renderPlaylists() { renderPlaylistsInner(); applyQFilter() }
function renderPlaylistsInner() {
  $('#c-playlists').textContent = playlists.length || '';
  const box = $('#pllist'); box.replaceChildren();
  const cur = playlists.find(p => p.id === openPl);
  if (!cur) openPl = null;
  if (!cur) {
    if (!playlists.length) return box.append(emptyState(ICON.plist, 'No playlists yet', 'Create one, then add songs from Music or save your queue.', ['New playlist', () => openPlDlg(null)]));
    const list = el('div', 'item-group');
    for (const p of playlists) {
      const r = el('div', 'item'), g = el('button', 'go'), th = el('div', 'item-media'), m = el('div', 'item-body');
      th.innerHTML = ICON.plist;
      m.append(el('span', 'item-title', p.name), el('span', 'item-desc', plCount(p)));
      g.append(th, m); g.onclick = () => { openPl = p.id; renderPlaylists() }; r.append(g);
      const pb = el('button', 'btn ghost icon muted'); pb.innerHTML = ICON.play; pb.title = pb.ariaLabel = 'Play'; pb.disabled = !p.items.length;
      pb.onclick = () => playPl(p, 0); r.append(pb);
      list.append(r);
    }
    return box.append(list);
  }
  const bar = el('div', 'pl-bar'), back = el('button', 'btn ghost icon'), t = el('div', 'pl-title');
  back.innerHTML = ICON.back; back.title = back.ariaLabel = 'All playlists'; back.onclick = () => { openPl = null; renderPlaylists() };
  t.append(el('b', '', cur.name), el('span', '', plCount(cur)));
  const play = el('button', 'btn'), ren = el('button', 'btn outline icon'), del = el('button', 'btn outline icon danger-btn');
  play.innerHTML = ICON.play + '<span>Play</span>'; play.disabled = !cur.items.length; play.onclick = () => playPl(cur, 0);
  ren.innerHTML = ICON.pen; ren.title = ren.ariaLabel = 'Rename'; ren.onclick = () => openPlDlg(cur);
  del.innerHTML = ICON.trash; del.title = del.ariaLabel = 'Delete playlist';
  del.onclick = async () => { if (!confirm('Delete “' + cur.name + '”?')) return; playlists = await api('playlists/' + cur.id, 'DELETE'); openPl = null; renderPlaylists(); toast('Playlist deleted') };
  bar.append(back, t, play, ren, del); box.append(bar);
  if (!cur.items.length) return box.append(emptyState(ICON.plist, 'This playlist is empty', 'Use the bookmark button on a song in Music to add it here.', ['Find music', () => go('music')]));
  const list = el('div', 'item-group');
  cur.items.forEach((it, i) => {
    const r = trackRow({...it, artist: it.artist || (it.kind === 'radio' ? 'Live radio' : '')},
      [[ICON.add, 'Add to queue', () => api('queue', 'POST', {items: [it]}).then(() => toast('Added to queue'))],
       [ICON.x, 'Remove from playlist', async () => { playlists = await api(`playlists/${cur.id}/items/${i}`, 'DELETE'); renderPlaylists() }]], i);
    r.classList.remove('now');
    r.querySelector('.go').onclick = () => playPl(cur, i);
    list.append(r);
  });
  box.append(list);
}
const playPl = (p, from) => api('play', 'POST', {playlist: p.id, from}).then(r => r.error ? toast(r.error) : toast('Playing ' + p.name));
function openPlDlg(p) {
  plEdit = p; plForm.reset(); if (p) plForm.name.value = p.name;
  $('#pldlgtitle').textContent = p ? 'Rename playlist' : 'New playlist';
  $('#plsave').textContent = p ? 'Save' : 'Create';
  plDlg.showModal(); plForm.name.focus();
}
$('#plnew').onclick = () => openPlDlg(null);
$('#plcancel').onclick = () => plDlg.close();
plDlg.addEventListener('click', e => { if (e.target === plDlg) plDlg.close() });
plForm.onsubmit = async e => {
  e.preventDefault();
  const name = plForm.name.value.trim(); if (!name) return;
  const r = plEdit ? await api('playlists/' + plEdit.id, 'PUT', {name}) : await api('playlists', 'POST', {name});
  if (!Array.isArray(r)) return toast(r.error || 'Could not save playlist');
  playlists = r; if (!plEdit) openPl = r[r.length - 1].id;
  plDlg.close(); renderPlaylists(); toast(plEdit ? 'Playlist renamed' : 'Playlist created');
};
// choose (or create) a playlist to receive tracks
async function pickPlaylist(items) {
  await loadPlaylists();
  pickForm.reset();
  $('#pickdesc').textContent = items.length === 1 ? items[0].title : items.length + ' tracks';
  const opts = $('#pickopts'); opts.replaceChildren();
  for (const p of playlists) {
    const b = el('button', 'btn outline pick-opt'); b.type = 'button';
    b.append(el('span', '', p.name), el('em', '', plCount(p)));
    b.onclick = async () => { const r = await api(`playlists/${p.id}/items`, 'POST', {items}); if (Array.isArray(r)) { playlists = r; renderPlaylists(); pickDlg.close(); toast('Added to ' + p.name) } else toast(r.error || 'Failed') };
    opts.append(b);
  }
  pickForm.onsubmit = async e => {
    e.preventDefault();
    const name = pickForm.name.value.trim(); if (!name) return;
    const r = await api('playlists', 'POST', {name, items});
    if (Array.isArray(r)) { playlists = r; renderPlaylists(); pickDlg.close(); toast('Saved to ' + name) } else toast(r.error || 'Failed');
  };
  pickDlg.showModal(); (playlists.length ? opts.firstChild : pickForm.name).focus();
}
$('#pickcancel').onclick = () => pickDlg.close();
pickDlg.addEventListener('click', e => { if (e.target === pickDlg) pickDlg.close() });
$('#qsave').onclick = () => pickPlaylist(S.queue.map(({kind, id, title, artist, duration, thumb, url}) => ({kind, id, title, artist, duration, thumb, url})));

// ---- listen on this device (the Pi streams its output to the browser) ----
const listenBox = $('#listen');
const lAudio = new Audio(); lAudio.preload = 'none';
let lWant = false, lRetry = 0;
function lStart() {
  if (!lWant) return;
  lAudio.src = '/api/listen?t=' + Date.now();
  lAudio.play().catch(() => {});
}
function lStop() {
  lWant = false; clearTimeout(lRetry); listenBox.checked = false;
  lAudio.pause(); lAudio.removeAttribute('src'); lAudio.load();
}
listenBox.onchange = () => { if (listenBox.checked) { lWant = true; lStart() } else lStop() };
const lReconnect = () => { if (!lWant) return; clearTimeout(lRetry); lRetry = setTimeout(lStart, 2000) };
lAudio.onerror = lAudio.onended = lAudio.onstalled = lReconnect;

// ---- now playing / transport ----
const ROOM = {male: 'Male', female: 'Female'};
function ago(t) {
  const m = Math.max(0, Math.floor((Date.now() / 1000 - t) / 60));
  return m < 1 ? 'just now' : m < 60 ? m + ' min' : Math.floor(m / 60) + ' h ' + (m % 60) + ' min';
}
const RICON = {
  female: '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="4.5" r="2.5"/><path d="M9 9h6l3 8h-3v5h-2v-5h-2v5H9v-5H6l3-8Z"/></svg>',
  male: '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="4.5" r="2.5"/><path d="M9 9h6a1 1 0 0 1 1 1v6h-2v6h-4v-6H8v-6a1 1 0 0 1 1-1Z"/></svg>'};
const SI = {
  door: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M10 21H2m8-18H7a2 2 0 0 0-2 2v16m9-9h.01"/><path d="M19 21V5a2 2 0 0 0-1.675-1.974l-6.163-1.013A1 1 0 0 0 10 3v18a1 1 0 0 0 1.124.992zm3 0h-3"/></g></svg>',
  clock: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></g></svg>',
  cal: '<svg viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9a9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5m4-1v5l4 2"/></g></svg>',
  ok: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 6L9 17l-5-5"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 6L6 18M6 6l12 12"/></svg>',
  off: '<svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 20h.01M8.5 16.429a5 5 0 0 1 7 0M5 12.859a10 10 0 0 1 5.17-2.69m8.83 2.69a10 10 0 0 0-2.007-1.523M2 8.82a15 15 0 0 1 4.177-2.643M22 8.82a15 15 0 0 0-11.288-3.764M2 2l20 20"/></svg>'};
function renderRooms() {
  const rs = S.bathrooms || [];
  $('#roomlist').innerHTML = rs.map(r => {
    const st = r.occupied == null ? 'unknown' : r.occupied ? 'busy' : 'free';
    const label = {unknown: 'No sensor', busy: 'Occupied', free: 'Available'}[st];
    const door = {unknown: 'Unknown', busy: 'Closed', free: 'Open'}[st];
    const since = r.since ? new Date(r.since * 1000).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'}) : '—';
    const big = {unknown: 'No sensor', busy: 'In use', free: 'Vacant'}[st];
    const row = (ico, k, v) => `<div class="room-row"><dt>${ico}${k}</dt><dd>${v}</dd></div>`;
    return `<article class="room ${st}">
      <header class="room-head"><div class="room-ico">${RICON[r.id] || RICON.male}</div>
        <div class="room-id"><div class="room-name">${ROOM[r.id] || r.id}</div><div class="room-hint">${st === 'busy' ? 'Someone is inside' : st === 'free' ? 'Ready to use' : 'Sensor not connected'}</div></div>
        <span class="room-state">${big}</span></header>
      <dl class="room-list">${row(SI.door, 'Door', door)}${row(SI.cal, 'Since', since)}</dl>
      ${r.stale ? `<div class="room-warn"><svg viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m21.73 18l-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3M12 9v4m0 4h.01"/></svg>No change for a long while. Check the sensor.</div>` : ''}
      </article>`;
  }).join('');
}
setInterval(() => $('#rooms').classList.contains('on') && renderRooms(), 30000);   // refresh the "for N min" text

// tint the player with the cover's dominant colour (saturation-weighted average, clamped dark so white text always reads)
let tintSrc = null;
function tintFrom(src) {
  if (src === tintSrc) return; tintSrc = src;
  const P = $('#player'), reset = () => P.style.removeProperty('--np-tint');
  if (!src) return reset();
  const im = new Image(); im.crossOrigin = 'anonymous';
  im.onerror = reset;
  im.onload = () => {
    if (src !== tintSrc) return;
    try {
      const c = document.createElement('canvas'); c.width = c.height = 16;
      const x = c.getContext('2d', {willReadFrequently: true}); x.drawImage(im, 0, 0, 16, 16);
      const d = x.getImageData(0, 0, 16, 16).data; let r = 0, g = 0, b = 0, w = 0;
      for (let i = 0; i < d.length; i += 4) {
        const mx = Math.max(d[i], d[i + 1], d[i + 2]), mn = Math.min(d[i], d[i + 1], d[i + 2]), sat = (mx - mn) / (mx || 1);
        const wt = .04 + sat * sat * (mx / 255); r += d[i] * wt; g += d[i + 1] * wt; b += d[i + 2] * wt; w += wt;
      }
      r /= w * 255; g /= w * 255; b /= w * 255;
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b), dl = mx - mn; let h = 0;
      if (dl) h = mx === r ? ((g - b) / dl) % 6 : mx === g ? (b - r) / dl + 2 : (r - g) / dl + 4;
      h = Math.round(((h * 60) + 360) % 360);
      const l = (mx + mn) / 2, sat = dl ? dl / (1 - Math.abs(2 * l - 1)) : 0;
      P.style.setProperty('--np-tint', `hsl(${h} ${Math.round(Math.min(sat, .6) * 100)}% 26%)`);
    } catch (e) { reset() }       // tainted canvas (cover served without CORS): keep the neutral tint
  };
  im.src = src;
}

let progLast = 0;
function setProg(f) {                    // scaleX on the compositor; jumps (seek, new track) skip the 0.5s glide
  const jump = f < progLast || (f - progLast) * (S.duration || 1) > 2;
  const i = $('#mprog'); i.style.transitionDuration = jump ? '0s' : ''; i.style.transform = `scaleX(${f})`; progLast = f;
}

function render() {
  renderRooms();
  paintDoors();
  const cur = S.current, live = cur && cur.kind === 'radio', busy = S.playing && !S.paused;
  document.body.classList.toggle('np-idle', !cur);          // desktop: no mini player while nothing is queued
  npResize();
  $$('.np-title').forEach(t => t.textContent = cur ? cur.title : 'Nothing playing');
  const sub = S.error || (!cur ? 'Pick a station or search for music' : S.loading ? 'Loading…' : live ? (S.icy || 'Live radio') : (cur.artist || ''));
  $$('.np-sub').forEach(s => { s.classList.toggle('err', !!S.error); s.textContent = sub });
  $$('.np-art').forEach(a => paintArt(a, cur));
  tintFrom(cur ? thumbOf(cur) : '');
  $$('.pp').forEach(b => b.innerHTML = S.loading ? ICON.load : (busy ? ICON.pause : ICON.play));
  const st = $('#state');
  st.className = 'badge' + (cur && busy && !S.loading ? ' primary-light' : '');
  st.innerHTML = !cur ? 'Idle' : S.loading ? 'Loading' : !busy ? 'Paused' : (EQ + (live ? 'Live' : 'Playing'));
  const nx = S.queue[S.index + 1], un = $('#upnext'); un.hidden = !nx;
  if (nx) { $('#untitle').textContent = nx.title; $('#unsub').textContent = nx.artist || (nx.kind === 'radio' ? 'Live radio' : ''); paintArt($('.un-art'), nx) }
  $('#mute').innerHTML = (+S.volume || 0) === 0 ? ICON.mute : ICON.vol;
  $('#seek').classList.toggle('live', !!live || !cur);
  if (!dragging) { const sr = $('#sr'); sr.max = S.duration || 100; sr.value = S.position || 0; fill(sr); $('#cur').textContent = fmt(S.position) }
  $('#dur').textContent = fmt(S.duration);
  setProg(!live && cur && S.duration ? Math.min(1, (S.position || 0) / S.duration) : 0);
  if (document.activeElement !== $('#vr')) { $('#vr').value = S.volume; fill($('#vr')); $('#vv').textContent = Math.round(S.volume || 0) }
  const sh = $('#shuffle'), rp = $('#repeat'), rmode = S.repeat || 'off';
  sh.classList.toggle('on', !!S.shuffle); sh.setAttribute('aria-pressed', !!S.shuffle); sh.title = 'Shuffle: ' + (S.shuffle ? 'on' : 'off');
  rp.innerHTML = rmode === 'one' ? ICON.repeat1 : ICON.repeat;
  rp.classList.toggle('on', rmode !== 'off'); rp.setAttribute('aria-pressed', rmode !== 'off');
  rp.title = 'Repeat: ' + {off: 'off', all: 'all tracks', one: 'this track'}[rmode];
  document.title = cur ? `${cur.title} · Cytron DJ` : 'Cytron DJ';
  tickBase = {t: performance.now(), pos: S.position || 0};
  renderStations(); renderQueue();
}
setInterval(() => {                      // smooth progress between server events
  if (document.hidden || !S.playing || S.paused || S.loading || dragging) return;
  if (S.duration && S.current && S.current.kind !== 'radio') {
    const pos = tickBase.pos + (performance.now() - tickBase.t) / 1000, sr = $('#sr');
    sr.value = Math.min(pos, S.duration); fill(sr); $('#cur').textContent = fmt(pos);
    setProg(Math.min(1, pos / S.duration));
  }
}, 500);

$$('.pp').forEach(b => b.onclick = e => {
  e.stopPropagation();
  S.playing ? ctl('toggle') : (S.queue.length ? api('play', 'POST', {index: Math.max(S.index, 0)}) : go('radio'));
});
$('#next').onclick = () => ctl('next');
$('#shuffle').onclick = () => ctl('shuffle', {value: !S.shuffle});
$('#repeat').onclick = () => ctl('repeat', {value: {off: 'all', all: 'one', one: 'off'}[S.repeat || 'off']});
$('#prev').onclick = () => ctl('prev');
$('#stop').onclick = () => ctl('stop');
$('#upnext').onclick = () => ctl('next');
let lastVol = 70;
$('#mute').onclick = () => {
  const v = +S.volume || 0;
  if (v > 0) { lastVol = v; ctl('volume', {value: 0}) } else ctl('volume', {value: lastVol || 70});
};
const sr = $('#sr');
sr.oninput = () => { dragging = true; fill(sr); $('#cur').textContent = fmt(sr.value) };
sr.onchange = () => { ctl('seek', {seconds: +sr.value}); dragging = false };
const vr = $('#vr');
let volTimer = 0;
const sendVol = () => { volTimer = 0; ctl('volume', {value: +vr.value}) };
vr.oninput = () => { fill(vr); $('#vv').textContent = vr.value; if (!volTimer) volTimer = setTimeout(sendVol, 80) };   // ~12 updates/s max
vr.onchange = () => { clearTimeout(volTimer); sendVol() };                                                        // always land on the final value

// mobile: mini-player expands into a full sheet
// (Android back / iOS swipe-back closes the sheet instead of leaving the app; swipe down also closes it)
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)'), isSheetLayout = matchMedia('(max-width:820px),(max-height:500px) and (max-width:1000px) and (orientation:landscape)');
function morph(fn) {                    // View Transitions where supported; otherwise the CSS transitions run on the class change
  if (!document.startViewTransition || reduceMotion.matches || !isSheetLayout.matches) return fn();
  const root = document.documentElement; root.classList.add('vt');
  document.startViewTransition(fn).finished.finally(() => root.classList.remove('vt'));
}
const setSheet = open => { const p = $('#player'); p.style.transform = ''; p.style.transition = ''; p.classList.toggle('open', open); $('#scrim').classList.toggle('on', open) };
// ---- desktop: the mini player morphs into the floating card (and back) ----
// The card's width/height/radius are CSS transitions; the cover is flown between its two sizes with the Web Animations API
// using the same duration and easing. Both start in the same frame, so the cover's top-left is exactly
// lerp(mini cover, big cover, e) for the eased progress e, with no per-frame measuring.
const isDesk = matchMedia('(min-width:1001px), (min-width:821px) and (min-height:501px)');
const NP_EASE = 'cubic-bezier(.32,.72,0,1)', NP_MS = 440;
let npAnims = [], npRaf = 0;
function npFullHeight() {                               // content height of the full player, capped to the window
  const f = $('#player .full'), keep = f.style.height; f.style.height = 'auto';
  const h = Math.min(f.offsetHeight, innerHeight - 40); f.style.height = keep; return h;
}
const setOpenHeight = () => $('#player').style.setProperty('--np-open-h', npFullHeight() + 'px');
function npRects(open) {                                // final geometry of a state, measured without animating
  const p = $('#player'), was = p.classList.contains('open');
  p.classList.add('np-measure'); p.classList.toggle('open', open); if (open) setOpenHeight();
  const r = {card: p.getBoundingClientRect(), mini: p.querySelector('.mini .np-art').getBoundingClientRect(),
             big: p.querySelector('.full .np-art.big').getBoundingClientRect()};
  p.classList.toggle('open', was); void p.offsetWidth;  // restore with transitions still off, then re-enable them
  p.classList.remove('np-measure'); void p.offsetWidth;
  return r;
}
function npMorph(open) {
  const p = $('#player');
  npAnims.forEach(a => a.cancel()); npAnims = [];
  if (reduceMotion.matches) { if (open) setOpenHeight(); return setSheet(open) }
  const A = npRects(!open), B = npRects(open), big = p.querySelector('.full .np-art.big');
  const k = {transformOrigin: '0 0'};
  if (open) {                                           // mini cover grows into the big cover
    const ox = B.big.left - B.card.left, oy = B.big.top - B.card.top, s = A.mini.width / B.big.width;
    npAnims.push(big.animate([
      {...k, transform: `translate(${A.mini.left - (A.card.left + ox)}px,${A.mini.top - (A.card.top + oy)}px) scale(${s})`, borderRadius: `${8 / s}px`, opacity: .3},
      {...k, offset: .2, opacity: 1},
      {...k, transform: 'none', borderRadius: '12px', opacity: 1}], {duration: NP_MS, easing: NP_EASE}));
  } else {                                              // big cover shrinks into the mini cover
    const ox = A.big.left - A.card.left, oy = A.big.top - A.card.top, s = B.mini.width / A.big.width;
    npAnims.push(big.animate([
      {...k, transform: 'none', borderRadius: '12px', opacity: 1},
      {...k, offset: .75, opacity: 1},
      {...k, transform: `translate(${B.mini.left - (B.card.left + ox)}px,${B.mini.top - (B.card.top + oy)}px) scale(${s})`, borderRadius: `${8 / s}px`, opacity: 0}], {duration: NP_MS, easing: NP_EASE}));
  }
  setSheet(open);                                       // class change: the card's own CSS transitions start now
}
const applySheet = open => isDesk.matches ? npMorph(open) : morph(() => setSheet(open));
// keep the open card sized to its content (window resized, "Up next" appeared...); the height change is transitioned
const npResize = () => { if (npRaf) return; npRaf = requestAnimationFrame(() => { npRaf = 0; if (isDesk.matches && $('#player').classList.contains('open')) setOpenHeight() }) };
addEventListener('resize', npResize);
let skipPop = false;
const sheet = open => {
  const p = $('#player'), was = p.classList.contains('open');
  if (open !== was) applySheet(open);
  if (open && !was) history.pushState({sheet: 1}, '');
  else if (!open && was && history.state && history.state.sheet) { skipPop = true; history.back() }
};
addEventListener('popstate', () => { if (skipPop) { skipPop = false; return } if ($('#player').classList.contains('open')) applySheet(false) });
$('#scrim').onclick = () => sheet(false);
// swipe down to close: the sheet follows the finger, then closes past 90px or springs back
let touchY = null, sheetDy = 0, sheetDrag = false;
const P = $('#player');
P.addEventListener('touchstart', e => { touchY = e.touches[0].clientY; sheetDy = 0; sheetDrag = false }, {passive: true});
P.addEventListener('touchmove', e => {
  if (touchY == null || !P.classList.contains('open')) return;
  const d = e.touches[0].clientY - touchY;
  if (!sheetDrag) { if (d > 8 && P.scrollTop === 0 && !e.target.closest('input')) sheetDrag = true; else return }
  e.preventDefault(); sheetDy = Math.max(0, d);
  P.style.transition = 'none'; P.style.transform = `translateY(${sheetDy}px)`;
}, {passive: false});
const endSheetDrag = cancel => {
  if (sheetDrag) {
    sheetDrag = false;
    if (!cancel && sheetDy > 90) sheet(false);                 // setSheet clears the offset (the morph starts from where the finger left it)
    else { P.style.transition = ''; P.style.transform = '' }   // spring back
  }
  touchY = null;
};
P.addEventListener('touchend', () => endSheetDrag(false), {passive: true});
P.addEventListener('touchcancel', () => endSheetDrag(true), {passive: true});
$('#mini').onclick = () => sheet(true);
$('#close').onclick = () => sheet(false);
addEventListener('keydown', e => {
  if (e.key === 'Escape') sheet(false);
  if (e.key === '/' && !(e.target.closest && e.target.closest('input,textarea,dialog'))) { e.preventDefault(); go('music'); setTimeout(() => window.musicFocus && window.musicFocus(), 0) }
});

// ---- live updates (SSE, auto-reconnect) ----
function connect() {
  const es = new EventSource('/api/events'); let down = false;     // EventSource reconnects by itself; just tell the user
  es.onmessage = e => { if (down) { down = false; toast('Reconnected') } S = JSON.parse(e.data); render() };
  es.onerror = () => { if (!down) { down = true; toast('Connection lost. Reconnecting…') } };
}
(async () => {
  const st = await api('stations'); if (Array.isArray(st)) stations = st;
  const s0 = await api('state'); if (s0 && Array.isArray(s0.queue)) S = s0;
  render(); connect(); loadPlaylists();
})();
