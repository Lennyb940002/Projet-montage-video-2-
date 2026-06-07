const drop = document.getElementById('drop');
const fileLbl = document.getElementById('file');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const preview = document.getElementById('preview');
const genBtn = document.getElementById('genBtn');
const expBtn = document.getElementById('expBtn');

let cleanPath = null;

['dragenter','dragover'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.add('drag');
}));
['dragleave','drop'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.remove('drag');
}));

drop.addEventListener('drop', async ev => {
  const f = ev.dataTransfer.files[0];
  if (!f) return;
  const audioPath = window.api.getPath(f);
  fileLbl.textContent = f.name;
  status.textContent = 'Transcription + nettoyage en cours…';
  genBtn.disabled = expBtn.disabled = true;
  try {
    const res = await window.api.load(audioPath);
    cleanPath = res.clean_path;
    transcript.value = res.transcript;
    status.textContent = `Prêt (${res.duration.toFixed(1)} s). Corrige le texte puis génère.`;
    genBtn.disabled = false;
  } catch (e) {
    status.textContent = 'Erreur : ' + e;
  }
});

genBtn.addEventListener('click', async () => {
  status.textContent = 'Génération de l\'aperçu…';
  try {
    const res = await window.api.preview(cleanPath, transcript.value);
    preview.src = 'file://' + res.video_path.replace(/\\/g,'/') + '?t=' + Date.now();
    preview.style.display = 'block';
    status.textContent = 'Aperçu prêt.';
    expBtn.disabled = false;
  } catch (e) { status.textContent = 'Erreur : ' + e; }
});

expBtn.addEventListener('click', async () => {
  const out = prompt('Chemin de sortie (ex: C:\\Users\\User\\Desktop\\video.mp4)');
  if (!out) return;
  status.textContent = 'Export…';
  try {
    const res = await window.api.export(cleanPath, transcript.value, out);
    status.textContent = 'Exporté : ' + res.video_path;
  } catch (e) { status.textContent = 'Erreur : ' + e; }
});
