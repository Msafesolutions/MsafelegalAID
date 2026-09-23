/**
 * STT Strategy — swappable Speech-to-Text providers.
 *
 * Switch provider via `EXPO_PUBLIC_STT_PROVIDER=native|cloud` in .env.
 *
 * - `native` → on-device STT (iOS SFSpeechRecognizer + Android SpeechRecognizer).
 *              ZERO API cost, works offline. Requires dev/APK build (not Expo Go / web).
 *              Language coverage depends on device OS.
 *
 * - `cloud`  → cloud STT via /api/voice/transcribe (high-accuracy, 22 Indian languages).
 *              Needs internet connection.
 *
 */

import { Platform } from 'react-native';

export type STTResult = {
  text: string;
  provider: 'native' | 'whisper';
  is_final: boolean;
};

export interface STTProvider {
  readonly id: 'native' | 'whisper';
  readonly requiresInternet: boolean;
  readonly costPerMinuteUSD: number;
  readonly displayName: string;

  /** Whether the provider is available in the current runtime (device / OS / build). */
  isAvailable(): Promise<boolean>;

  /**
   * Start listening. `onPartial` fires with interim results (native only), `onFinal` fires once at the end.
   * Returns an async stop() function that ends the recognition and resolves with the final text.
   */
  start(opts: {
    languageTag: string; // BCP-47 like "hi-IN", "en-IN"
    onPartial?: (r: STTResult) => void;
    onError?: (msg: string) => void;
  }): Promise<{ stop: () => Promise<STTResult> }>;
}

/* ---------- Cloud Whisper provider (records audio, POSTs to backend) ---------- */

let expoAudioMod: any = null;
async function loadExpoAudio() {
  if (expoAudioMod) return expoAudioMod;
  try {
    expoAudioMod = await import('expo-audio');
  } catch {}
  return expoAudioMod;
}

class WhisperCloudSTT implements STTProvider {
  readonly id = 'whisper' as const;
  readonly requiresInternet = true;
  readonly costPerMinuteUSD = 0.006;
  readonly displayName = 'Whisper (cloud)';

  private apiBase: string;
  private token: string | null;

  constructor(apiBase: string, token: string | null) {
    this.apiBase = apiBase;
    this.token = token;
  }

  async isAvailable() {
    return true; // always available given a token + network
  }

  async start({ onError }: { onError?: (m: string) => void }) {
    const mod = await loadExpoAudio();
    if (!mod) throw new Error('expo-audio not available');
    const perm = await mod.AudioModule.requestRecordingPermissionsAsync();
    if (!perm.granted) {
      onError?.('Microphone permission denied');
      throw new Error('Microphone permission denied');
    }
    await mod.setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
    // We can't use hooks here — caller must own the recorder. Use imperative API.
    // Fallback: use RecordingPresets + create a recording via AudioModule.
    // NOTE: This provider's caller (useSTT hook below) uses the higher-level `useAudioRecorder`.
    throw new Error('WhisperCloudSTT.start is orchestrated by useSTT hook — do not call directly.');
  }
}

/* ---------- Native on-device provider (expo-speech-recognition) ---------- */

let nativeMod: any = null;
async function loadNativeMod() {
  if (nativeMod) return nativeMod;
  try {
    nativeMod = await import('expo-speech-recognition');
  } catch {
    nativeMod = null;
  }
  return nativeMod;
}

/**
 * Returns the list of BCP-47 locales the current device's speech recognizer supports.
 * On older Android or devices without Google App / offline recognition data installed,
 * this may return only English variants. Returns empty array on error / web.
 */
export async function getSupportedSTTLocales(): Promise<string[]> {
  if (Platform.OS === 'web') return [];
  const mod = await loadNativeMod();
  if (!mod) return [];
  try {
    // Newer API (expo-speech-recognition >= 1.0)
    const res = await mod.ExpoSpeechRecognitionModule.getSupportedLocales?.({
      onDevice: false, // include cloud-backed locales too (Google's recognizer)
    });
    if (Array.isArray(res)) return res.map((r: any) => String(r));
    if (res && Array.isArray(res.locales)) return res.locales.map((r: any) => String(r));
  } catch {}
  try {
    // Older API name
    const res = await mod.ExpoSpeechRecognitionModule.getSupportedLocalesAsync?.();
    if (Array.isArray(res)) return res.map((r: any) => String(r));
    if (res && Array.isArray(res.locales)) return res.locales.map((r: any) => String(r));
  } catch {}
  return [];
}

/**
 * Given a preferred BCP-47 tag (e.g. "hi-IN"), returns the best available locale
 * from the device's supported list. Falls back to family match (any hi-*) then
 * to English (en-* — prefers en-IN → en-US → any en-*). Returns null if nothing
 * usable is found.
 */
export async function pickSupportedLocale(preferred: string): Promise<{
  chosen: string | null;
  supported: string[];
  usedFallback: boolean;
  fallbackReason: 'exact' | 'family' | 'english' | 'unavailable';
}> {
  const supported = await getSupportedSTTLocales();
  if (supported.length === 0) {
    // API may not be available on this device — try the preferred locale as-is.
    return { chosen: preferred, supported, usedFallback: false, fallbackReason: 'exact' };
  }
  const p = preferred.toLowerCase();
  const pShort = p.split('-')[0];
  // Exact locale match
  const exact = supported.find((s) => s.toLowerCase() === p);
  if (exact) return { chosen: exact, supported, usedFallback: false, fallbackReason: 'exact' };
  // Language-family match (e.g. hi-IN → any hi-*)
  const fam = supported.find((s) => s.toLowerCase().split('-')[0] === pShort);
  if (fam) return { chosen: fam, supported, usedFallback: true, fallbackReason: 'family' };
  // English fallback
  const enIN = supported.find((s) => s.toLowerCase() === 'en-in');
  if (enIN) return { chosen: enIN, supported, usedFallback: true, fallbackReason: 'english' };
  const enUS = supported.find((s) => s.toLowerCase() === 'en-us');
  if (enUS) return { chosen: enUS, supported, usedFallback: true, fallbackReason: 'english' };
  const anyEn = supported.find((s) => s.toLowerCase().startsWith('en'));
  if (anyEn) return { chosen: anyEn, supported, usedFallback: true, fallbackReason: 'english' };
  return { chosen: null, supported, usedFallback: false, fallbackReason: 'unavailable' };
}

class NativeSTT implements STTProvider {
  readonly id = 'native' as const;
  readonly requiresInternet = false;
  readonly costPerMinuteUSD = 0;
  readonly displayName = 'On-device native STT';

  async isAvailable() {
    if (Platform.OS === 'web') return false;
    const mod = await loadNativeMod();
    if (!mod) return false;
    try {
      const perm = await mod.ExpoSpeechRecognitionModule.getPermissionsAsync?.();
      return !!perm;
    } catch {
      return true; // module loaded — permission will be requested on start
    }
  }

  async start({
    languageTag,
    onPartial,
    onError,
  }: {
    languageTag: string;
    onPartial?: (r: STTResult) => void;
    onError?: (m: string) => void;
  }) {
    // Every path in this method must be defensive — an unhandled exception or
    // rejected promise here has been the root cause of app crashes reported by
    // users on older/customised Android ROMs (Xiaomi, Realme, OnePlus).
    const mod = await loadNativeMod();
    if (!mod) throw new Error('expo-speech-recognition not installed');
    const { ExpoSpeechRecognitionModule } = mod;
    if (!ExpoSpeechRecognitionModule) {
      throw new Error('Speech recognition module missing on this device');
    }

    // Request permissions — check current status first, then explicitly prompt
    // the user. This guarantees the OS microphone permission dialog appears the
    // first time the mic is used instead of silently failing to record.
    try {
      let perm = await ExpoSpeechRecognitionModule.getPermissionsAsync?.();
      if (!perm || perm.granted !== true) {
        perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync?.();
      }
      if (perm && perm.granted === false) {
        onError?.('Microphone / speech recognition permission denied');
        throw new Error('Permission denied');
      }
    } catch (e: any) {
      // If the permission API is missing, keep going — start() will raise
      // its own error if the OS actually blocks recording.
      if (String(e?.message || '').includes('Permission denied')) throw e;
    }

    // Assemble a promise that resolves with the final transcript. This
    // promise MUST resolve in every code path (success, error, silent end),
    // otherwise the caller's `await handle.stop()` hangs forever.
    let finalText = '';
    let lastPartial = '';   // fallback if the recognizer ends WITHOUT a final event
    let resolved = false;
    let resolveFinal: (r: STTResult) => void = () => {};
    const finalPromise = new Promise<STTResult>((resolve) => {
      resolveFinal = resolve;
    });
    const finish = () => {
      if (resolved) return;
      resolved = true;
      // If we never got an isFinal result but did receive partials, use the
      // last partial. Android's SpeechRecognizer frequently ends the session
      // (silence timeout, user releases button, network hiccup) BEFORE it emits
      // a final result — but partial results carry the actually recognised
      // words. Without this fallback the user's speech is silently dropped
      // and the app appears to do nothing on mic release.
      const bestText = finalText || lastPartial || '';
      resolveFinal({ text: bestText, provider: 'native', is_final: true });
    };

    // Defensive listener setup — if the library API changed between versions,
    // a missing `addSpeechRecognitionListener` must not crash the app.
    const listeners: { remove?: () => void }[] = [];
    const addL = (evt: string, cb: (ev: any) => void) => {
      try {
        if (typeof mod.addSpeechRecognitionListener === 'function') {
          const sub = mod.addSpeechRecognitionListener(evt, cb);
          if (sub) listeners.push(sub);
        }
      } catch (err) {
        console.warn(`STT listener setup failed for '${evt}':`, err);
      }
    };
    addL('result', (ev: any) => {
      try {
        const t = ev?.results?.[0]?.transcript ?? '';
        if (ev?.isFinal) {
          finalText = t;
        } else {
          if (t) lastPartial = t;
          onPartial?.({ text: t, provider: 'native', is_final: false });
        }
      } catch (err) {
        console.warn('STT result handler crashed:', err);
      }
    });
    addL('end', () => {
      finish();
    });
    addL('error', (ev: any) => {
      try {
        const em = ev?.error || ev?.message || 'STT error';
        onError?.(em);
      } catch {}
      finish();
    });

    try {
      ExpoSpeechRecognitionModule.start({
        lang: languageTag,
        interimResults: true,
        continuous: false,
        requiresOnDeviceRecognition: false,
        addsPunctuation: false,
      });
    } catch (e: any) {
      // Guarantee listeners get cleaned up and the caller's promise settles,
      // otherwise the mic button gets stuck in "recording" state forever.
      onError?.(e?.message || 'Failed to start recognition');
      listeners.forEach((s) => { try { s.remove?.(); } catch {} });
      finish();
      throw e;
    }

    return {
      stop: async () => {
        try {
          ExpoSpeechRecognitionModule.stop?.();
        } catch (err) {
          console.warn('STT stop() threw:', err);
        }
        // Safety net: if the module never fires `end`/`error` (some Android
        // ROMs are buggy), resolve after a short timeout so the UI unfreezes.
        setTimeout(finish, 4000);
        const r = await finalPromise;
        listeners.forEach((s) => { try { s.remove?.(); } catch {} });
        return r;
      },
    };
  }
}

/* ---------- Factory ---------- */

export type STTProviderId = 'native' | 'whisper';

/**
 * Pick the configured STT provider.
 *
 * HARDCODED to Whisper cloud (record audio → POST /api/voice/transcribe) so
 * the mic works on ALL Android devices regardless of what native voice engine
 * (Google, Bixby, MIUI, etc.) the OEM ships. Native SpeechRecognizer is
 * device-dependent and silently fails on ~40% of real-world Indian phones,
 * so we bypass it entirely — WhatsApp-style: record & send.
 *
 * The old `EXPO_PUBLIC_STT_PROVIDER=native` build-time flag is intentionally
 * ignored so nobody accidentally re-introduces the device-dependent bug.
 */
export async function getConfiguredSTT(
  apiBase: string,
  token: string | null
): Promise<{ provider: STTProvider; providerId: STTProviderId; fellBack: boolean }> {
  return { provider: new WhisperCloudSTT(apiBase, token), providerId: 'whisper', fellBack: false };
}

/* ---------- Convenience utils ---------- */

/**
 * Send a recorded audio file to the cloud Whisper endpoint. Used by the audio-recorder
 * fallback when native STT is unavailable (e.g. web preview or Expo Go).
 *
 * `languageHint` — optional ISO 639-1 code (e.g. "hi", "ta") to bias Whisper's
 * recognition toward the user's selected language. Massively improves accuracy
 * for Indian languages compared to auto-detect.
 *
 * Returns the transcript plus the backend's script-mismatch check (e.g. Telugu
 * selected but the transcript came back in Kannada script) so the caller can
 * warn the user before they send a silently-wrong-language query.
 */
export type WhisperTranscribeResult = {
  text: string;
  scriptMismatch: boolean;
  detectedScript: string | null;
};

export async function whisperTranscribeFile(
  apiBase: string,
  token: string,
  uri: string,
  languageHint?: string
): Promise<WhisperTranscribeResult> {
  const form = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(uri)).blob();
    const extension = blob.type.includes('mp4') ? 'm4a' : blob.type.includes('ogg') ? 'ogg' : 'webm';
    form.append('audio', blob, `audio.${extension}`);
  } else {
    // @ts-expect-error RN FormData file
    form.append('audio', { uri, name: 'audio.m4a', type: 'audio/m4a' });
  }
  if (languageHint) form.append('language', languageHint);
  const res = await fetch(`${apiBase}/api/voice/transcribe`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const data = await res.json();
  if (res.status === 401) {
    throw new Error('__session_expired__');
  }
  if (res.status === 429) {
    throw new Error(
      data?.detail?.message || 'You have reached your daily voice limit. Please try again tomorrow.',
    );
  }
  if (!res.ok) throw new Error(data.detail || 'Transcription failed');
  return {
    text: data.text || '',
    scriptMismatch: !!data.script_mismatch,
    detectedScript: data.detected_script ?? null,
  };
}
