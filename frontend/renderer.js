const drop = document.getElementById('drop');
const fileLbl = document.getElementById('file');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const preview = document.getElementById('preview');
const genBtn = document.getElementById('genBtn');
const expBtn = document.getElementById('expBtn');

let cleanPath = null;
function setStatus(msg) { status.textContent = msg; }

// Empêche Electron d'ouvrir le fichier lâché à la place de le traiter
// (indispensable : c'est ce comportement par défaut qui bloquait le drop).
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => e.preventDefault());

['dragenter','dragover'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.add('drag');
}));
['dragleave','drop'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.remove('drag');
}));

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
    cleanPath = res.clean_path;
    transcript.value = res.transcript;
    setStatus(`Prêt (${res.duration.toFixed(1)} s). Corrige le texte puis génère.`);
    genBtn.disabled = false;
  } catch (e) {
    setStatus('Erreur : ' + (e.message || e));
  }
});

genBtn.addEventListener('click', async () => {
  setStatus('Génération de l\'aperçu…');
  try {
    const res = await window.api.preview(cleanPath, transcript.value);
    preview.src = 'file://' + res.video_path.replace(/\\/g,'/') + '?t=' + Date.now();
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
    const res = await window.api.export(cleanPath, transcript.value, out);
    setStatus('Exporté : ' + res.video_path);
  } catch (e) { setStatus('Erreur export : ' + (e.message || e)); }
});
