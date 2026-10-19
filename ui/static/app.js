/* ThoraxLens front end. Vanilla JS, no dependencies. Talks to ui/server.py. */
(() => {
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const f4 = (v) => v.toFixed(4);
const f3 = (v) => v.toFixed(3);
const pct = (v, d = 0) => (v * 100).toFixed(d) + '%';
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};

/* ------------------------------------------------------------------ icons */
const I = {
  scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
  chart: '<path d="M18 20V10M12 20V4M6 20v-6"/>',
  layers: '<path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  keyboard: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M7 15h10"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  minus: '<path d="M5 12h14"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  fit: '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M16 21h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>',
  invert: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor"/>',
  contrast: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor"/>',
  flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.4 1-3 0 2.2 1 3 2.5 3z"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
  grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
  pulse: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  print: '<path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
};
const icon = (n) => `<svg viewBox="0 0 24 24" aria-hidden="true">${I[n] || ''}</svg>`;
function paintIcons(root = document) { $$('i[data-i]', root).forEach((el) => { if (!el.firstChild) el.innerHTML = icon(el.dataset.i); }); }

/* ------------------------------------------------------------------ static knowledge */
const GLOSS = {
  Atelectasis: ['Partial or complete lung collapse with volume loss.', 'Common after surgery; can signal an airway blockage.'],
  Cardiomegaly: ['Enlarged heart shadow (cardiothoracic ratio above about 0.5 on a PA film).', 'AP films magnify the heart, inflating false positives.'],
  Effusion: ['Fluid in the pleural space; blunted costophrenic angle.', 'Heart failure, infection or malignancy; small ones are subtle.'],
  Infiltration: ['A non-specific opacity.', 'Vague, heterogeneous label; the hardest finding here.'],
  Mass: ['Focal opacity larger than 3 cm.', 'Possible lung cancer; needs follow-up imaging.'],
  Nodule: ['Round opacity up to 3 cm.', 'Small nodules lose detail at 320 px.'],
  Pneumonia: ['Infection-related airspace opacity.', 'Looks like consolidation and atelectasis on film.'],
  Pneumothorax: ['Air in the pleural space; a lung edge with no markings beyond it.', 'Can be time-critical; labels were reported to be confounded by chest drains.'],
  Consolidation: ['Airspace filled with fluid, pus or cells.', 'Overlaps with pneumonia labels.'],
  Edema: ['Pulmonary oedema; perihilar haze and septal lines.', 'Often cardiogenic and acute.'],
  Emphysema: ['Hyperinflation and flattened diaphragms.', 'A COPD marker; a strong global pattern.'],
  Fibrosis: ['Lung scarring.', 'Chronic lung disease; low prevalence (1.7%).'],
  'Pleural thickening': ['Thickened pleura.', 'Chronic disease, asbestos exposure; low prevalence.'],
  Hernia: ['Hiatal hernia; air-fluid level behind the heart.', 'Usually incidental; only 86 test positives.'],
};
const PAL = ['#3ee0cf', '#5aa9ff', '#ffb454', '#ff6b7a', '#b794f6', '#4ade80', '#f472b6', '#a3e635'];

/* ------------------------------------------------------------------ state */
const S = {
  cfg: null, M: null, healthOK: false,
  op: store.get('tl.op', 'balanced'), val: store.get('tl.val', 'cal'), byModel: false, flagOnly: false, sortRisk: false,
  res: null, sel: null, order: [], heat: false, reveal: false, busy: false, sample: null,
  view: 'analyze', zoom: { s: 1, x: 0, y: 0 },
  perf: { sort: 'auc', curve: 'roc', curveSel: [7, 1, 3], rel: 'raw', relSel: 8, op: 'balanced', cmSel: 7 },
  train: { t: 'val', sel: [3, 4] },
};

/* ------------------------------------------------------------------ boot */
async function api(path, opt) { const r = await fetch(path, opt); if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch { /* */ } throw new Error(m); } return r; }

async function boot() {
  paintIcons();
  setTheme(new URLSearchParams(location.search).get('theme') || store.get('tl.theme', 'dark'));
  bind();
  route();
  try { S.cfg = await (await api('/api/config')).json(); buildSamples(); } catch (e) { toast('Could not load config: ' + e.message, 'err'); }
  api('/api/metrics').then((r) => r.json()).then((m) => { S.M = m; if (S.view !== 'analyze') renderView(S.view); }).catch(() => {});
  pollHealth();
  renderHistory();
}

async function pollHealth() {
  const el = $('#status'), txt = $('#status-text');
  try {
    const h = await (await api('/api/health')).json();
    if (h.error) { el.className = 'status bad'; txt.textContent = 'model load failed'; el.title = h.error; return; }
    if (!h.ok) { el.className = 'status'; txt.textContent = 'loading models…'; setTimeout(pollHealth, 1500); return; }
    const first = !S.healthOK; S.healthOK = true;
    el.className = 'status ok';
    txt.textContent = h.device === 'cuda' ? `${(h.gpu.name || 'GPU').replace('NVIDIA GeForce ', '').replace(' Laptop GPU', '')} · 3 models ready` : 'CPU · 3 models ready';
    el.title = `${h.models.map((m) => `${m.name} ${m.px}px`).join(', ')} · loaded in ${h.load_seconds}s · torch ${h.torch}`;
    if (first) autostart();
  } catch { el.className = 'status bad'; txt.textContent = 'backend offline'; setTimeout(pollHealth, 4000); }
}

// Deep link: /?sample=s01[&heat=1][&reveal=1][&theme=light] runs a sample on load.
function autostart() {
  const q = new URLSearchParams(location.search), id = q.get('sample');
  if (!id || !S.cfg) return;
  analyze({ sample: id }).then(() => { if (q.get('sel') != null && S.res) select(+q.get('sel')); if (q.get('heat')) setHeat(true); if (q.get('reveal')) $('#reveal').click(); });
}

/* ------------------------------------------------------------------ theme, routing, toasts */
function setTheme(t) {
  document.documentElement.dataset.theme = t; store.set('tl.theme', t);
  $('#btn-theme').innerHTML = `<i data-i="${t === 'dark' ? 'sun' : 'moon'}"></i>`; paintIcons($('#btn-theme'));
  if (S.view !== 'analyze') renderView(S.view);
}
function toast(msg, kind = '') {
  const t = document.createElement('div'); t.className = 'toast ' + kind; t.textContent = msg; $('#toasts').append(t);
  setTimeout(() => t.remove(), kind === 'err' ? 6000 : 2600);
}
const VIEWS = ['analyze', 'performance', 'models', 'validation', 'about'];
function route() { const h = location.hash.slice(1); showView(VIEWS.includes(h) ? h : 'analyze', false); }
function showView(v, push = true) {
  S.view = v;
  $$('.tabs [role=tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.view === v)));
  VIEWS.forEach((n) => { $('#view-' + n).hidden = n !== v; });
  if (push) history.replaceState(null, '', '#' + v);
  renderView(v);
  window.scrollTo({ top: 0 });
}
function renderView(v) {
  if (v === 'analyze') return;
  if (!S.M) { const root = $('#view-' + v); if (!root.dataset.loading) { root.dataset.loading = '1'; } return; }
  ({ performance: renderPerformance, models: renderModels, validation: renderValidation, about: renderAbout })[v]();
}

/* ------------------------------------------------------------------ binding */
function bind() {
  $$('.tabs [role=tab]').forEach((b) => b.addEventListener('click', () => showView(b.dataset.view)));
  window.addEventListener('hashchange', route);
  $('#btn-theme').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
  $('#btn-help').addEventListener('click', () => $('#help').showModal());
  $('#help-close').addEventListener('click', () => $('#help').close());
  $('#btn-history').addEventListener('click', () => toggleDrawer(true));
  $('#drawer-close').addEventListener('click', () => toggleDrawer(false));
  $('#scrim').addEventListener('click', () => toggleDrawer(false));
  $('#history-clear').addEventListener('click', () => { store.set('tl.history', []); renderHistory(); toast('History cleared'); });

  const dz = $('#dropzone'), file = $('#file');
  dz.addEventListener('click', () => file.click());
  dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); file.click(); } });
  $('#dz-browse').addEventListener('click', (e) => { e.stopPropagation(); file.click(); });
  file.addEventListener('change', () => { if (file.files[0]) analyze({ file: file.files[0] }); file.value = ''; });
  ['dragenter', 'dragover'].forEach((ev) => document.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => document.addEventListener(ev, (e) => { e.preventDefault(); if (ev === 'drop' || e.target === document.documentElement || !e.relatedTarget) dz.classList.remove('over'); }));
  document.addEventListener('drop', (e) => { const f = [...(e.dataTransfer?.files || [])].find((x) => x.type.startsWith('image/')); if (f) { showView('analyze'); analyze({ file: f }); } else if (e.dataTransfer?.files.length) toast('That file is not an image. Use PNG or JPEG.', 'err'); });
  document.addEventListener('paste', (e) => { const it = [...(e.clipboardData?.items || [])].find((x) => x.type.startsWith('image/')); if (it) { showView('analyze'); analyze({ file: it.getAsFile() }); } });

  $('#reveal').addEventListener('change', (e) => { S.reveal = e.target.checked; $('#sample-strip').classList.toggle('reveal', S.reveal); renderFindings(); renderSummary(); });
  $('#flag-only').addEventListener('change', (e) => { S.flagOnly = e.target.checked; renderFindings(); });
  $('#sort-risk').addEventListener('change', (e) => { S.sortRisk = e.target.checked; renderFindings(); });
  $('#by-model').addEventListener('change', (e) => { S.byModel = e.target.checked; $('#findings').classList.toggle('by-model', S.byModel); });
  seg('#seg-op', 'op', (v) => { S.op = v; store.set('tl.op', v); renderFindings(); renderSummary(); renderDetail(); });
  seg('#seg-val', 'val', (v) => { S.val = v; store.set('tl.val', v); renderFindings(); renderDetail(); });
  $$('#seg-op button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.op === S.op)));
  $$('#seg-val button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.val === S.val)));

  // viewer tools
  $('#t-zoom-in').addEventListener('click', () => zoomBy(1.25)); $('#t-zoom-out').addEventListener('click', () => zoomBy(0.8));
  $('#t-reset').addEventListener('click', resetView); $('#t-new').addEventListener('click', () => $('#file').click());
  $('#t-invert').addEventListener('click', toggleInvert); $('#t-heat').addEventListener('click', () => setHeat(!S.heat));
  $('#heat-op').addEventListener('input', (e) => { $('#heat').style.opacity = e.target.value / 100; });
  $('#adj-b').addEventListener('input', applyFilter); $('#adj-c').addEventListener('input', applyFilter);
  const stage = $('#stage');
  stage.addEventListener('wheel', (e) => { e.preventDefault(); zoomAt(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY); }, { passive: false });
  let drag = null;
  stage.addEventListener('pointerdown', (e) => { if (e.target.closest('.stage-hud')) return; drag = { x: e.clientX, y: e.clientY, tx: S.zoom.x, ty: S.zoom.y }; stage.setPointerCapture(e.pointerId); stage.classList.add('panning'); });
  stage.addEventListener('pointermove', (e) => { if (!drag) return; S.zoom.x = drag.tx + e.clientX - drag.x; S.zoom.y = drag.ty + e.clientY - drag.y; applyZoom(); });
  const end = () => { drag = null; stage.classList.remove('panning'); };
  stage.addEventListener('pointerup', end); stage.addEventListener('pointercancel', end);
  stage.addEventListener('dblclick', resetView);

  $('#x-json').addEventListener('click', copyJSON); $('#x-csv').addEventListener('click', downloadCSV); $('#x-print').addEventListener('click', printReport);
  $('#findings').addEventListener('click', (e) => { const r = e.target.closest('.f-row'); if (r) select(+r.dataset.i); });
  document.addEventListener('keydown', onKey);

  // tooltips
  const tip = $('#tip');
  document.addEventListener('mousemove', (e) => {
    const t = e.target.closest?.('[data-tip]');
    if (!t) { tip.hidden = true; return; }
    const [a, b] = t.dataset.tip.split('|');
    tip.innerHTML = `<b>${esc(a)}</b>${b ? `<span>${esc(b)}</span>` : ''}`; tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = clamp(e.clientX + 14, 8, innerWidth - w - 8) + 'px'; tip.style.top = clamp(e.clientY + 16, 8, innerHeight - h - 8) + 'px';
  });
}

function seg(sel, key, fn) {
  $(sel).addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    $$('button', $(sel)).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    fn(b.dataset[key] ?? b.dataset[Object.keys(b.dataset)[0]]);
  });
}

function onKey(e) {
  if (e.target.matches('input, textarea, select') && e.target.type !== 'range') return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key;
  if (k === '?') { $('#help').open ? $('#help').close() : $('#help').showModal(); return; }
  if (k >= '1' && k <= '5') { showView(VIEWS[+k - 1]); return; }
  const lk = k.toLowerCase();
  if (lk === 't') setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  if (S.view !== 'analyze') return;
  if (lk === 'u') $('#file').click();
  else if (lk === 'h') { if (!$('#t-heat').disabled) setHeat(!S.heat); }
  else if (lk === 'i') toggleInvert();
  else if (lk === 'r') resetView();
  else if (lk === 'b') { const n = S.op === 'balanced' ? 'sensitive' : 'balanced'; $(`#seg-op [data-op=${n}]`).click(); }
  else if (k === '+' || k === '=') zoomBy(1.25);
  else if (k === '-') zoomBy(0.8);
  else if (k === 'ArrowDown' || k === 'ArrowUp') {
    if (!S.order.length) return; e.preventDefault();
    const idx = S.order.indexOf(S.sel); select(S.order[clamp(idx + (k === 'ArrowDown' ? 1 : -1), 0, S.order.length - 1)]);
  }
}

/* ------------------------------------------------------------------ viewer */
function applyZoom() { $('#stage-img').style.transform = `translate(${S.zoom.x}px,${S.zoom.y}px) scale(${S.zoom.s})`; $('#zoom-read').textContent = Math.round(S.zoom.s * 100) + '%'; }
function resetView() { S.zoom = { s: 1, x: 0, y: 0 }; applyZoom(); }
function zoomAt(f, cx, cy) {
  const r = $('#stage').getBoundingClientRect(), px = cx - r.left, py = cy - r.top, ns = clamp(S.zoom.s * f, 1, 10);
  const k = ns / S.zoom.s; S.zoom.x = px - (px - S.zoom.x) * k; S.zoom.y = py - (py - S.zoom.y) * k; S.zoom.s = ns;
  if (ns === 1) { S.zoom.x = 0; S.zoom.y = 0; } applyZoom();
}
function zoomBy(f) { const r = $('#stage').getBoundingClientRect(); zoomAt(f, r.left + r.width / 2, r.top + r.height / 2); }
function applyFilter() {
  const b = $('#adj-b').value / 100, c = $('#adj-c').value / 100, inv = $('#t-invert').getAttribute('aria-pressed') === 'true';
  $('#xray').style.filter = `brightness(${b}) contrast(${c})${inv ? ' invert(1)' : ''}`;
}
function toggleInvert() { const t = $('#t-invert'); t.setAttribute('aria-pressed', String(t.getAttribute('aria-pressed') !== 'true')); applyFilter(); }
function setHeat(on) {
  if (on && !(S.res && S.res.id)) { toast('The heatmap needs a live analysis (not a restored history entry).'); return; }
  S.heat = on; $('#t-heat').setAttribute('aria-pressed', String(on)); $('#hud-heat').hidden = !on; $('#heat').hidden = !on;
  if (on) loadHeat();
}
function loadHeat() {
  if (!S.heat || !S.res?.id || S.sel == null) return;
  const img = $('#heat'), url = `/api/cam?id=${S.res.id}&cls=${S.sel}`;
  if (img.dataset.src === url) return;
  $('#stage-loading').hidden = false;
  img.onload = () => { $('#stage-loading').hidden = true; img.dataset.src = url; img.style.opacity = $('#heat-op').value / 100; };
  img.onerror = () => { $('#stage-loading').hidden = true; toast('Heatmap failed. Run the analysis again.', 'err'); };
  img.src = url;
}

/* ------------------------------------------------------------------ samples */
function buildSamples() {
  const strip = $('#sample-strip');
  strip.innerHTML = S.cfg.samples.map((s) => `<button class="sample" data-id="${s.id}" aria-label="Sample ${s.id}"><img src="${s.file}" alt="" loading="lazy"><span class="tag">${s.labels.length ? esc(s.labels.join(', ')) : 'No finding'}</span></button>`).join('');
  strip.addEventListener('click', (e) => { const b = e.target.closest('.sample'); if (b) analyze({ sample: b.dataset.id }); });
}

/* ------------------------------------------------------------------ analysis */
const STEPS = ['preprocess', 'coatnet', 'densenet320', 'convnext320', 'blend'];
function setStep(name, state, txt) {
  const li = $(`#stepper [data-step=${name}]`); if (!li) return;
  li.classList.toggle('active', state === 'active'); li.classList.toggle('done', state === 'done');
  if (txt !== undefined) $('em', li).textContent = txt;
}
function resetSteps() { STEPS.forEach((s) => setStep(s, '', '')); }

async function analyze({ file, sample }) {
  if (S.busy) { toast('An analysis is already running.'); return; }
  if (!S.healthOK) { toast('Models are still loading. Try again in a few seconds.'); return; }
  S.busy = true; S.res = null; S.sel = null; S.order = []; S.sample = null;
  const sm = sample ? S.cfg.samples.find((x) => x.id === sample) : null; S.sample = sm;
  $$('.sample').forEach((b) => b.removeAttribute('aria-current'));
  if (sm) $(`.sample[data-id=${sm.id}]`)?.setAttribute('aria-current', 'true');
  const url = sm ? sm.file : URL.createObjectURL(file);
  const name = sm ? `Sample ${sm.id} · ${sm.image}` : (file.name || 'Pasted image');

  // viewer
  $('#dropzone').hidden = true; $('#stage').hidden = false; $('#viewer-tools').hidden = false;
  const img = $('#xray'); img.src = url; img.alt = 'Chest X-ray: ' + name;
  $('#heat').hidden = true; $('#heat').dataset.src = ''; setHeat(false); $('#t-heat').disabled = true;
  resetView(); $('#scan-line').hidden = false; $('#warnings').hidden = true;
  $('#hud-tl').innerHTML = `<span>${esc(name)}</span>` + (sm ? `<span>${sm.age} y · ${sm.sex} · ${sm.view}</span>` : '');

  // results
  $('#results-empty').hidden = true; $('#stepper').hidden = false; ['summary', 'list-tools', 'detail', 'export'].forEach((i) => { $('#' + i).hidden = true; });
  $('#findings').innerHTML = skeleton(); resetSteps(); setStep('preprocess', 'active');

  try {
    const fd = new FormData(); if (sm) fd.append('sample', sm.id); else fd.append('file', file);
    const resp = await api('/api/analyze', { method: 'POST', body: fd });
    const reader = resp.body.getReader(), dec = new TextDecoder(); let buf = '', res = { models: {} };
    for (;;) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true }); let nl;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1); if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.event === 'start') { res.id = ev.id; res.info = ev.info; showInfo(ev.info); }
        else if (ev.event === 'stage') { setStep('preprocess', 'done', ev.ms + ' ms'); setStep('coatnet', 'active'); }
        else if (ev.event === 'model') { res.models[ev.key] = ev; setStep(ev.key, 'done', ev.ms + ' ms'); const nx = STEPS[STEPS.indexOf(ev.key) + 1]; setStep(nx, 'active'); }
        else if (ev.event === 'done') { res.ens = ev.ensemble; res.cal = ev.calibrated; res.ms = ev.total_ms; res.device = ev.device; setStep('blend', 'done', ev.total_ms + ' ms total'); }
      }
    }
    if (!res.ens) throw new Error('The analysis ended early.');
    res.name = name; res.t = Date.now(); S.res = res;
    $('#scan-line').hidden = true; $('#t-heat').disabled = false;
    ['summary', 'list-tools', 'detail', 'export'].forEach((i) => { $('#' + i).hidden = false; });
    $('#findings').classList.toggle('by-model', S.byModel);
    select(topIndex(), true); renderSummary(); saveHistory(img);
  } catch (e) {
    $('#scan-line').hidden = true; resetSteps(); $('#findings').innerHTML = '';
    $('#results-empty').hidden = false; $('#stepper').hidden = true;
    toast(e.message || 'Analysis failed', 'err');
  } finally { S.busy = false; }
}
const skeleton = () => Array.from({ length: 14 }, () => '<li class="f-row" style="opacity:.45"><div class="f-name"><span class="f-flag"></span><span>…</span></div><div class="f-bar"></div><div class="f-val"></div></li>').join('');

function showInfo(info) {
  const meta = $('#img-meta'); meta.hidden = false; meta.textContent = `${info.width}×${info.height} · ${info.mode}`;
  const w = $('#warnings');
  if (info.warnings?.length) { w.hidden = false; w.innerHTML = info.warnings.map((m) => `<div class="warn-item"><i data-i="alert"></i><span>${esc(m)}</span></div>`).join(''); paintIcons(w); }
}

/* ------------------------------------------------------------------ results rendering */
const T = (i) => S.cfg.calibration.thresholds[i][S.op];
const NAMES = () => S.cfg.calibration.names;
function rows() {
  const r = S.res; if (!r) return [];
  return NAMES().map((name, i) => {
    const t = T(i), raw = r.ens[i], cal = r.cal[i], ratio = raw / t.thr_raw;
    return { i, name, raw, cal, t, ratio, flagged: raw >= t.thr_raw, pos: 0.5 + 0.5 * Math.tanh(Math.log2(Math.max(raw, 1e-6) / t.thr_raw) / 2) };
  }).sort((a, b) => (S.sortRisk ? b.cal - a.cal : b.ratio - a.ratio));
}
const topIndex = () => [...rows()].sort((a, b) => b.ratio - a.ratio)[0].i;
const showVal = (r) => (S.val === 'cal' ? (r.cal < 0.01 ? '<1%' : pct(r.cal, r.cal < 0.1 ? 1 : 0)) : f3(r.raw));

function renderSummary() {
  if (!S.res) return;
  const rs = rows(), fl = rs.filter((r) => r.flagged), top = [...rs].sort((a, b) => b.ratio - a.ratio)[0];
  const label = S.op === 'balanced' ? 'balanced threshold' : 'high-sensitivity threshold';
  let truth = '';
  if (S.sample) truth = `<p style="margin-top:6px">NIH label for this sample: <b>${S.reveal ? (S.sample.labels.join(', ') || 'No Finding') : 'hidden (turn on "Reveal labels")'}</b></p>`;
  $('#summary').innerHTML = `<div class="big">${fl.length}<small>of 14 above<br>${label}</small></div>
    <div><p><b>${esc(top.name)}</b> ranks highest relative to its threshold${fl.length ? '' : ', but nothing crosses it'}.</p>
    <p style="margin-top:4px">Flagged: ${fl.length ? fl.map((r) => esc(r.name)).join(', ') : 'none'}. ${S.res.ms} ms on ${S.res.device === 'cuda' ? 'GPU' : 'CPU'}.</p>${truth}</div>`;
}

function renderFindings() {
  if (!S.res) return;
  let rs = rows(); S.order = rs.map((r) => r.i);
  if (S.flagOnly) rs = rs.filter((r) => r.flagged);
  const truth = S.sample && S.reveal ? new Set(S.sample.labels) : null;
  const ul = $('#findings');
  if (!rs.length) { ul.innerHTML = '<li class="fine" style="padding:10px">Nothing above the threshold. Turn off "Flagged only" to see all findings.</li>'; renderSummary(); return; }
  ul.innerHTML = rs.map((r, n) => `<li class="f-row${r.flagged ? ' flagged' : ''}${r.ratio >= 2 ? ' hi' : ''}" role="option" tabindex="-1" data-i="${r.i}" aria-selected="${r.i === S.sel}" style="animation-delay:${n * 18}ms">
      <div class="f-name"><span class="f-flag" aria-hidden="true"></span><span>${esc(r.name)}</span>${truth && truth.has(r.name) ? '<span class="truth" data-tip="NIH label|This finding is labelled positive for the sample.">NIH</span>' : ''}</div>
      <div class="f-bar" data-tip="${esc(r.name)}|${r.flagged ? 'Above' : 'Below'} the ${S.op === 'balanced' ? 'balanced' : 'high-sensitivity'} threshold (raw ${f3(r.raw)} vs ${f3(r.t.thr_raw)}). The tick marks the threshold."><div class="f-fill" data-w="${(r.pos * 100).toFixed(1)}"></div><div class="f-thr" style="left:50%"></div></div>
      <div class="f-val">${showVal(r)}</div>
      <div class="f-models">${['coatnet', 'densenet320', 'convnext320'].map((k) => { const m = S.res.models[k]; return m ? `<div class="mini"><span>${esc(m.name)} ${m.px}</span><div><i style="width:${(m.scores[r.i] * 100).toFixed(1)}%"></i></div><span>${f3(m.scores[r.i])}</span></div>` : ''; }).join('')}</div>
    </li>`).join('');
  requestAnimationFrame(() => requestAnimationFrame(() => $$('.f-fill', ul).forEach((el) => { el.style.width = el.dataset.w + '%'; })));
}

function select(i, first) {
  S.sel = i; renderFindings(); renderDetail(); renderSummary();
  const row = $(`.f-row[data-i="${i}"]`); if (row && !first) row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  loadHeat();
}

function renderDetail() {
  if (!S.res || S.sel == null) return;
  const i = S.sel, r = rows().find((x) => x.i === i), t = r.t, c = S.M?.classes[i];
  const g = GLOSS[r.name] || ['', ''];
  const st = (n, l) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`;
  $('#detail').innerHTML = `<h3>${esc(r.name)} <span class="chip" style="color:${r.flagged ? 'var(--warn)' : 'var(--text-2)'}">${r.flagged ? 'above threshold' : 'below threshold'}</span><span class="chip">raw ${f3(r.raw)} · risk ${r.cal < 0.01 ? '<1%' : pct(r.cal, 1)}</span></h3>
    <p>${esc(g[0])} ${esc(g[1])}</p>
    <div class="stats">${st(pct(t.sens), 'sensitivity at this threshold')}${st(pct(t.spec), 'specificity')}${st(pct(t.ppv, t.ppv < 0.1 ? 1 : 0), 'precision (PPV)')}${st(c ? f3(c.auc) : '…', 'test AUROC')}</div>
    <p class="fine" style="margin:0">Test-set behaviour of this finding at the ${S.op === 'balanced' ? 'balanced' : 'high-sensitivity'} threshold: it flags ${pct(t.flag_rate, 1)} of all images; prevalence is ${c ? pct(c.prevalence, 1) : '…'}. ${S.heat ? 'Heatmap: Grad-CAM on DenseNet121, a sanity check only; it has not been validated against ground-truth regions.' : 'Press <kbd>H</kbd> for a Grad-CAM heatmap of this finding.'}</p>`;
}

/* ------------------------------------------------------------------ history, export */
function thumbOf(img) {
  try { const c = document.createElement('canvas'); c.width = c.height = 160; c.getContext('2d').drawImage(img, 0, 0, 160, 160); return c.toDataURL('image/jpeg', 0.7); } catch { return ''; }
}
function saveHistory(img) {
  const h = store.get('tl.history', []), rs = rows();
  h.unshift({ t: S.res.t, name: S.res.name, thumb: thumbOf(img), ens: S.res.ens, cal: S.res.cal, top: rs.slice(0, 3).map((r) => [r.name, r.flagged]), n: rs.filter((r) => r.flagged).length });
  store.set('tl.history', h.slice(0, 12)); renderHistory();
}
function renderHistory() {
  const h = store.get('tl.history', []), el = $('#history-list');
  el.innerHTML = h.length ? h.map((x, n) => `<button class="h-item" data-n="${n}"><img src="${x.thumb}" alt=""><div><b>${esc(x.name.slice(0, 34))}</b><span>${new Date(x.t).toLocaleString()}</span><span>${x.n} flagged · ${x.top.map((t) => esc(t[0])).join(', ')}</span></div></button>`).join('') : '<p class="fine" style="padding:8px">No analyses yet.</p>';
  $$('.h-item', el).forEach((b) => b.addEventListener('click', () => { restore(h[+b.dataset.n]); toggleDrawer(false); }));
}
function restore(x) {
  showView('analyze'); S.sample = null; S.sel = null;
  S.res = { id: null, ens: x.ens, cal: x.cal, models: {}, ms: 0, device: 'restored', name: x.name, t: x.t };
  $('#dropzone').hidden = true; $('#stage').hidden = false; $('#viewer-tools').hidden = false; $('#xray').src = x.thumb; setHeat(false); $('#t-heat').disabled = true; resetView();
  $('#hud-tl').innerHTML = `<span>${esc(x.name)}</span><span>restored from history (thumbnail only)</span>`;
  $('#results-empty').hidden = true; $('#stepper').hidden = true; ['summary', 'list-tools', 'detail', 'export'].forEach((i) => { $('#' + i).hidden = false; });
  select(topIndex(), true); renderSummary();
}
function toggleDrawer(on) { $('#drawer').classList.toggle('open', on); $('#drawer').setAttribute('aria-hidden', String(!on)); $('#scrim').hidden = !on; }

function exportObj() {
  const rs = rows();
  return { tool: 'ThoraxLens (research prototype, not a medical device)', image: S.res.name, analysed_at: new Date(S.res.t).toISOString(), threshold: S.op,
    findings: rs.map((r) => ({ finding: r.name, raw_score: +r.raw.toFixed(5), calibrated_risk: +r.cal.toFixed(5), threshold_raw: +r.t.thr_raw.toFixed(5), flagged: r.flagged })) };
}
async function copyJSON() { try { await navigator.clipboard.writeText(JSON.stringify(exportObj(), null, 2)); toast('JSON copied', 'ok'); } catch { toast('Clipboard blocked by the browser', 'err'); } }
function downloadCSV() {
  const o = exportObj(), csv = ['finding,raw_score,calibrated_risk,threshold_raw,flagged', ...o.findings.map((f) => [f.finding, f.raw_score, f.calibrated_risk, f.threshold_raw, f.flagged].join(','))].join('\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'thoraxlens_scores.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
function printReport() {
  const rs = rows(); let el = $('.print-report'); if (el) el.remove(); el = document.createElement('div'); el.className = 'print-report';
  const heat = S.heat && S.res.id && $('#heat').dataset.src ? `<img src="${$('#heat').dataset.src}" alt="">` : '';
  el.innerHTML = `<h1>ThoraxLens report</h1><div>${esc(S.res.name)} · ${new Date(S.res.t).toLocaleString()} · ${S.op === 'balanced' ? 'balanced' : 'high-sensitivity'} threshold</div>
    <div class="pr-img"><img src="${$('#xray').src}" alt="">${heat}</div>
    <h2>Finding scores</h2><table><thead><tr><th>Finding</th><th>Raw score</th><th>Calibrated risk</th><th>Threshold</th><th>Flag</th></tr></thead><tbody>
    ${rs.map((r) => `<tr><td>${esc(r.name)}</td><td>${f3(r.raw)}</td><td>${r.cal < 0.01 ? '&lt;1%' : pct(r.cal, 1)}</td><td>${f3(r.t.thr_raw)}</td><td>${r.flagged ? 'above threshold' : ''}</td></tr>`).join('')}</tbody></table>
    <div class="note"><b>Research use only.</b> Not a medical device; not validated for clinical decisions. Scores are model outputs from an ensemble trained on NIH ChestX-ray14 (test mean AUROC 0.8289, one hospital, no external validation). Calibrated risk uses per-finding Platt scaling fitted on a validation set. A radiologist must review every study.</div>`;
  document.body.append(el); window.print();
}

/* ================================================================== charts */
const cssv = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function lineChart({ w = 520, h = 330, pad = { l: 46, r: 12, t: 10, b: 38 }, xd, yd, xt, yt, xl, yl, series, fx = (v) => v, fy = (v) => v, diag }) {
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const X = (v) => pad.l + (v - xd[0]) / (xd[1] - xd[0]) * iw, Y = (v) => pad.t + ih - (v - yd[0]) / (yd[1] - yd[0]) * ih;
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img"><g class="ax">`;
  yt.forEach((t) => { s += `<line x1="${pad.l}" x2="${w - pad.r}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pad.l - 7}" y="${Y(t) + 4}" text-anchor="end">${fy(t)}</text>`; });
  xt.forEach((t) => { s += `<line y1="${pad.t}" y2="${pad.t + ih}" x1="${X(t)}" x2="${X(t)}"/><text x="${X(t)}" y="${h - pad.b + 16}" text-anchor="middle">${fx(t)}</text>`; });
  s += `<line class="axis-line" x1="${pad.l}" x2="${w - pad.r}" y1="${pad.t + ih}" y2="${pad.t + ih}"/><text x="${pad.l + iw / 2}" y="${h - 4}" text-anchor="middle">${xl}</text><text transform="translate(12 ${pad.t + ih / 2}) rotate(-90)" text-anchor="middle">${yl}</text></g>`;
  if (diag) s += `<line x1="${X(xd[0])}" y1="${Y(yd[0])}" x2="${X(xd[1])}" y2="${Y(yd[1])}" style="stroke:var(--muted);stroke-dasharray:4 4" opacity=".6"/>`;
  series.forEach((se) => {
    const pts = se.pts.map(([x, y]) => `${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(' ');
    s += `<polyline points="${pts}" fill="none" stroke="${se.color}" stroke-width="${se.w || 2}" stroke-linejoin="round" stroke-linecap="round" opacity="${se.o ?? 1}" ${se.dash ? `stroke-dasharray="${se.dash}"` : ''}/>`;
    (se.dots || []).forEach(([x, y, tip, r]) => { s += `<circle cx="${X(x)}" cy="${Y(y)}" r="${r || 4}" fill="${se.color}" data-tip="${esc(tip || '')}"/>`; });
  });
  return s + '</svg>';
}

function renderPerformance() {
  const M = S.M, P = S.perf;
  $('#kpis').innerHTML = `
    <div class="kpi accent"><span>Mean test AUROC</span><b>${f4(M.bootstrap.final[0])}</b><small>95% CI ${f4(M.bootstrap.final[1])} to ${f4(M.bootstrap.final[2])}</small></div>
    <div class="kpi"><span>Gain over baseline</span><b>+${f4(M.bootstrap.paired[0].diff)}</b><small>95% CI +${f4(M.bootstrap.paired[0].ci[0])} to +${f4(M.bootstrap.paired[0].ci[1])}</small></div>
    <div class="kpi"><span>Mean average precision</span><b>${f3(M.ap_mean)}</b><small>prevalence-limited for rare findings</small></div>
    <div class="kpi"><span>Calibration error (ECE)</span><b>${f3(M.calibration.ece_raw)} → ${f3(M.calibration.ece_cal)}</b><small>raw → after Platt scaling</small></div>
    <div class="kpi"><span>Test set</span><b>${M.dataset.images.test.toLocaleString()}</b><small>${M.dataset.patients.test.toLocaleString()} patients, never trained on</small></div>`;
  forest(); curves(); reliability(); opTable(); subgroups(); confusion();
  if (!renderPerformance.bound) {
    renderPerformance.bound = true;
    seg('#seg-sort', 'sort', (v) => { P.sort = v; forest(); }); seg('#seg-curve', 'curve', (v) => { P.curve = v; curves(); });
    seg('#seg-rel', 'rel', (v) => { P.rel = v; reliability(); }); seg('#seg-opt', 'op', (v) => { P.op = v; opTable(); confusion(); });
  }
}

function forest() {
  const M = S.M, cs = [...M.classes].sort((a, b) => (S.perf.sort === 'auc' ? b.auc - a.auc : b.prevalence - a.prevalence));
  const w = 560, rh = 25, top = 34, left = 130, h = top + cs.length * rh + 44, x0 = 0.66, x1 = 0.97, X = (v) => left + (v - x0) / (x1 - x0) * (w - left - 56);
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Per-finding test AUROC with 95% intervals"><g class="ax">`;
  [0.7, 0.75, 0.8, 0.85, 0.9, 0.95].forEach((t) => { s += `<line x1="${X(t)}" x2="${X(t)}" y1="${top - 8}" y2="${top + cs.length * rh}"/><text x="${X(t)}" y="${top + cs.length * rh + 16}" text-anchor="middle">${t.toFixed(2)}</text>`; });
  s += `<line class="axis-line" x1="${X(x0)}" x2="${X(x1)}" y1="${top + cs.length * rh}" y2="${top + cs.length * rh}"/><text x="${X(0.815)}" y="${h - 6}" text-anchor="middle">Test AUROC, 95% bootstrap interval over patients</text></g>`;
  s += `<line x1="${X(M.mean_auc)}" x2="${X(M.mean_auc)}" y1="${top - 8}" y2="${top + cs.length * rh}" style="stroke:var(--accent-2);stroke-dasharray:4 4"/><text x="${X(M.mean_auc)}" y="${top - 14}" text-anchor="middle" style="fill:var(--accent-2);font-size:11px">mean ${f3(M.mean_auc)}</text>`;
  cs.forEach((c, i) => {
    const y = top + i * rh + rh / 2, hi = c.auc >= 0.9;
    s += `<g data-tip="${esc(c.name)}|AUROC ${f3(c.auc)} (95% CI ${f3(c.ci[0])} to ${f3(c.ci[1])}) · ${c.n_pos.toLocaleString()} positives · prevalence ${pct(c.prevalence, 1)}">
      <text class="c-label" x="${left - 10}" y="${y + 4}" text-anchor="end">${esc(c.name)}</text>
      <line x1="${X(c.ci[0])}" x2="${X(c.ci[1])}" y1="${y}" y2="${y}" stroke-width="3" stroke-linecap="round" style="stroke:${hi ? 'var(--accent)' : 'var(--muted-fill)'}"/>
      <circle cx="${X(c.auc)}" cy="${y}" r="5.5" style="fill:${hi ? 'var(--accent)' : 'var(--text-2)'}"/>
      <text class="c-val" x="${w - 46}" y="${y + 4}">${f3(c.auc)}</text></g>`;
  });
  $('#ch-forest').innerHTML = s + '</svg>';
}

function chipRow(el, items, sel, multi, fn) {
  el.innerHTML = items.map((n, i) => `<button data-i="${i}" aria-pressed="${multi ? sel.includes(i) : sel === i}">${esc(n)}</button>`).join('');
  el.onclick = (e) => { const b = e.target.closest('button'); if (b) fn(+b.dataset.i); };
}
function curves() {
  const P = S.perf, cs = S.M.classes, el = $('#chips-curve');
  chipRow(el, cs.map((c) => c.name), P.curveSel, true, (i) => { P.curveSel = P.curveSel.includes(i) ? P.curveSel.filter((x) => x !== i) : [...P.curveSel, i].slice(-6); curves(); });
  const roc = P.curve === 'roc', series = [];
  cs.forEach((c, i) => { if (!P.curveSel.includes(i)) series.push({ pts: roc ? c.roc.fpr.map((x, k) => [x, c.roc.tpr[k]]) : c.pr.recall.map((x, k) => [x, c.pr.precision[k]]), color: cssv('--muted'), o: 0.22, w: 1 }); });
  P.curveSel.forEach((i, k) => { const c = cs[i], col = PAL[k % PAL.length]; series.push({ pts: roc ? c.roc.fpr.map((x, j) => [x, c.roc.tpr[j]]) : c.pr.recall.map((x, j) => [x, c.pr.precision[j]]), color: col, w: 2.4 }); });
  $$('button', el).forEach((b) => { const k = P.curveSel.indexOf(+b.dataset.i); if (k >= 0) b.style.cssText = `border-color:${PAL[k % PAL.length]};color:${PAL[k % PAL.length]}`; else b.style.cssText = ''; });
  const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1], f = (v) => v.toFixed(1);
  $('#ch-curve').innerHTML = lineChart({ xd: [0, 1], yd: [0, 1], xt: ticks, yt: ticks, fx: f, fy: f, xl: roc ? 'False positive rate' : 'Recall (sensitivity)', yl: roc ? 'True positive rate' : 'Precision', series, diag: roc }).replace('</svg>', P.curveSel.map((i, k) => `<g transform="translate(${roc ? 300 : 300} ${236 + k * 15})"><rect x="0" y="-8" width="10" height="3" fill="${PAL[k % PAL.length]}"/><text x="16" y="-3" class="c-val">${esc(cs[i].name)} · ${roc ? 'AUC ' + f3(cs[i].auc) : 'AP ' + f3(cs[i].ap)}</text></g>`).join('') + '</svg>');
}

function reliability() {
  const P = S.perf, M = S.M, el = $('#chips-rel');
  chipRow(el, M.classes.map((c) => c.name), P.relSel, false, (i) => { P.relSel = i; reliability(); });
  const r = M.reliability[P.relSel][P.rel], N = r.reduce((s, b) => s + b.n, 0), pts = r.filter((b) => b.n > 0);
  const e = pts.reduce((s, b) => s + b.n / N * Math.abs(b.obs - b.pred), 0), col = P.rel === 'raw' ? PAL[3] : PAL[0];
  const ser = [{ pts: pts.map((b) => [b.pred, b.obs]), color: col, w: 2.4, dots: pts.map((b) => [b.pred, b.obs, `${pct(b.pred, 0)} predicted|observed ${pct(b.obs, 1)} · ${b.n.toLocaleString()} images`, 3 + Math.sqrt(b.n / N) * 9]) }];
  const t = [0, 0.2, 0.4, 0.6, 0.8, 1];
  $('#ch-rel').innerHTML = lineChart({ xd: [0, 1], yd: [0, 1], xt: t, yt: t, fx: (v) => v.toFixed(1), fy: (v) => v.toFixed(1), xl: 'Predicted score', yl: 'Observed frequency', series: ser, diag: true });
  $('#rel-note').textContent = `${M.classes[P.relSel].name}: calibration error ${f3(e)} on test. Dot size shows how many images fall in the bin. ${P.rel === 'raw' ? 'Raw scores sit far above the diagonal because training weighted positives up to 50×.' : 'After per-finding Platt scaling fitted on validation, points follow the diagonal.'}`;
}

function opTable() {
  const M = S.M, k = S.perf.op;
  $('#op-table').innerHTML = `<table><thead><tr><th>Finding</th><th>Risk thr.</th><th>Sens.</th><th>Spec.</th><th>PPV</th><th>NPV</th><th>Flag rate</th></tr></thead><tbody>${M.classes.map((c, i) => { const t = M.thresholds[i][k]; return `<tr><td>${esc(c.name)}</td><td>${t.thr_cal < 0.01 ? '<1%' : pct(t.thr_cal, 1)}</td><td>${pct(t.sens)}</td><td>${pct(t.spec)}</td><td>${pct(t.ppv, 1)}</td><td>${pct(t.npv, 1)}</td><td>${pct(t.flag_rate, 1)}</td></tr>`; }).join('')}</tbody></table>`;
}

function subgroups() {
  const M = S.M, g = M.subgroups, w = 520, rh = 30, top = 18, left = 112, x0 = 0.77, x1 = 0.84, h = top + g.length * rh + 40, X = (v) => left + (v - x0) / (x1 - x0) * (w - left - 70);
  const nm = { 'sex=M': 'Male', 'sex=F': 'Female', 'view=PA': 'PA view', 'view=AP': 'AP view', 'age<40': 'Age under 40', 'age 40-64': 'Age 40–64', 'age>=65': 'Age 65+' };
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Mean test AUROC by subgroup"><g class="ax">`;
  [0.78, 0.80, 0.82, 0.84].forEach((t) => { s += `<line x1="${X(t)}" x2="${X(t)}" y1="${top - 6}" y2="${top + g.length * rh}"/><text x="${X(t)}" y="${top + g.length * rh + 16}" text-anchor="middle">${t.toFixed(2)}</text>`; });
  s += `<line class="axis-line" x1="${X(x0)}" x2="${X(x1)}" y1="${top + g.length * rh}" y2="${top + g.length * rh}"/><text x="${X((x0 + x1) / 2)}" y="${h - 4}" text-anchor="middle">Mean AUROC over 14 findings (axis starts at 0.77)</text></g>`;
  s += `<line x1="${X(M.mean_auc)}" x2="${X(M.mean_auc)}" y1="${top - 6}" y2="${top + g.length * rh}" style="stroke:var(--accent-2);stroke-dasharray:4 4"/>`;
  g.forEach((r, i) => { const y = top + i * rh + rh / 2; s += `<g data-tip="${esc(nm[r.group] || r.group)}|mean AUROC ${f4(r.auc)} · ${r.n.toLocaleString()} images"><text class="c-label" x="${left - 10}" y="${y + 4}" text-anchor="end">${esc(nm[r.group] || r.group)}</text><line x1="${X(x0)}" x2="${X(r.auc)}" y1="${y}" y2="${y}" style="stroke:var(--border-2)" stroke-width="2"/><circle cx="${X(r.auc)}" cy="${y}" r="6" style="fill:${r.auc < 0.8 ? 'var(--warn)' : 'var(--accent)'}"/><text class="c-val" x="${X(r.auc) + 12}" y="${y + 4}">${f3(r.auc)}</text></g>`; });
  $('#ch-sub').innerHTML = s + '</svg>';
}

function confusion() {
  const P = S.perf, M = S.M, el = $('#chips-cm');
  chipRow(el, M.classes.map((c) => c.name), P.cmSel, false, (i) => { P.cmSel = i; confusion(); });
  const t = M.thresholds[P.cmSel][P.op], N = t.tp + t.fp + t.fn + t.tn, cell = (v, l, cls) => `<div style="padding:14px 10px;border-radius:12px;border:1px solid var(--border);background:${cls};text-align:center"><b style="font-size:20px;font-variant-numeric:tabular-nums">${v.toLocaleString()}</b><div style="font-size:11.5px;color:var(--text-2)">${l}</div><div style="font-size:11px;color:var(--muted)">${pct(v / N, 1)} of images</div></div>`;
  $('#ch-cm').innerHTML = `<div style="display:grid;grid-template-columns:auto 1fr 1fr;gap:8px;align-items:center;font-size:12px;color:var(--muted)">
    <span></span><span style="text-align:center">Flagged</span><span style="text-align:center">Not flagged</span>
    <span style="writing-mode:vertical-rl;transform:rotate(180deg)">Finding present</span>${cell(t.tp, 'true positives', 'color-mix(in srgb,var(--good) 14%,transparent)')}${cell(t.fn, 'missed (false negatives)', 'color-mix(in srgb,var(--crit) 12%,transparent)')}
    <span style="writing-mode:vertical-rl;transform:rotate(180deg)">Absent</span>${cell(t.fp, 'false alarms', 'color-mix(in srgb,var(--warn) 12%,transparent)')}${cell(t.tn, 'true negatives', 'var(--panel-2)')}</div>
    <p class="fine">${esc(M.classes[P.cmSel].name)}: sensitivity ${pct(t.sens)}, specificity ${pct(t.spec)}, precision ${pct(t.ppv, 1)} on the test set.</p>`;
}

function renderModels() {
  const M = S.M, tr = S.train;
  $('#model-cards').innerHTML = M.models.map((m) => `<div class="mcard ${m.weight > 0 ? 'on' : 'off'}"><span class="badge ${m.weight > 0 ? 'on' : 'off'}">${m.weight > 0 ? 'IN ENSEMBLE' : 'RETIRED'}</span><h3>${esc(m.name)}</h3><div class="fam">${esc(m.family)} · ${m.px} px</div>
    <div class="row"><span>TTA (picked on val)</span><b>${m.tta}</b></div><div class="row"><span>Validation AUROC</span><b>${f4(m.val)}</b></div><div class="row"><span>Test AUROC</span><b>${f4(m.test)}</b></div>
    <div class="row"><span>Ensemble weight</span><b>${m.weight.toFixed(2)}</b></div><div class="wbar"><i style="width:${m.weight * 100}%"></i></div></div>`).join('');
  // ablation (step plot)
  const a = M.ablation, w = 520, h = 250, left = 40, x0 = 0.8195, x1 = 0.8305, Y = (v) => 24 + (x1 - v) / (x1 - x0) * 170, X = (i) => left + 40 + i * ((w - left - 80) / (a.length - 1));
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Test AUROC by ensemble step"><g class="ax">`;
  [0.82, 0.824, 0.828].forEach((t) => { s += `<line x1="${left}" x2="${w - 10}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${left - 6}" y="${Y(t) + 4}" text-anchor="end">${t.toFixed(3)}</text>`; });
  s += '</g>' + `<polyline fill="none" stroke-width="2.5" style="stroke:var(--accent)" points="${a.map((d, i) => `${X(i)},${Y(d.test)}`).join(' ')}"/>`;
  a.forEach((d, i) => { s += `<g data-tip="${esc(d.step)}|${esc(d.detail)} · test AUROC ${f4(d.test)}"><circle cx="${X(i)}" cy="${Y(d.test)}" r="6" style="fill:var(--accent)"/><text class="c-strong" x="${X(i)}" y="${Y(d.test) - 14}" text-anchor="middle" style="font-size:12px">${f4(d.test)}</text><text class="c-label" x="${X(i)}" y="214" text-anchor="middle" style="font-size:11px">${esc(d.step.split(' ').slice(0, 2).join(' '))}</text><text class="c-val" x="${X(i)}" y="228" text-anchor="middle" style="font-size:10.5px">${esc(d.step.split(' ').slice(2).join(' '))}</text></g>`; });
  $('#ch-ablation').innerHTML = s + '</svg>';
  // training curves
  const keys = Object.keys(M.training); chipRow($('#chips-train'), keys, tr.sel, true, (i) => { tr.sel = tr.sel.includes(i) ? tr.sel.filter((x) => x !== i) : [...tr.sel, i]; renderModels(); });
  $$('#chips-train button').forEach((b) => { const k = tr.sel.indexOf(+b.dataset.i); b.style.cssText = k >= 0 ? `border-color:${PAL[k % 8]};color:${PAL[k % 8]}` : ''; });
  const isV = tr.t === 'val', ser = tr.sel.map((i, k) => ({ color: PAL[k % 8], pts: M.training[keys[i]].map((r) => [r.epoch, isV ? r.val : r.loss]), dots: M.training[keys[i]].map((r) => [r.epoch, isV ? r.val : r.loss, `${keys[i]}|epoch ${r.epoch} · ${isV ? 'validation AUROC ' + f4(r.val) : 'train loss ' + r.loss.toFixed(3)} · ${Math.round(r.sec / 60)} min`, 3.5]) }));
  $('#ch-train').innerHTML = lineChart({ xd: [0.8, 5.2], yd: isV ? [0.76, 0.86] : [0.55, 1.05], xt: [1, 2, 3, 4, 5], yt: isV ? [0.78, 0.8, 0.82, 0.84, 0.86] : [0.6, 0.7, 0.8, 0.9, 1.0], fy: (v) => v.toFixed(isV ? 2 : 1), xl: 'Epoch', yl: isV ? 'Validation mean AUROC (EMA weights at 320 px)' : 'Training loss (weighted BCE)', series: ser })
    .replace('</svg>', ser.map((se, k) => `<g transform="translate(${isV ? 320 : 320} ${isV ? 258 - (ser.length - k) * 14 : 36 + k * 14})"><rect x="0" y="-8" width="10" height="3" fill="${se.color}"/><text x="16" y="-3" class="c-val">${esc(keys[tr.sel[k]])}</text></g>`).join('') + '</svg>');
  if (!renderModels.bound) { renderModels.bound = true; seg('#seg-train', 't', (v) => { S.train.t = v; renderModels(); }); }
  // seed repeat
  const sd = M.seed, items = [['DenseNet121 320', 'densenet320'], ['ConvNeXt-Tiny 320', 'convnext320'], ['Ensemble', 'ensemble']], sw = 520, sx0 = 0.815, sx1 = 0.832, SX = (v) => 150 + (v - sx0) / (sx1 - sx0) * (sw - 190);
  let q = `<svg viewBox="0 0 ${sw} 190" role="img" aria-label="Test AUROC for two random seeds"><g class="ax">`;
  [0.82, 0.824, 0.828, 0.832].forEach((t) => { q += `<line x1="${SX(t)}" x2="${SX(t)}" y1="14" y2="${14 + items.length * 44}"/><text x="${SX(t)}" y="${14 + items.length * 44 + 16}" text-anchor="middle">${t.toFixed(3)}</text>`; });
  q += '</g>';
  items.forEach(([l, k], i) => { const y = 36 + i * 44, a1 = sd.seed42[k], a2 = sd.seed7[k]; q += `<text class="c-label" x="138" y="${y + 4}" text-anchor="end">${l}</text><line x1="${SX(a2)}" x2="${SX(a1)}" y1="${y}" y2="${y}" style="stroke:var(--border-2)" stroke-width="3"/><circle cx="${SX(a1)}" cy="${y}" r="6" style="fill:var(--accent)" data-tip="${l}, seed 42|test AUROC ${f4(a1)}"/><circle cx="${SX(a2)}" cy="${y}" r="6" style="fill:var(--accent-2)" data-tip="${l}, seed 7|test AUROC ${f4(a2)}"/><text class="c-val" x="${SX(Math.max(a1, a2)) + 12}" y="${y + 4}">Δ ${(a1 - a2).toFixed(4)}</text>`; });
  q += `<g transform="translate(150 ${14 + items.length * 44 + 36})"><circle cx="5" cy="-4" r="5" style="fill:var(--accent)"/><text x="16" y="0" class="c-val">seed 42 (original)</text><circle cx="140" cy="-4" r="5" style="fill:var(--accent-2)"/><text x="151" y="0" class="c-val">seed 7 (repeat)</text></g>`;
  $('#ch-seed').innerHTML = q + '</svg>';
}

function renderValidation() {
  const M = S.M, P = M.bootstrap.paired;
  const items = [
    ['Split integrity', 'Zero patient overlap between train, validation and test; the test set equals the official 25,596-image NIH list; no duplicate image IDs.'],
    ['Confidence interval', `1000 bootstrap resamples of 2,797 test patients: ${f4(M.bootstrap.final[0])} (${f4(M.bootstrap.final[1])} to ${f4(M.bootstrap.final[2])}).`],
    ['Paired gain', `+${f4(P[0].diff)} over the original baseline (+${f4(P[0].ci[0])} to +${f4(P[0].ci[1])}); the final ensemble was better in 100% of resamples.`],
    ['Weight stability', 'Weights refitted on 30 resamples of the validation set: test AUROC stayed between 0.8281 and 0.8293.'],
    ['Seed repeat', `The 320 px models retrained with seed 7 give an ensemble test AUROC of ${f4(M.seed.seed7.ensemble)} (original ${f4(M.seed.seed42.ensemble)}).`],
    ['Validation vs test', 'Final 0.8610 vs 0.8289. Every model drops by about 0.03 and the model ranking is identical on both splits.'],
    ['Inference path', 'predict.py on 64 random test PNGs matched the cached ensemble to within 0.00007 with identical class rankings.'],
  ];
  $('#checks').innerHTML = items.map(([b, t]) => `<li><span class="ck">${icon('check')}</span><div><b>${esc(b)}</b><span>${esc(t)}</span></div></li>`).join('');
  const w = 520, rh = 38, left = 190, x1 = 0.012, X = (v) => left + v / x1 * (w - left - 60), h = 20 + P.length * rh + 40;
  let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Gain of the final ensemble over other systems"><g class="ax">`;
  [0, 0.004, 0.008, 0.012].forEach((t) => { s += `<line x1="${X(t)}" x2="${X(t)}" y1="8" y2="${14 + P.length * rh}"/><text x="${X(t)}" y="${14 + P.length * rh + 16}" text-anchor="middle">${t === 0 ? '0' : '+' + t.toFixed(3)}</text>`; });
  s += `<text x="${X(0.006)}" y="${h - 4}" text-anchor="middle">Mean AUROC gain, 95% paired bootstrap interval</text></g>`;
  P.forEach((p, i) => { const y = 30 + i * rh; s += `<g data-tip="${esc(p.vs)}|+${f4(p.diff)} (95% CI +${f4(p.ci[0])} to +${f4(p.ci[1])})"><text class="c-label" x="${left - 12}" y="${y + 4}" text-anchor="end">vs ${esc(p.vs)}</text><line x1="${X(p.ci[0])}" x2="${X(p.ci[1])}" y1="${y}" y2="${y}" stroke-width="3" stroke-linecap="round" style="stroke:var(--accent)"/><circle cx="${X(p.diff)}" cy="${y}" r="5.5" style="fill:var(--accent)"/><text class="c-val" x="${X(p.ci[1]) + 10}" y="${y + 4}">+${f4(p.diff)}</text></g>`; });
  $('#ch-paired').innerHTML = s + '</svg>';
}

function renderAbout() {
  const M = S.M, d = M.dataset, tot = d.images.train + d.images.val + d.images.test, w = 520;
  const seg3 = [['train', 'Train', 'var(--accent)'], ['val', 'Validation', 'var(--accent-2)'], ['test', 'Test', 'var(--warn)']];
  let x = 0, s = `<svg viewBox="0 0 ${w} 96" role="img" aria-label="Images per split"><text class="c-label c-strong" x="0" y="14">${tot.toLocaleString()} images, split by patient</text>`;
  seg3.forEach(([k, l, c]) => { const ww = d.images[k] / tot * w; s += `<g data-tip="${l}|${d.images[k].toLocaleString()} images · ${d.patients[k].toLocaleString()} patients"><rect x="${x}" y="26" width="${Math.max(ww - 2, 1)}" height="26" rx="6" style="fill:${c}" opacity=".85"/><text class="c-val" x="${x + 2}" y="70">${l}</text><text class="c-val" x="${x + 2}" y="86">${d.images[k].toLocaleString()}</text></g>`; x += ww; });
  $('#ch-split').innerHTML = s + '</svg>';
  const ah = d.test_age_hist, mx = Math.max(...ah), bw = (w - 20) / ah.length;
  let a = `<svg viewBox="0 0 ${w} 130" role="img" aria-label="Test set age distribution"><text class="c-label c-strong" x="0" y="14" style="margin-top:12px">Test set age (years)</text>`;
  ah.forEach((v, i) => { const hh = v / mx * 70; a += `<g data-tip="Age ${i * 10}–${i * 10 + 9}|${v.toLocaleString()} images"><rect x="${10 + i * bw}" y="${100 - hh}" width="${bw - 6}" height="${hh}" rx="4" style="fill:var(--accent)" opacity=".75"/><text class="c-val" x="${10 + i * bw + (bw - 6) / 2}" y="116" text-anchor="middle">${i * 10}</text></g>`; });
  const sx = d.test_sex, vw = d.test_view; a += `<text class="c-val" x="${w}" y="14" text-anchor="end">${Object.entries(sx).map(([k, v]) => `${k} ${pct(v / d.images.test)}`).join(' · ')} · ${Object.entries(vw).map(([k, v]) => `${k} ${pct(v / d.images.test)}`).join(' · ')}</text>`;
  $('#ch-demo').innerHTML = a + '</svg>';
  $('#pipeline').innerHTML = `<div style="display:grid;gap:10px">${[['1', 'Preprocess', 'Grayscale, bilinear resize to 224 px and 320 px, normalise on the GPU.'], ['2', 'Three networks', 'CoAtNet-0 (224), DenseNet121 (320), ConvNeXt-Tiny (320); each averages a few zoomed or flipped views (TTA).'], ['3', 'Weighted blend', '0.05 / 0.30 / 0.65, fitted on the validation set only.'], ['4', 'Recalibrate and threshold', 'Per-finding Platt scaling turns scores into risk estimates; thresholds from validation set the flag.'], ['5', 'Inspect', 'Grad-CAM from DenseNet121 shows where the network looked; a sanity check only.']].map(([n, t, d2]) => `<div style="display:grid;grid-template-columns:30px 1fr;gap:12px;align-items:start"><span style="display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--accent-soft);color:var(--accent);font-weight:700">${n}</span><div><b>${t}</b><div style="color:var(--text-2);font-size:12.5px">${d2}</div></div></div>`).join('')}</div>`;
  $('#glossary').innerHTML = M.classes.map((c) => `<div class="g-item"><b>${esc(c.name)}<em>${f3(c.auc)}</em></b><span>${esc((GLOSS[c.name] || [''])[0])}</span><span style="color:var(--muted)">${esc((GLOSS[c.name] || ['', ''])[1])}</span></div>`).join('');
}

boot();
})();
