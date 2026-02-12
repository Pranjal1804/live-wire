import { invoke } from "@tauri-apps/api/core";

export const tauriAPI = {
  setClickthrough: (enabled: boolean) =>
    invoke("set_clickthrough", { ignore: enabled }),

  setAlwaysOnTop: (enabled: boolean) =>
    invoke("set_always_on_top", { enabled }),

  resizeWindow: (w: number, h: number) =>
    invoke("resize_window", { width: w, height: h }),

  closeApp: () => invoke("close_app"),
};
