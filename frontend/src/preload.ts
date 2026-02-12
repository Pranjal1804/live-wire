import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  setClickthrough: (enabled: boolean) =>
    ipcRenderer.send("set-clickthrough", enabled),

  setAlwaysOnTop: (enabled: boolean) =>
    ipcRenderer.send("set-always-on-top", enabled),

  resizeWindow: (w: number, h: number) =>
    ipcRenderer.send("resize-window", w, h),

  closeApp: () =>
    ipcRenderer.send("close-app"),
});
