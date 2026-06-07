const { contextBridge, webUtils } = require('electron');
const PORT = 8765;
const base = `http://127.0.0.1:${PORT}`;

function post(path, body) {
  return fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => r.json());
}

contextBridge.exposeInMainWorld('api', {
  // Electron 32+ : File.path supprimé -> récupérer le chemin via webUtils
  getPath: (file)                       => webUtils.getPathForFile(file),
  load:    (audio_path)                 => post('/load',    { audio_path }),
  cut:     (clean_path, ranges)         => post('/cut',     { clean_path, ranges }),
  preview: (clean_path, text)           => post('/preview', { clean_path, text }),
  export:  (clean_path, text, out_path) => post('/export',  { clean_path, text, out_path })
});
