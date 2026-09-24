const { app, BrowserWindow, ipcMain, dialog, session } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const net = require('net');
const { spawn, exec } = require('child_process');

let mainWindow = null;
let splashWindow = null;
let pythonProcess = null;
let assignedPort = 8000;
let isQuitting = false;
let restartAttempts = 0;
const MAX_RESTART_ATTEMPTS = 3;

// Find free TCP port
function findFreePort(startPort = 8000) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(startPort, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', () => {
      // If startPort is in use, let OS assign a random free port
      const fallbackServer = net.createServer();
      fallbackServer.listen(0, '127.0.0.1', () => {
        const port = fallbackServer.address().port;
        fallbackServer.close(() => resolve(port));
      });
      fallbackServer.on('error', () => resolve(8000));
    });
  });
}

// Find Python executable dynamically across production, resources, and dev environments
function resolvePythonExecutable() {
  // 1. Env variable override
  if (process.env.SONG_CHORD_ANALYZER_PYTHON && fs.existsSync(process.env.SONG_CHORD_ANALYZER_PYTHON)) {
    return process.env.SONG_CHORD_ANALYZER_PYTHON;
  }

  // 2. Packaged Electron resources directory (production installer)
  const resourcesPython = path.join(process.resourcesPath, 'python', 'python.exe');
  if (fs.existsSync(resourcesPython)) {
    return resourcesPython;
  }

  // 3. Local app resources directory
  const localResPython = path.join(__dirname, '..', 'resources', 'python', 'python.exe');
  if (fs.existsSync(localResPython)) {
    return localResPython;
  }

  // 4. Windows AppData StemKit venv (development environment)
  const appData = process.env.APPDATA || '';
  const stemkitPython = path.join(appData, 'StemKit', 'venv', 'Scripts', 'python.exe');
  if (fs.existsSync(stemkitPython)) {
    return stemkitPython;
  }

  // 5. System PATH fallback
  return 'python';
}

// Kill process and all its children on Windows cleanly
function killProcessTree(pid) {
  if (!pid) return;
  try {
    if (process.platform === 'win32') {
      exec(`taskkill /pid ${pid} /T /F`, (err) => {
        if (err) console.log(`[Electron] Cleaned process ${pid}`);
      });
    } else {
      process.kill(pid, 'SIGTERM');
    }
  } catch (err) {
    console.error(`[Electron] Error terminating process ${pid}:`, err);
  }
}

// Start local Python backend process
function startPythonBackend(port) {
  const pythonPath = resolvePythonExecutable();
  const rootDir = path.resolve(__dirname, '..');
  const scriptPath = path.join(rootDir, 'run_app.py');

  console.log(`[Electron] Launching Python backend...`);
  console.log(`[Electron] Python executable: ${pythonPath}`);
  console.log(`[Electron] Script: ${scriptPath} on port ${port}`);

  const env = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    SONG_CHORD_ANALYZER_PORT: String(port),
    SONG_CHORD_ANALYZER_NO_BROWSER: '1'
  };

  pythonProcess = spawn(
    pythonPath,
    [scriptPath, '--port', String(port), '--no-browser'],
    {
      cwd: rootDir,
      env: env,
      stdio: ['pipe', 'pipe', 'pipe']
    }
  );

  pythonProcess.stdout.on('data', (data) => {
    const text = data.toString().trim();
    if (text) console.log(`[Python Backend] ${text}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    const text = data.toString().trim();
    if (text) console.error(`[Python Backend Error] ${text}`);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[Python Backend] Exited with code ${code}, signal ${signal}`);
    pythonProcess = null;

    if (!isQuitting && restartAttempts < MAX_RESTART_ATTEMPTS) {
      restartAttempts++;
      console.log(`[Electron] Unexpected backend exit. Attempting restart (${restartAttempts}/${MAX_RESTART_ATTEMPTS})...`);
      setTimeout(() => startPythonBackend(assignedPort), 2000);
    }
  });

  pythonProcess.on('error', (err) => {
    console.error(`[Python Backend] Spawn error:`, err);
  });
}

// Poll health check until backend is ready
function waitForBackend(port, timeoutMs = 60000) {
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    const check = () => {
      if (Date.now() - startTime > timeoutMs) {
        reject(new Error('Timed out waiting for Python backend to initialize'));
        return;
      }

      const req = http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
        let body = '';
        res.on('data', (chunk) => body += chunk);
        res.on('end', () => {
          if (res.statusCode === 200) {
            try {
              const data = JSON.parse(body);
              if (data.status === 'healthy') {
                resolve(data);
                return;
              }
            } catch (e) {
              // json parse failure
            }
          }
          setTimeout(check, 600);
        });
      });

      req.on('error', () => {
        setTimeout(check, 600);
      });

      req.setTimeout(1500, () => {
        req.destroy();
        setTimeout(check, 600);
      });
    };

    check();
  });
}

// Create splash screen while models & backend boot
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 520,
    height: 340,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    center: true,
    backgroundColor: '#0f172a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  const splashHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {
          margin: 0;
          padding: 32px;
          background: #090d16;
          color: #f8fafc;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          border: 1px solid #1e293b;
          border-radius: 16px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100vh;
          box-sizing: border-box;
          user-select: none;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
        }
        .icon {
          width: 56px;
          height: 56px;
          background: linear-gradient(135deg, #4f46e5, #06b6d4);
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 20px;
          box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.5);
        }
        .icon svg {
          width: 32px;
          height: 32px;
          fill: none;
          stroke: #ffffff;
          stroke-width: 2.2;
          stroke-linecap: round;
          stroke-linejoin: round;
        }
        h1 {
          font-size: 20px;
          font-weight: 700;
          letter-spacing: -0.025em;
          margin: 0 0 6px 0;
          color: #f1f5f9;
        }
        p {
          font-size: 13px;
          color: #94a3b8;
          margin: 0 0 24px 0;
          text-align: center;
        }
        .spinner-container {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 12px;
          color: #64748b;
        }
        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid #334155;
          border-top-color: #6366f1;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      </style>
    </head>
    <body>
      <div class="icon">
        <svg viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10"></circle>
          <polygon points="10 8 16 12 10 16 10 8"></polygon>
        </svg>
      </div>
      <h1>Song Chord Analyzer</h1>
      <p>Starting MIR engine & hardware acceleration...</p>
      <div class="spinner-container">
        <div class="spinner"></div>
        <span>Initializing CUDA & AI models...</span>
      </div>
    </body>
    </html>
  `;

  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(splashHtml)}`);
}

// Create Main Application Window
function createMainWindow(port, healthInfo) {
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#0f172a',
    title: 'Song Chord Analyzer',
    show: false, // show after ready-to-show
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true
    }
  });

  // Remove default menu bar for clean modern desktop look
  mainWindow.setMenuBarVisibility(false);

  // Load backend server URL (serves built React SPA and API)
  const appUrl = `http://127.0.0.1:${port}`;
  console.log(`[Electron] Loading application URL: ${appUrl}`);
  mainWindow.loadURL(appUrl);

  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
    console.log(`[Electron] Main window displayed successfully. GPU Device: ${healthInfo?.device || 'CPU'}`);
  });

  // Setup download handling for PDF/TXT/JSON chord sheets
  session.defaultSession.on('will-download', (event, item, webContents) => {
    const fileName = item.getFilename();
    item.setPromptUser(true);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('dialog:openFile', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'Audio Files', extensions: ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'wma'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  return result;
});

ipcMain.handle('dialog:saveFile', async (event, options) => {
  const result = await dialog.showSaveDialog(mainWindow, options);
  return result;
});

ipcMain.handle('backend:info', () => {
  return {
    port: assignedPort,
    python: resolvePythonExecutable()
  };
});

ipcMain.on('window:minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window:close', () => {
  if (mainWindow) mainWindow.close();
});

// App Lifecycle
app.whenReady().then(async () => {
  createSplashWindow();

  assignedPort = await findFreePort(8000);
  console.log(`[Electron] Selected free port: ${assignedPort}`);

  startPythonBackend(assignedPort);

  try {
    const healthInfo = await waitForBackend(assignedPort, 60000);
    console.log(`[Electron] Backend verified healthy:`, healthInfo);
    createMainWindow(assignedPort, healthInfo);
  } catch (err) {
    console.error(`[Electron] Failed to initialize backend:`, err);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    dialog.showErrorBox(
      'Startup Error',
      `Could not initialize the Song Chord Analyzer audio engine.\n\nDetails: ${err.message}`
    );
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  if (pythonProcess && pythonProcess.pid) {
    console.log(`[Electron] Shutting down Python backend process PID ${pythonProcess.pid}...`);
    killProcessTree(pythonProcess.pid);
    pythonProcess = null;
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0 && !isQuitting) {
    createMainWindow(assignedPort);
  }
});
