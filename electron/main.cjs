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

  // 4. Windows AppData SongChordAnalyzer venv (isolated app runtime)
  const localAppData = process.env.LOCALAPPDATA || '';
  const appVenvPython = path.join(localAppData, 'SongChordAnalyzer', 'venv', 'Scripts', 'python.exe');
  if (fs.existsSync(appVenvPython)) {
    return appVenvPython;
  }

  // 5. Windows AppData StemKit venv (development / companion environment)
  const appData = process.env.APPDATA || '';
  const stemkitPython = path.join(appData, 'StemKit', 'venv', 'Scripts', 'python.exe');
  if (fs.existsSync(stemkitPython)) {
    return stemkitPython;
  }

  // 6. Project local venv (.venv or venv)
  const localVenv = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
  if (fs.existsSync(localVenv)) {
    return localVenv;
  }
  const localVenv2 = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe');
  if (fs.existsSync(localVenv2)) {
    return localVenv2;
  }

  // 7. System PATH fallback
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
  const rootDir = app.isPackaged
    ? path.join(process.resourcesPath, 'app.asar.unpacked')
    : path.resolve(__dirname, '..');
  const scriptPath = path.join(rootDir, 'run_app.py');

  console.log(`[Electron] Launching Python backend...`);
  console.log(`[Electron] Python executable: ${pythonPath}`);
  console.log(`[Electron] Script: ${scriptPath} on port ${port}`);

  const ffmpegBin = app.isPackaged
    ? path.join(process.resourcesPath, 'ffmpeg', 'ffmpeg.exe')
    : path.join(__dirname, '..', 'resources', 'ffmpeg', 'ffmpeg.exe');

  const env = {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    SONG_CHORD_ANALYZER_PORT: String(port),
    SONG_CHORD_ANALYZER_NO_BROWSER: '1',
    SONG_CHORD_ANALYZER_PYTHON: pythonPath,
    SONG_CHORD_ANALYZER_FFMPEG: fs.existsSync(ffmpegBin) ? ffmpegBin : ''
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

  // Setup download handling for any direct browser downloads with safe fallback
  session.defaultSession.on('will-download', (event, item, webContents) => {
    try {
      const defaultFilename = sanitizeFilename(item.getFilename());
      if (typeof item.setSaveDialogOptions === 'function') {
        const defaultFolder = app.getPath('downloads') || app.getPath('documents');
        item.setSaveDialogOptions({
          title: 'Save Exported File',
          defaultPath: path.join(defaultFolder, defaultFilename)
        });
      }

      item.once('done', (event, state) => {
        if (state === 'completed') {
          console.log('[Electron Download] Saved successfully to:', item.getSavePath());
        } else if (state === 'cancelled') {
          console.log('[Electron Download] Export cancelled by user');
        } else {
          console.warn(`[Electron Download] Export state: ${state}`);
        }
      });
    } catch (err) {
      console.error('[Electron Download] Error during will-download handling:', err);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Sanitize filename to ensure Windows path compliance
function sanitizeFilename(name) {
  if (!name) return 'Song';
  let clean = name
    .replace(/[/\\]/g, '-')
    .replace(/[<>:"|?*\x00-\x1f\uff5c]/g, '_')
    .replace(/\s+/g, ' ')
    .replace(/\s*_\s*/g, '_')
    .replace(/_+/g, '_')
    .trim();
  clean = clean.replace(/^[ ._-]+|[ ._-]+$/g, '');
  return clean || 'Song';
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

ipcMain.handle('export:saveFile', async (event, { defaultFilename, format, content, isBase64 }) => {
  try {
    const safeFilename = sanitizeFilename(defaultFilename || `Song_ChordSheet.${format}`);
    const documentsDir = app.getPath('documents') || app.getPath('downloads');
    const defaultPath = path.join(documentsDir, safeFilename);

    let filters = [{ name: 'All Files', extensions: ['*'] }];
    if (format === 'pdf') {
      filters = [{ name: 'PDF Chord Sheet (*.pdf)', extensions: ['pdf'] }, ...filters];
    } else if (format === 'txt') {
      filters = [{ name: 'Monospace Text Chart (*.txt)', extensions: ['txt'] }, ...filters];
    } else if (format === 'json') {
      filters = [{ name: 'Structured JSON (*.json)', extensions: ['json'] }, ...filters];
    }

    const result = await dialog.showSaveDialog(mainWindow, {
      title: `Export ${format.toUpperCase()}`,
      defaultPath: defaultPath,
      filters: filters
    });

    if (result.canceled || !result.filePath) {
      return { canceled: true };
    }

    const buffer = isBase64 ? Buffer.from(content, 'base64') : Buffer.from(content, 'utf-8');
    await fs.promises.writeFile(result.filePath, buffer);

    console.log(`[Export] Successfully saved ${format.toUpperCase()} to: ${result.filePath}`);
    return {
      success: true,
      filePath: result.filePath,
      filename: path.basename(result.filePath)
    };
  } catch (err) {
    console.error(`[Export Error] Failed to export ${format}:`, err);
    return {
      success: false,
      error: `${format.toUpperCase()} export failed. Please try again.`
    };
  }
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
