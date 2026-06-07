const { contextBridge, webUtils, ipcRenderer } = require('electron');
const PORT = 8765;
const base = `http://127.0.0.1:${PORT}`;

function post(path, body) {
  return fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(r => r.json());
}
function get(path) { return fetch(base + path).then(r => r.json()); }

contextBridge.exposeInMainWorld('api', {
  // Electron 32+ : File.path supprimé -> récupérer le chemin via webUtils
  getPath: (file)                              => webUtils.getPathForFile(file),
  savePath: ()                                 => ipcRenderer.invoke('save-dialog'),
  styles:  ()                                  => get('/styles'),
  load:    (audio_path)                        => post('/load',    { audio_path }),
  cut:     (clean_path, ranges)                => post('/cut',     { clean_path, ranges }),
  caption: (text)                              => post('/caption', { text }),
  getSettings: ()                              => get('/settings'),
  saveSettings: (ig_token, ig_user_id)         => post('/settings', { ig_token, ig_user_id }),
  publishInstagram: (video_path, caption)      => post('/publish/instagram', { video_path, caption }),
  preview: (clean_path, text, style, boost)           => post('/preview', { clean_path, text, style, boost }),
  export:  (clean_path, text, out_path, style, boost) => post('/export',  { clean_path, text, out_path, style, boost })
});
