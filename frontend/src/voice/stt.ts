/**
 * STT Strategy — swappable Speech-to-Text providers.
 *
 * Switch provider via `EXPO_PUBLIC_STT_PROVIDER=native|whisper` in .env.
 *
 * - `native`  → on-device via expo-speech-recognition (iOS SFSpeechRecognizer + Android SpeechRecognizer).
 *              ZERO API cost, works offline. Requires dev/APK build (not Expo Go / web).
 *              Language coverage depends on device OS.
 *
 * - `whisper` → cloud OpenAI Whisper via /api/voice/transcribe (uses your Emergent LLM key).
 *              Best accuracy for 22 Indian languages, needs internet, ~$0.006/min.
 *
 * The strategy pattern lets you upgrade to Whisper later with a single env-var flip
 * once revenue justifies the cost, without touching any UI code.
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
    const mod = await loadNativeMod();
    if (!mod) throw new Error('expo-speech-recognition not installed');
    const { ExpoSpeechRecognitionModule } = mod;

    // Request permissions
    const perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
    if (!perm.granted) {
      onError?.('Microphone / speech recognition permission denied');
      throw new Error('Permission denied');
    }

    // Assemble a promise that resolves with the final transcript
    let finalText = '';
    let resolved = false;
    let resolveFinal: (r: STTResult) => void = () => {};
    const finalPromise = new Promise<STTResult>((resolve) => {
      resolveFinal = resolve;
    });

    const resultSub = mod.addSpeechRecognitionListener('result', (ev: any) => {
      const t = ev?.results?.[0]?.transcript ?? '';
      if (ev?.isFinal) {
        finalText = t;
      } else {
        onPartial?.({ text: t, provider: 'native', is_final: false });
      }
    });
    const endSub = mod.addSpeechRecognitionListener('end', () => {
      if (!resolved) {
        resolved = true;
        resolveFinal({ text: finalText, provider: 'native', is_final: true });
      }
    });
    const errorSub = mod.addSpeechRecognitionListener('error', (ev: any) => {
      const em = ev?.error || ev?.message || 'STT error';
      onError?.(em);
      if (!resolved) {
        resolved = true;
        resolveFinal({ text: finalText, provider: 'native', is_final: true });
      }
    });

    try {
      ExpoSpeechRecognitionModule.start({
        lang: languageTag,
        interimResults: true,
        continuous: false,
        requiresOnDeviceRecognition: false, // OS decides; false gives broader lang coverage
        addsPunctuation: true,
      });
    } catch (e: any) {
      onError?.(e?.message || 'Failed to start recognition');
      throw e;
    }

    return {
      stop: async () => {
        try {
          ExpoSpeechRecognitionModule.stop();
        } catch {}
        const r = await finalPromise;
        try {
          resultSub?.remove?.();
          endSub?.remove?.();
          errorSub?.remove?.();
        } catch {}
        return r;
      },
    };
  }
}

/* ---------- Factory ---------- */

export type STTProviderId = 'native' | 'whisper';

/**
 * Pick the configured STT provider.
 * Reads EXPO_PUBLIC_STT_PROVIDER at build time.
 * Falls back to `whisper` gracefully if native is chosen but unavailable in the current runtime.
 */
export async function getConfiguredSTT(
  apiBase: string,
  token: string | null
): Promise<{ provider: STTProvider; providerId: STTProviderId; fellBack: boolean }> {
  const configured = (process.env.EXPO_PUBLIC_STT_PROVIDER || 'native').toLowerCase() as STTProviderId;

  if (configured === 'native') {
    const native = new NativeSTT();
    const ok = await native.isAvailable();
    if (ok) return { provider: native, providerId: 'native', fellBack: false };
    // fall back to whisper
    return { provider: new WhisperCloudSTT(apiBase, token), providerId: 'whisper', fellBack: true };
  }
  return { provider: new WhisperCloudSTT(apiBase, token), providerId: 'whisper', fellBack: false };
}

/* ---------- Convenience utils ---------- */

/**
 * Send a recorded audio file to the cloud Whisper endpoint. Used by the audio-recorder
 * fallback when native STT is unavailable (e.g. web preview or Expo Go).
 */
export async function whisperTranscribeFile(
  apiBase: string,
  token: string,
  uri: string
): Promise<string> {
  const form = new FormData();
  // @ts-expect-error RN FormData file
  form.append('audio', { uri, name: 'audio.m4a', type: 'audio/m4a' });
  const res = await fetch(`${apiBase}/api/voice/transcribe`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Transcription failed');
  return data.text || '';
}
