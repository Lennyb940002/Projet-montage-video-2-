const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let backend;
const PORT = 8765;

function startBackend() {
  // lance: python -m uvicorn backend.server:app (cwd = racine projet)
  const root = path.join(__dirname, '..');
  backend = spawn('python', ['-m', 'uvicorn', 'backend.server:app',
    '--host', '127.0.0.1', '--port', String(PORT)],
    { cwd: root, shell: true });
  backend.stdout.on('data', d => console.log('[py]', d.toString()));
  backend.stderr.on('data', d => console.log('[py]', d.toString()));
}

async function waitForBackend(retries = 40) {
  for (let i = 0; i < retries; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/health`);
      if (r.ok) return true;
    } catch (_) {}
    await new Promise(res => setTimeout(res, 500));
  }
  return false;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1400, height: 900, backgroundColor: '#0f0f10',
    webPreferences: { preload: path.join(__dirname, 'preload.js') }
  });
  win.loadFile('index.html');
}

app.whenReady().then(async () => {
  startBackend();
  await waitForBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (backend) backend.kill();
  if (process.platform !== 'darwin') app.quit();
});
