use base64::Engine;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{SampleFormat, StreamConfig};
use serde::Serialize;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

// ── Target format for all audio sent to backend ──
const TARGET_SAMPLE_RATE: u32 = 16000;

// ── VAD parameters ──
const VAD_ENERGY_THRESHOLD: f32 = 0.005; // RMS energy threshold for speech
const VAD_SILENCE_FRAMES: usize = 24; // ~1.5s of silence at 16kHz/1024-sample frames
const VAD_MIN_SPEECH_FRAMES: usize = 5; // minimum ~320ms of speech to emit a chunk

// ── Serializable metadata sent alongside audio chunks ──
#[derive(Debug, Clone, Serialize)]
pub struct AudioChunk {
    /// base64-encoded 16-bit PCM, 16 kHz mono
    pub audio_b64: String,
    /// "mic" or "loopback"
    pub source: String,
    /// duration of this chunk in seconds
    pub duration_secs: f32,
    /// number of samples (mono, 16 kHz)
    pub sample_count: usize,
}

/// Holds the running state for one capture stream (mic or loopback).
/// The VAD accumulates audio while speech is detected, then flushes
/// the entire utterance as a single chunk when silence is detected.
struct VadAccumulator {
    source_label: String,
    buffer: Vec<f32>,          // accumulated f32 samples (mono 16 kHz)
    silence_counter: usize,    // consecutive silent frames
    speech_counter: usize,     // consecutive speech frames in current utterance
    is_speaking: bool,
}

impl VadAccumulator {
    fn new(source_label: &str) -> Self {
        Self {
            source_label: source_label.to_string(),
            buffer: Vec::with_capacity(TARGET_SAMPLE_RATE as usize * 10), // pre-alloc ~10s
            silence_counter: 0,
            speech_counter: 0,
            is_speaking: false,
        }
    }

    /// Feed a frame of mono 16 kHz f32 samples. Returns Some(AudioChunk) when
    /// the speaker stops (silence detected after speech).
    fn feed(&mut self, mono_16k: &[f32]) -> Option<AudioChunk> {
        let rms = (mono_16k.iter().map(|s| s * s).sum::<f32>() / mono_16k.len() as f32).sqrt();
        let is_speech = rms > VAD_ENERGY_THRESHOLD;

        if is_speech {
            self.silence_counter = 0;
            self.speech_counter += 1;
            self.is_speaking = true;
            self.buffer.extend_from_slice(mono_16k);
            None
        } else if self.is_speaking {
            // still accumulate a little silence so we don't clip the tail
            self.buffer.extend_from_slice(mono_16k);
            self.silence_counter += 1;

            if self.silence_counter >= VAD_SILENCE_FRAMES {
                // end of utterance -- flush
                self.is_speaking = false;
                let chunk = self.flush();
                self.silence_counter = 0;
                self.speech_counter = 0;
                chunk
            } else {
                None
            }
        } else {
            // pure silence, not speaking -- discard
            self.silence_counter += 1;
            None
        }
    }

    /// Convert accumulated f32 buffer to a base64-encoded 16-bit PCM chunk.
    fn flush(&mut self) -> Option<AudioChunk> {
        if self.speech_counter < VAD_MIN_SPEECH_FRAMES {
            self.buffer.clear();
            return None;
        }

        let sample_count = self.buffer.len();
        let duration_secs = sample_count as f32 / TARGET_SAMPLE_RATE as f32;

        // Convert f32 [-1.0, 1.0] to i16 PCM bytes (little-endian)
        let mut pcm_bytes: Vec<u8> = Vec::with_capacity(sample_count * 2);
        for &sample in &self.buffer {
            let clamped = sample.clamp(-1.0, 1.0);
            let as_i16 = (clamped * i16::MAX as f32) as i16;
            pcm_bytes.extend_from_slice(&as_i16.to_le_bytes());
        }

        let audio_b64 = base64::engine::general_purpose::STANDARD.encode(&pcm_bytes);

        self.buffer.clear();

        Some(AudioChunk {
            audio_b64,
            source: self.source_label.clone(),
            duration_secs,
            sample_count,
        })
    }
}

/// Converts interleaved multi-channel audio at an arbitrary sample rate
/// to mono at TARGET_SAMPLE_RATE using simple linear interpolation.
fn to_mono_16k(input: &[f32], channels: u16, input_rate: u32) -> Vec<f32> {
    // Step 1: downmix to mono by averaging channels
    let mono: Vec<f32> = input
        .chunks_exact(channels as usize)
        .map(|frame| frame.iter().sum::<f32>() / channels as f32)
        .collect();

    // Step 2: resample if needed
    if input_rate == TARGET_SAMPLE_RATE {
        return mono;
    }

    let ratio = TARGET_SAMPLE_RATE as f64 / input_rate as f64;
    let output_len = (mono.len() as f64 * ratio) as usize;
    let mut resampled = Vec::with_capacity(output_len);

    for i in 0..output_len {
        let src_idx = i as f64 / ratio;
        let idx0 = src_idx.floor() as usize;
        let idx1 = (idx0 + 1).min(mono.len().saturating_sub(1));
        let frac = (src_idx - idx0 as f64) as f32;
        resampled.push(mono[idx0] * (1.0 - frac) + mono[idx1] * frac);
    }

    resampled
}

/// Shared state that both capture threads push chunks into,
/// and the Tauri command polls from.
pub struct AudioCaptureState {
    pub running: AtomicBool,
    pub chunks: Mutex<Vec<AudioChunk>>,
    /// Cumulative seconds of speech detected per source, for talk-ratio
    pub mic_speech_secs: Mutex<f32>,
    pub loopback_speech_secs: Mutex<f32>,
}

impl Default for AudioCaptureState {
    fn default() -> Self {
        Self {
            running: AtomicBool::new(false),
            chunks: Mutex::new(Vec::new()),
            mic_speech_secs: Mutex::new(0.0),
            loopback_speech_secs: Mutex::new(0.0),
        }
    }
}

/// Builds a cpal input stream for a given device.
/// `source_label` is "mic" or "loopback".
/// Captured audio is VAD-sliced and pushed into `state.chunks`.
fn build_capture_stream(
    device: &cpal::Device,
    source_label: &str,
    state: Arc<AudioCaptureState>,
) -> Result<(cpal::Stream, StreamConfig), String> {
    let supported = device
        .default_input_config()
        .map_err(|e| format!("No default config for {}: {}", source_label, e))?;

    let sample_format = supported.sample_format();
    let config: StreamConfig = supported.into();

    let channels = config.channels;
    let sample_rate = config.sample_rate.0;
    let label = source_label.to_string();

    let vad = Arc::new(Mutex::new(VadAccumulator::new(&label)));

    let speech_secs = state.clone();
    let state_for_stream = state.clone();
    let label_for_err = label.clone();

    let stream = match sample_format {
        SampleFormat::F32 => device.build_input_stream(
            &config,
            move |data: &[f32], _info| {
                if !state_for_stream.running.load(Ordering::Relaxed) {
                    return;
                }
                let mono_16k = to_mono_16k(data, channels, sample_rate);
                if let Ok(mut vad_lock) = vad.lock() {
                    if let Some(chunk) = vad_lock.feed(&mono_16k) {
                        // Track cumulative speech time
                        let secs_mutex = if label == "mic" {
                            &speech_secs.mic_speech_secs
                        } else {
                            &speech_secs.loopback_speech_secs
                        };
                        if let Ok(mut secs) = secs_mutex.lock() {
                            *secs += chunk.duration_secs;
                        }
                        if let Ok(mut chunks) = state_for_stream.chunks.lock() {
                            chunks.push(chunk);
                        }
                    }
                }
            },
            move |err| {
                log::error!("Audio stream error ({}): {}", label_for_err, err);
            },
            None,
        ),
        SampleFormat::I16 => {
            let vad_i16 = Arc::new(Mutex::new(VadAccumulator::new(&label)));
            let state_i16 = state.clone();
            let speech_secs_i16 = state.clone();
            let label_i16 = label.clone();
            let label_err_i16 = label.clone();
            device.build_input_stream(
                &config,
                move |data: &[i16], _info| {
                    if !state_i16.running.load(Ordering::Relaxed) {
                        return;
                    }
                    let f32_data: Vec<f32> =
                        data.iter().map(|&s| s as f32 / i16::MAX as f32).collect();
                    let mono_16k = to_mono_16k(&f32_data, channels, sample_rate);
                    if let Ok(mut vad_lock) = vad_i16.lock() {
                        if let Some(chunk) = vad_lock.feed(&mono_16k) {
                            let secs_mutex = if label_i16 == "mic" {
                                &speech_secs_i16.mic_speech_secs
                            } else {
                                &speech_secs_i16.loopback_speech_secs
                            };
                            if let Ok(mut secs) = secs_mutex.lock() {
                                *secs += chunk.duration_secs;
                            }
                            if let Ok(mut chunks) = state_i16.chunks.lock() {
                                chunks.push(chunk);
                            }
                        }
                    }
                },
                move |err| {
                    log::error!("Audio stream error ({}): {}", label_err_i16, err);
                },
                None,
            )
        }
        _ => {
            return Err(format!(
                "Unsupported sample format {:?} for {}",
                sample_format, source_label
            ));
        }
    }
    .map_err(|e| format!("Failed to build {} stream: {}", source_label, e))?;

    Ok((stream, config))
}

/// Lists all available audio input devices with their names.
pub fn list_input_devices() -> Vec<String> {
    let host = cpal::default_host();
    let mut names = Vec::new();
    if let Ok(devices) = host.input_devices() {
        for device in devices {
            if let Ok(name) = device.name() {
                names.push(name);
            }
        }
    }
    names
}

/// Lists all available audio output devices.
pub fn list_output_devices() -> Vec<String> {
    let host = cpal::default_host();
    let mut names = Vec::new();
    if let Ok(devices) = host.output_devices() {
        for device in devices {
            if let Ok(name) = device.name() {
                names.push(name);
            }
        }
    }
    names
}

/// Starts dual capture (mic + loopback). Returns the two cpal::Stream handles
/// which must be kept alive for the duration of capture.
///
/// On Windows (WASAPI), loopback capture is done by opening the default
/// output device as an input stream -- WASAPI exposes this automatically.
/// On macOS, CoreAudio aggregate devices or ScreenCaptureKit are needed;
/// this implementation captures the default output device which works
/// with loopback-capable drivers.
/// On Linux, PipeWire/PulseAudio monitor sources appear as input devices.
pub fn start_capture(
    state: Arc<AudioCaptureState>,
) -> Result<(cpal::Stream, cpal::Stream), String> {
    let host = cpal::default_host();

    // ── Microphone (default input device) ──
    let mic_device = host
        .default_input_device()
        .ok_or("No default input (microphone) device found")?;
    log::info!(
        "Mic device: {}",
        mic_device.name().unwrap_or_default()
    );

    let (mic_stream, mic_config) = build_capture_stream(&mic_device, "mic", state.clone())?;
    log::info!(
        "Mic stream: {}ch @ {}Hz",
        mic_config.channels,
        mic_config.sample_rate.0
    );

    // ── Loopback (default output device captured as input) ──
    //
    // Platform behavior:
    //   Windows (WASAPI): default_output_device supports build_input_stream
    //     for loopback capture natively.
    //   Linux: PipeWire/PulseAudio monitor sources show up as input devices.
    //     We try to find a "Monitor" device first, fall back to default output.
    //   macOS: Requires a loopback driver (e.g., BlackHole) or ScreenCaptureKit.
    //     We try default output; this works if a loopback driver is installed.
    let loopback_device = find_loopback_device(&host)
        .ok_or("No loopback/monitor audio device found. On Linux, ensure PipeWire or PulseAudio is running. On Windows, WASAPI loopback is used automatically. On macOS, a loopback audio driver is required.")?;

    log::info!(
        "Loopback device: {}",
        loopback_device.name().unwrap_or_default()
    );

    let (loopback_stream, loopback_config) =
        build_capture_stream(&loopback_device, "loopback", state.clone())?;
    log::info!(
        "Loopback stream: {}ch @ {}Hz",
        loopback_config.channels,
        loopback_config.sample_rate.0
    );

    // Mark running and start both streams
    state.running.store(true, Ordering::SeqCst);
    mic_stream.play().map_err(|e| format!("Mic play failed: {}", e))?;
    loopback_stream
        .play()
        .map_err(|e| format!("Loopback play failed: {}", e))?;

    Ok((mic_stream, loopback_stream))
}

/// Platform-aware loopback device finder.
fn find_loopback_device(host: &cpal::Host) -> Option<cpal::Device> {
    // On Linux, look for a PipeWire/PulseAudio monitor source first
    #[cfg(target_os = "linux")]
    {
        if let Ok(devices) = host.input_devices() {
            for device in devices {
                if let Ok(name) = device.name() {
                    let lower = name.to_lowercase();
                    if lower.contains("monitor") {
                        log::info!("Found Linux monitor source: {}", name);
                        return Some(device);
                    }
                }
            }
        }
    }

    // On Windows, WASAPI exposes loopback via the default output device
    // opened as an input stream. On macOS, this works if a loopback
    // driver is installed.
    #[cfg(any(target_os = "windows", target_os = "macos"))]
    {
        return host.default_output_device();
    }

    // Fallback for Linux: try default output device
    #[cfg(target_os = "linux")]
    {
        host.default_output_device()
    }
}

/// Stops capture by setting the running flag to false.
/// The Stream handles should be dropped by the caller to fully release devices.
pub fn stop_capture(state: &AudioCaptureState) {
    state.running.store(false, Ordering::SeqCst);
}

/// Drains all pending audio chunks from the shared state.
pub fn drain_chunks(state: &AudioCaptureState) -> Vec<AudioChunk> {
    if let Ok(mut chunks) = state.chunks.lock() {
        chunks.drain(..).collect()
    } else {
        Vec::new()
    }
}

/// Returns (mic_secs, loopback_secs) for talk-ratio calculation.
pub fn get_talk_ratio(state: &AudioCaptureState) -> (f32, f32) {
    let mic = state
        .mic_speech_secs
        .lock()
        .map(|s| *s)
        .unwrap_or(0.0);
    let loopback = state
        .loopback_speech_secs
        .lock()
        .map(|s| *s)
        .unwrap_or(0.0);
    (mic, loopback)
}
