use std::sync::Arc;
use tauri::Manager;

mod audio;

/// Holds the cpal Stream handles. They must stay alive for capture to continue.
/// Wrapped in Option so we can take/drop them on stop.
struct StreamHandles {
    _mic: cpal::Stream,
    _loopback: cpal::Stream,
}

// We cannot Send cpal::Stream across threads on all platforms, so we
// store them in a std::sync::Mutex on the main thread side and only
// manipulate them from Tauri commands (which run on the main thread).
struct AudioStreams(std::sync::Mutex<Option<StreamHandles>>);

// ── Existing window commands ──

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

// ── Audio capture commands ──

#[tauri::command]
fn start_audio_capture(state: tauri::State<'_, Arc<audio::AudioCaptureState>>, streams: tauri::State<'_, AudioStreams>) -> Result<String, String> {
    // Check if already running
    if state.running.load(std::sync::atomic::Ordering::Relaxed) {
        return Err("Audio capture is already running".into());
    }

    let (mic_stream, loopback_stream) = audio::start_capture(state.inner().clone())?;

    if let Ok(mut lock) = streams.0.lock() {
        *lock = Some(StreamHandles {
            _mic: mic_stream,
            _loopback: loopback_stream,
        });
    }

    Ok("Audio capture started".into())
}

#[tauri::command]
fn stop_audio_capture(state: tauri::State<'_, Arc<audio::AudioCaptureState>>, streams: tauri::State<'_, AudioStreams>) -> Result<String, String> {
    audio::stop_capture(&state);

    // Drop the stream handles to release the audio devices
    if let Ok(mut lock) = streams.0.lock() {
        *lock = None;
    }

    Ok("Audio capture stopped".into())
}

#[tauri::command]
fn poll_audio_chunks(state: tauri::State<'_, Arc<audio::AudioCaptureState>>) -> Vec<audio::AudioChunk> {
    audio::drain_chunks(&state)
}

#[tauri::command]
fn get_talk_ratio(state: tauri::State<'_, Arc<audio::AudioCaptureState>>) -> (f32, f32) {
    audio::get_talk_ratio(&state)
}

#[tauri::command]
fn list_audio_devices() -> serde_json::Value {
    serde_json::json!({
        "input": audio::list_input_devices(),
        "output": audio::list_output_devices(),
    })
}

// ── App entry ──

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let capture_state = Arc::new(audio::AudioCaptureState::default());

    tauri::Builder::default()
        .plugin(tauri_plugin_process::init())
        .manage(capture_state)
        .manage(AudioStreams(std::sync::Mutex::new(None)))
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
            resize_window,
            start_audio_capture,
            stop_audio_capture,
            poll_audio_chunks,
            get_talk_ratio,
            list_audio_devices,
        ])
        .run(tauri::generate_context!())
        .expect("error while running MAESTRO");
}
