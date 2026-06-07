const drop = document.getElementById('drop');
const fileLbl = document.getElementById('file');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const preview = document.getElementById('preview');
const genBtn = document.getElementById('genBtn');
const expBtn = document.getElementById('expBtn');
const styleSel = document.getElementById('style');
const boostChk = document.getElementById('boost');
const menu = document.getElementById('menu');
const canvas = document.getElementById('wave');
const player = document.getElementById('player');
const playBtn = document.getElementById('playBtn');
const timeLbl = document.getElementById('time');
const selPlay = document.getElementById('selPlay');
const selDel = document.getElementById('selDel');
const selClear = document.getElementById('selClear');

const state = { cleanPath: null, duration: 0, words: [], retakes: [], lowconf: [], peaks: [], sel: null };
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
  state.peaks = res.peaks || [];
  state.sel = null;
  transcript.value = res.transcript;
  player.src = 'file://' + res.clean_path.replace(/\\/g, '/') + '?t=' + Date.now();
  playBtn.disabled = false;
  updateSelButtons();
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
}
window.addEventListener('resize', drawWave);

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
  if (reg.type === 'y') state.retakes = state.retakes.filter(r => r !== reg.ref);
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
genBtn.addEventListener('click', async () => {
  setStatus('Génération de l\'aperçu…');
  try {
    const res = await window.api.preview(state.cleanPath, transcript.value, styleSel.value, boostChk.checked);
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
    const res = await window.api.export(state.cleanPath, transcript.value, out, styleSel.value, boostChk.checked);
    if (res.error) throw new Error(res.error);
    setStatus('Exporté : ' + res.video_path);
  } catch (e) { setStatus('Erreur export : ' + (e.message || e)); }
});
