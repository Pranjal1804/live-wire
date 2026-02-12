use tauri::Manager;

#[tauri::command]
fn set_clickthrough(window: tauri::Window, ignore: bool) {
    let _ = window.set_ignore_cursor_events(ignore);
    if !ignore {
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn close_app(app: tauri::AppHandle) {
    app.exit(0);
}

#[tauri::command]
fn set_always_on_top(window: tauri::Window, enabled: bool) {
    let _ = window.set_always_on_top(enabled);
}

#[tauri::command]
fn resize_window(window: tauri::Window, width: f64, height: f64) {
    let _ = window.set_size(tauri::Size::Logical(tauri::LogicalSize::new(width, height)));
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();

            // Position at right edge of primary monitor
            if let Ok(Some(monitor)) = window.primary_monitor() {
                let screen_size = monitor.size();
                let scale = monitor.scale_factor();
                let x = (screen_size.width as f64 / scale) - 390.0;
                let _ = window.set_position(tauri::Position::Logical(
                    tauri::LogicalPosition::new(x, 0.0),
                ));
                let _ = window.set_size(tauri::Size::Logical(
                    tauri::LogicalSize::new(380.0, screen_size.height as f64 / scale),
                ));
            }

            // Start in click-through mode
            let _ = window.set_ignore_cursor_events(true);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            set_clickthrough,
            close_app,
            set_always_on_top,
            resize_window
        ])
        .run(tauri::generate_context!())
        .expect("error while running MAESTRO");
}
