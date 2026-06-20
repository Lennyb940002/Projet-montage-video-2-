const drop = document.getElementById('drop');
const fileLbl = document.getElementById('file');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const preview = document.getElementById('preview');
const genBtn = document.getElementById('genBtn');
const expBtn = document.getElementById('expBtn');
const styleSel = document.getElementById('style');
const boostChk = document.getElementById('boost');
const captionBox = document.getElementById('caption');
const tabTr = document.getElementById('tabTr');
const tabDesc = document.getElementById('tabDesc');
const paneTr = document.getElementById('paneTr');
const paneDesc = document.getElementById('paneDesc');
const regenBtn = document.getElementById('regenBtn');
const copyBtn = document.getElementById('copyBtn');

function showTab(which) {
  const desc = which === 'desc';
  paneDesc.style.display = desc ? 'flex' : 'none';
  paneTr.style.display = desc ? 'none' : 'flex';
  tabDesc.classList.toggle('active', desc);
  tabTr.classList.toggle('active', !desc);
}
tabTr.addEventListener('click', () => showTab('tr'));
tabDesc.addEventListener('click', () => showTab('desc'));

regenBtn.addEventListener('click', async () => {
  try {
    const c = await window.api.caption(transcript.value);
    if (c.error) throw new Error(c.error);
    captionBox.value = c.full;
  } catch (e) { captionBox.value = 'Erreur : ' + (e.message || e); }
});
copyBtn.addEventListener('click', async () => {
  await navigator.clipboard.writeText(captionBox.value);
  copyBtn.textContent = '✓ Copié';
  setTimeout(() => { copyBtn.textContent = '📋 Copier'; }, 1200);
});

// ---- Réglages Instagram + publication ----
const setBtn = document.getElementById('setBtn');
const igBtn = document.getElementById('igBtn');
const setModal = document.getElementById('setModal');
const setToken = document.getElementById('setToken');
const setIgId = document.getElementById('setIgId');
const setSave = document.getElementById('setSave');
const setClose = document.getElementById('setClose');
const setMsg = document.getElementById('setMsg');
let lastExport = null;

setBtn.addEventListener('click', async () => {
  const s = await window.api.getSettings();
  setIgId.value = s.ig_user_id || '';
  setToken.value = '';
  setToken.placeholder = s.has_token ? '•••• (déjà enregistré)' : 'EAAB...';
  setMsg.textContent = '';
  setModal.style.display = 'flex';
});
setClose.addEventListener('click', () => { setModal.style.display = 'none'; });
setSave.addEventListener('click', async () => {
  await window.api.saveSettings(setToken.value, setIgId.value);
  setMsg.textContent = 'Enregistré ✓';
});

igBtn.addEventListener('click', async () => {
  if (!lastExport) { setStatus('Exporte la vidéo d\'abord.'); return; }
  setStatus('Publication Instagram… (tunnel → encodage → publication)');
  try {
    const r = await window.api.publishInstagram(lastExport, captionBox.value);
    if (r.error) throw new Error(r.error);
    setStatus('Publié sur Instagram ✅ (id ' + r.id + ')');
  } catch (e) { setStatus('Erreur Instagram : ' + (e.message || e)); }
});
const menu = document.getElementById('menu');
const canvas = document.getElementById('wave');
const player = document.getElementById('player');
const playBtn = document.getElementById('playBtn');
const timeLbl = document.getElementById('time');
const selPlay = document.getElementById('selPlay');
const selDel = document.getElementById('selDel');
const selClear = document.getElementById('selClear');

const state = { cleanPath: null, duration: 0, words: [], retakes: [], lowconf: [], peaks: [], sel: null, pauses: [], inserts: [] };
let regions = [];
let drag = null;
let playingSel = false;
function setStatus(m) { status.textContent = m; }

// ---- styles de sous-titres ----
(async function initStyles() {
  try {
    const list = await window.api.styles();
    styleSel.innerHTML = '';
    list.forEach(s => { const o = document.createElement('option'); o.value = s.key; o.textContent = s.label; styleSel.appendChild(o); });
  } catch (_) {}
})();

function setState(res) {
  state.cleanPath = res.clean_path;
  state.duration = res.duration;
  state.words = res.words;
  state.retakes = res.detect.retakes;
  state.lowconf = res.detect.lowconf;
  state.pauses = res.detect.pauses || [];
  state.peaks = res.peaks || [];
  state.sel = null;
  // Les inserts manuels sont liés au timecode de l'audio courant ; on les remet
  // à zéro à chaque rechargement/coupe pour éviter les positions incohérentes.
  state.inserts = [];
  transcript.value = res.transcript;
  player.src = 'file://' + res.clean_path.replace(/\\/g, '/') + '?t=' + Date.now();
  playBtn.disabled = false;
  updateSelButtons();
  if (res.caption) captionBox.value = res.caption.full;
  buildRegions();
  drawWave();
}

function buildRegions() {
  regions = [];
  state.retakes.forEach(r => regions.push({ type: 'y', start: r.start, end: r.end, ref: r }));
  const low = [...state.lowconf].sort((a, b) => a - b);
  let i = 0;
  while (i < low.length) {
    let j = i;
    while (j + 1 < low.length && low[j + 1] === low[j] + 1) j++;
    const idxs = low.slice(i, j + 1);
    regions.push({ type: 'r', start: state.words[idxs[0]].start, end: state.words[idxs[idxs.length - 1]].end, idxs });
    i = j + 1;
  }
  (state.pauses || []).forEach(p => regions.push({ type: 'y', kind: 'pause', start: p.start, end: p.end, ref: p }));
}

// ---- dessin ----
function drawWave() {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth, H = canvas.clientHeight;
  canvas.width = W * dpr; canvas.height = H * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  const mid = H / 2;
  const t2x = t => state.duration ? (t / state.duration) * W : 0;

  regions.forEach(r => {
    const x1 = t2x(r.start), x2 = t2x(r.end);
    ctx.fillStyle = r.type === 'y' ? 'rgba(255,212,0,.16)' : 'rgba(239,68,68,.16)';
    ctx.fillRect(x1, 0, Math.max(2, x2 - x1), H);
    ctx.strokeStyle = r.type === 'y' ? '#ffd400' : '#ef4444';
    ctx.lineWidth = 2;
    ctx.strokeRect(x1 + 1, 4, Math.max(2, x2 - x1) - 2, H - 8);
  });

  const p = state.peaks, n = p.length;
  if (n) {
    ctx.fillStyle = '#3b9ad9';
    const bw = Math.max(1, W / n);
    for (let i = 0; i < n; i++) {
      const x = (i / n) * W;
      const h = Math.max(1, p[i] * (H * 0.45));
      ctx.fillRect(x, mid - h, bw * 0.8, h * 2);
    }
  }

  if (state.sel) {
    const x1 = t2x(state.sel.start), x2 = t2x(state.sel.end);
    ctx.fillStyle = 'rgba(59,130,246,.28)';
    ctx.fillRect(x1, 0, x2 - x1, H);
    ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2;
    ctx.strokeRect(x1, 0, x2 - x1, H);
  }

  const px = t2x(player.currentTime || 0);
  ctx.fillStyle = '#fff';
  ctx.fillRect(px, 0, 2, H);

  // Track visuelle alignée temporellement avec le waveform
  drawVisualTrack();
}
window.addEventListener('resize', () => { drawWave(); });

// ====== Track visuelle (B-roll manuel : images + vidéos) ======
const visualTrack = document.getElementById('visualTrack');
const visualInsertsEl = document.getElementById('visualInserts');
const visualEmpty = document.getElementById('visualEmpty');
const visualCursor = document.getElementById('visualCursor');

const IMG_EXT = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'];
const VID_EXT = ['.mp4', '.mov', '.webm', '.mkv'];
const INSERT_DEFAULT_DUR = 2.5;
const INSERT_MIN_DUR = 0.5;

function _ext(p) {
  const i = (p || '').lastIndexOf('.');
  return i >= 0 ? p.slice(i).toLowerCase() : '';
}
function _kindFromPath(p) {
  const e = _ext(p);
  if (IMG_EXT.includes(e)) return 'image';
  if (VID_EXT.includes(e)) return 'clip';
  return null;
}
function _fileUrl(p) { return 'file://' + p.replace(/\\/g, '/') + '?t=' + Date.now(); }
function _basename(p) { return (p || '').replace(/\\/g, '/').split('/').pop(); }

function drawVisualTrack() {
  visualInsertsEl.innerHTML = '';
  visualEmpty.style.display = state.inserts.length ? 'none' : 'grid';
  const W = visualTrack.clientWidth || 1;
  const dur = state.duration || 1;
  state.inserts.forEach((ins, i) => {
    const left = (ins.start / dur) * W;
    const width = Math.max(8, ((ins.end - ins.start) / dur) * W);
    const el = document.createElement('div');
    el.className = 'insert';
    el.style.left = left + 'px';
    el.style.width = width + 'px';
    if (ins.kind === 'image') el.style.backgroundImage = `url('${_fileUrl(ins.path)}')`;
    el.dataset.idx = i;
    el.title = `${ins.kind === 'image' ? '📷' : '🎬'} ${_basename(ins.path)} · ${(ins.end - ins.start).toFixed(1)}s`;
    const ico = document.createElement('div'); ico.className = 'ins-icon'; ico.textContent = ins.kind === 'image' ? '📷' : '🎬';
    const name = document.createElement('div'); name.className = 'ins-name'; name.textContent = _basename(ins.path);
    const hL = document.createElement('div'); hL.className = 'ins-handle left';  hL.dataset.handle = 'L'; hL.dataset.idx = i;
    const hR = document.createElement('div'); hR.className = 'ins-handle right'; hR.dataset.handle = 'R'; hR.dataset.idx = i;
    el.appendChild(ico); el.appendChild(name); el.appendChild(hL); el.appendChild(hR);
    visualInsertsEl.appendChild(el);
  });
  // Curseur de lecture aligné
  const t = player.currentTime || 0;
  visualCursor.style.left = ((t / dur) * W) + 'px';
}

function _trackXToTime(clientX) {
  const r = visualTrack.getBoundingClientRect();
  const t = ((clientX - r.left) / r.width) * (state.duration || 1);
  return Math.max(0, Math.min(state.duration || 0, t));
}

// --- Drag&drop fichier sur la track : ajoute un insert au timestamp visé ---
['dragenter','dragover'].forEach(e => visualTrack.addEventListener(e, ev => {
  ev.preventDefault(); ev.stopPropagation();
  visualTrack.classList.add('drag');
}));
['dragleave','drop'].forEach(e => visualTrack.addEventListener(e, ev => {
  ev.preventDefault(); ev.stopPropagation();
  visualTrack.classList.remove('drag');
}));
visualTrack.addEventListener('drop', ev => {
  ev.preventDefault(); ev.stopPropagation();
  if (!state.duration) { setStatus('Charge un audio d\'abord avant d\'ajouter un visuel.'); return; }
  const t = _trackXToTime(ev.clientX);
  const files = Array.from(ev.dataTransfer.files || []);
  let added = 0;
  files.forEach(f => {
    const p = window.api.getPath(f);
    const kind = _kindFromPath(p);
    if (!kind) return;
    const start = Math.max(0, Math.min(state.duration - INSERT_MIN_DUR, t + added * INSERT_DEFAULT_DUR));
    const end = Math.min(state.duration, start + INSERT_DEFAULT_DUR);
    state.inserts.push({ kind, path: p, start, end });
    added++;
  });
  if (added) {
    state.inserts.sort((a, b) => a.start - b.start);
    drawVisualTrack();
    setStatus(`${added} insert${added > 1 ? 's' : ''} ajouté${added > 1 ? 's' : ''}.`);
  } else {
    setStatus('Format non supporté (utilise PNG/JPG/WEBP ou MP4/MOV/WEBM).');
  }
});

// --- Move / Resize : mousedown sur un .insert ---
let insertDrag = null;
visualInsertsEl.addEventListener('mousedown', ev => {
  const handle = ev.target.closest('.ins-handle');
  const block = ev.target.closest('.insert');
  if (!block) return;
  ev.preventDefault();
  const idx = parseInt(block.dataset.idx, 10);
  const ins = state.inserts[idx];
  insertDrag = {
    idx, t0: _trackXToTime(ev.clientX),
    startOrig: ins.start, endOrig: ins.end,
    mode: handle ? (handle.dataset.handle === 'L' ? 'resizeL' : 'resizeR') : 'move',
  };
  block.classList.add('dragging');
});
window.addEventListener('mousemove', ev => {
  if (!insertDrag) return;
  const t = _trackXToTime(ev.clientX);
  const dt = t - insertDrag.t0;
  const ins = state.inserts[insertDrag.idx];
  const dur = state.duration;
  if (insertDrag.mode === 'move') {
    const len = insertDrag.endOrig - insertDrag.startOrig;
    let s = Math.max(0, Math.min(dur - len, insertDrag.startOrig + dt));
    ins.start = s; ins.end = s + len;
  } else if (insertDrag.mode === 'resizeL') {
    let s = Math.max(0, Math.min(insertDrag.endOrig - INSERT_MIN_DUR, insertDrag.startOrig + dt));
    ins.start = s;
  } else if (insertDrag.mode === 'resizeR') {
    let e = Math.max(insertDrag.startOrig + INSERT_MIN_DUR, Math.min(dur, insertDrag.endOrig + dt));
    ins.end = e;
  }
  drawVisualTrack();
});
window.addEventListener('mouseup', () => {
  if (!insertDrag) return;
  state.inserts.sort((a, b) => a.start - b.start);
  insertDrag = null;
  drawVisualTrack();
});

// --- Clic droit sur insert -> supprimer ---
visualInsertsEl.addEventListener('contextmenu', ev => {
  const block = ev.target.closest('.insert');
  if (!block) return;
  ev.preventDefault();
  const idx = parseInt(block.dataset.idx, 10);
  state.inserts.splice(idx, 1);
  drawVisualTrack();
  setStatus('Insert supprimé.');
});

// ---- sélection (drag) / clic ----
function xToTime(clientX) {
  const rect = canvas.getBoundingClientRect();
  let t = ((clientX - rect.left) / rect.width) * state.duration;
  return Math.max(0, Math.min(state.duration, t));
}
canvas.addEventListener('mousedown', e => {
  if (!state.duration) return;
  drag = { x0: e.clientX, t0: xToTime(e.clientX), moved: false };
});
window.addEventListener('mousemove', e => {
  if (!drag) return;
  if (Math.abs(e.clientX - drag.x0) > 3) {
    drag.moved = true;
    const t = xToTime(e.clientX);
    state.sel = { start: Math.min(drag.t0, t), end: Math.max(drag.t0, t) };
    drawWave();
  }
});
window.addEventListener('mouseup', e => {
  if (!drag) return;
  if (!drag.moved) {
    const t = drag.t0;
    const reg = regions.find(r => t >= r.start && t <= r.end);
    if (reg) showMenuAt(e.clientX, e.clientY, () => keepRegion(reg), () => cutRange(reg.start, reg.end));
    else { state.sel = null; player.currentTime = t; drawWave(); }
  }
  updateSelButtons();
  drag = null;
});

function updateSelButtons() {
  const has = !!state.sel;
  selPlay.disabled = selDel.disabled = selClear.disabled = !has;
}
selClear.addEventListener('click', () => { state.sel = null; updateSelButtons(); drawWave(); });
selDel.addEventListener('click', () => { if (state.sel) cutRange(state.sel.start, state.sel.end); });
selPlay.addEventListener('click', () => {
  if (!state.sel) return;
  player.currentTime = state.sel.start; playingSel = true; player.play();
});

function keepRegion(reg) {
  if (reg.kind === 'pause') state.pauses = state.pauses.filter(p => p !== reg.ref);
  else if (reg.type === 'y') state.retakes = state.retakes.filter(r => r !== reg.ref);
  else { const s = new Set(reg.idxs); state.lowconf = state.lowconf.filter(i => !s.has(i)); }
  buildRegions(); drawWave();
}

async function cutRange(s, e) {
  hideMenu();
  setStatus('Suppression + ré-analyse…');
  try {
    const res = await window.api.cut(state.cleanPath, [[s, e]]);
    if (res.error) throw new Error(res.error);
    setState(res);
    setStatus(`Mis à jour (${res.duration.toFixed(1)} s).`);
  } catch (err) { setStatus('Erreur coupe : ' + (err.message || err)); }
}

// ---- lecture ----
playBtn.addEventListener('click', () => { player.paused ? player.play() : player.pause(); });
player.addEventListener('play', () => { playBtn.textContent = '⏸ Pause'; tick(); });
player.addEventListener('pause', () => { playBtn.textContent = '▶ Lire'; playingSel = false; });
player.addEventListener('timeupdate', () => {
  updateTime();
  if (playingSel && state.sel && player.currentTime >= state.sel.end) { player.pause(); playingSel = false; }
});
function tick() { if (player.paused) return; drawWave(); requestAnimationFrame(tick); }
function fmt(s) { s = Math.max(0, s | 0); return String((s / 60) | 0).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); }
function updateTime() { timeLbl.textContent = `${fmt(player.currentTime)} / ${fmt(state.duration)}`; }

// ---- menu ----
function showMenuAt(x, y, onKeep, onDelete) {
  menu.innerHTML = '';
  const k = document.createElement('button'); k.className = 'keep'; k.textContent = '✓ Garder';
  const d = document.createElement('button'); d.className = 'del'; d.textContent = '🗑 Supprimer';
  k.onclick = () => { hideMenu(); onKeep(); };
  d.onclick = () => { hideMenu(); onDelete(); };
  menu.appendChild(k); menu.appendChild(d);
  menu.style.display = 'flex';
  menu.style.left = Math.min(x, window.innerWidth - 190) + 'px';
  menu.style.top = Math.min(y, window.innerHeight - 50) + 'px';
}
function hideMenu() { menu.style.display = 'none'; }
document.addEventListener('mousedown', e => { if (!menu.contains(e.target) && e.target !== canvas) hideMenu(); });

// ---- drag & drop fichier ----
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => e.preventDefault());
['dragenter','dragover'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.add('drag'); }));
['dragleave','drop'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.remove('drag'); }));

drop.addEventListener('drop', async ev => {
  ev.preventDefault();
  const f = ev.dataTransfer.files[0];
  if (!f) return;
  const audioPath = window.api.getPath(f);
  if (!audioPath) { setStatus('Impossible de lire le chemin du fichier.'); return; }
  fileLbl.textContent = f.name;
  setStatus('Transcription + nettoyage en cours…');
  genBtn.disabled = expBtn.disabled = true;
  try {
    const res = await window.api.load(audioPath);
    if (res.error) throw new Error(res.error);
    if (!res.clean_path) throw new Error(JSON.stringify(res).slice(0, 200));
    setState(res);
    updateTime();
    setStatus(`Prêt (${res.duration.toFixed(1)} s). Vérifie les zones sur la forme d'onde.`);
    genBtn.disabled = false;
  } catch (e) { setStatus('Erreur : ' + (e.message || e)); }
});

// ---- aperçu / export ----
function _insertsForBackend() {
  // Sérialise les inserts pour le backend (kind/path/start/end uniquement)
  return state.inserts.map(i => ({ kind: i.kind, path: i.path, start: i.start, end: i.end }));
}

genBtn.addEventListener('click', async () => {
  setStatus('Génération de l\'aperçu…');
  try {
    const res = await window.api.preview(state.cleanPath, transcript.value, styleSel.value, boostChk.checked, _insertsForBackend());
    if (res.error) throw new Error(res.error);
    preview.src = 'file://' + res.video_path.replace(/\\/g, '/') + '?t=' + Date.now();
    preview.style.display = 'block';
    preview.currentTime = 0;
    preview.play().catch(() => {});
    setStatus('Aperçu prêt (lecture auto).');
    expBtn.disabled = false;
  } catch (e) { setStatus('Erreur aperçu : ' + (e.message || e)); }
});

expBtn.addEventListener('click', async () => {
  const out = await window.api.savePath();
  if (!out) return;
  setStatus('Export…');
  try {
    const res = await window.api.export(state.cleanPath, transcript.value, out, styleSel.value, boostChk.checked, _insertsForBackend());
    if (res.error) throw new Error(res.error);
    setStatus('Exporté : ' + res.video_path);
    lastExport = res.video_path;
    igBtn.disabled = false;
  } catch (e) { setStatus('Erreur export : ' + (e.message || e)); }
});
