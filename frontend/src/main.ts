import { app, BrowserWindow, ipcMain, screen } from "electron";
import * as path from "path";

const isDev = !app.isPackaged;

app.commandLine.appendSwitch("disable-gpu");
app.commandLine.appendSwitch("disable-software-rasterizer");
app.disableHardwareAcceleration();

let mainWindow: BrowserWindow | null = null;

function createOverlayWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 380,
    height: height,
    x: width - 390,
    y: 0,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    focusable: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.setIgnoreMouseEvents(true, { forward: true });
  mainWindow.setAlwaysOnTop(true, "screen-saver");
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

ipcMain.on("set-clickthrough", (event, ignore: boolean) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return;

  if (ignore) {
    win.setIgnoreMouseEvents(true, { forward: true });
  } else {
    win.setIgnoreMouseEvents(false);
    win.focus();
  }
});

ipcMain.on("close-app", () => {
  app.quit();
});

ipcMain.on("set-always-on-top", (_event, enabled: boolean) => {
  mainWindow?.setAlwaysOnTop(enabled, "screen-saver");
});

ipcMain.on("resize-window", (_event, w: number, h: number) => {
  mainWindow?.setSize(w, h);
});

app.whenReady().then(createOverlayWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
