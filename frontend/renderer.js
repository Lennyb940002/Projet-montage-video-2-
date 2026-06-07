const drop = document.getElementById('drop');
const fileLbl = document.getElementById('file');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const preview = document.getElementById('preview');
const genBtn = document.getElementById('genBtn');
const expBtn = document.getElementById('expBtn');
const menu = document.getElementById('menu');

const state = { cleanPath: null, duration: 0, words: [], retakes: [], lowconf: [] };
function setStatus(m) { status.textContent = m; }

function setState(res) {
  state.cleanPath = res.clean_path;
  state.duration = res.duration;
  state.words = res.words;
  state.retakes = res.detect.retakes;
  state.lowconf = res.detect.lowconf;
}

// ---- drag & drop ----
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
    if (!res.clean_path) throw new Error(JSON.stringify(res).slice(0, 200));
    setState(res);
    renderTranscript();
    setStatus(`Prêt (${res.duration.toFixed(1)} s). Vérifie les passages surlignés puis génère.`);
    genBtn.disabled = false;
  } catch (e) { setStatus('Erreur : ' + (e.message || e)); }
});

// ---- rendu transcription ----
function renderTranscript() {
  hideMenu();
  transcript.innerHTML = '';
  const retakeOf = {};
  state.retakes.forEach((r, ri) => { for (let k = r.i1; k < r.i2; k++) retakeOf[k] = ri; });
  const low = new Set(state.lowconf);
  state.words.forEach((w, i) => {
    const s = document.createElement('span');
    s.className = 'w'; s.dataset.i = i; s.textContent = w.text;
    if (i in retakeOf) { s.classList.add('yellow'); s.dataset.retake = retakeOf[i]; }
    else if (low.has(i)) s.classList.add('red');
    s.addEventListener('click', onWordClick);
    s.addEventListener('dblclick', onWordEdit);
    transcript.appendChild(s);
    transcript.appendChild(document.createTextNode(' '));
  });
}

function onWordClick(ev) {
  const span = ev.currentTarget;
  if (span.isContentEditable) return;
  const i = +span.dataset.i;
  if (span.classList.contains('yellow')) {
    const r = state.retakes[+span.dataset.retake];
    showMenu(ev, () => resolveRetake(r), () => cutRange(r.start, r.end));
  } else if (span.classList.contains('red')) {
    const w = state.words[i];
    showMenu(ev, () => resolveLow(i), () => cutRange(w.start, w.end));
  }
}

function onWordEdit(ev) {
  const span = ev.currentTarget;
  hideMenu();
  span.contentEditable = 'true';
  span.focus();
  document.execCommand('selectAll', false, null);
  const finish = () => {
    span.contentEditable = 'false';
    const i = +span.dataset.i;
    state.words[i].text = span.textContent.trim();
    span.removeEventListener('blur', finish);
  };
  span.addEventListener('blur', finish);
  span.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); span.blur(); } });
}

// ---- menu Garder / Supprimer ----
function showMenu(ev, onKeep, onDelete) {
  menu.innerHTML = '';
  const k = document.createElement('button'); k.className = 'keep'; k.textContent = '✓ Garder';
  const d = document.createElement('button'); d.className = 'del'; d.textContent = '🗑 Supprimer';
  k.onclick = () => { hideMenu(); onKeep(); };
  d.onclick = () => { hideMenu(); onDelete(); };
  menu.appendChild(k); menu.appendChild(d);
  menu.style.display = 'flex';
  const rect = ev.currentTarget.getBoundingClientRect();
  menu.style.left = Math.min(rect.left, window.innerWidth - 180) + 'px';
  menu.style.top = (rect.bottom + 4) + 'px';
}
function hideMenu() { menu.style.display = 'none'; }
document.addEventListener('click', e => {
  if (!menu.contains(e.target) && !e.target.classList.contains('w')) hideMenu();
});

function resolveRetake(r) { state.retakes = state.retakes.filter(x => x !== r); renderTranscript(); }
function resolveLow(i) { state.lowconf = state.lowconf.filter(x => x !== i); renderTranscript(); }

async function cutRange(s, e) {
  setStatus('Suppression + ré-analyse…');
  try {
    const res = await window.api.cut(state.cleanPath, [[s, e]]);
    setState(res);
    renderTranscript();
    setStatus(`Mis à jour (${res.duration.toFixed(1)} s).`);
  } catch (err) { setStatus('Erreur coupe : ' + (err.message || err)); }
}

function currentText() { return state.words.map(w => w.text).join(' '); }

// ---- aperçu / export ----
genBtn.addEventListener('click', async () => {
  setStatus('Génération de l\'aperçu…');
  try {
    const res = await window.api.preview(state.cleanPath, currentText());
    preview.src = 'file://' + res.video_path.replace(/\\/g, '/') + '?t=' + Date.now();
    preview.style.display = 'block';
    setStatus('Aperçu prêt.');
    expBtn.disabled = false;
  } catch (e) { setStatus('Erreur aperçu : ' + (e.message || e)); }
});

expBtn.addEventListener('click', async () => {
  const out = prompt('Chemin de sortie (ex: C:\\Users\\User\\Desktop\\video.mp4)');
  if (!out) return;
  setStatus('Export…');
  try {
    const res = await window.api.export(state.cleanPath, currentText(), out);
    setStatus('Exporté : ' + res.video_path);
  } catch (e) { setStatus('Erreur export : ' + (e.message || e)); }
});
