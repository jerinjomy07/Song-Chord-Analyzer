const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktopAPI', {
  isElectron: true,
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node
  },
  openFileDialog: () => ipcRenderer.invoke('dialog:openFile'),
  showSaveDialog: (options) => ipcRenderer.invoke('dialog:saveFile', options),
  saveExportFile: (payload) => ipcRenderer.invoke('export:saveFile', payload),
  minimizeWindow: () => ipcRenderer.send('window:minimize'),
  maximizeWindow: () => ipcRenderer.send('window:maximize'),
  closeWindow: () => ipcRenderer.send('window:close'),
  getBackendInfo: () => ipcRenderer.invoke('backend:info')
});
