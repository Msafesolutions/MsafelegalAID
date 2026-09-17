/**
 * Native device TTS — free Indian accent voices.
 *
 * Uses the device's built-in speech engine so there is NO cloud round-trip
 * and no API credits are consumed.
 *
 *  • Web  : window.speechSynthesis — prefers an en-IN / te-IN / kn-IN voice
 *           when one is installed; falls back gracefully to the default voice
 *           with the correct lang tag so the OS still applies an Indian cadence.
 *  • Native: expo-speech — same lang tags and pitch offsets.
 *
 * Gender is simulated by adjusting pitch only (device voices are mono-gender
 * per locale on most Android / iOS installs; we pick the best available and
 * nudge the pitch so the user can tell female from male).
 */
import * as Speech from 'expo-speech';
import { Platform } from 'react-native';

export type VoiceGender = 'female' | 'male';

/** BCP-47 map: our short codes → Indian locale tags. */
const LOCALE_MAP: Record<string, string> = {
  en: 'en-IN',
  te: 'te-IN',
  kn: 'kn-IN',
  hi: 'hi-IN',
  mr: 'mr-IN',
  ta: 'ta-IN',
  ml: 'ml-IN',
  bn: 'bn-IN',
  gu: 'gu-IN',
  pa: 'pa-IN',
  or: 'or-IN',
  as: 'as-IN',
};

function toBCP47(langCode: string): string {
  return LOCALE_MAP[langCode] ?? `${langCode}-IN`;
}

// ─── Web ─────────────────────────────────────────────────────────────────────

function speakWeb(
  text: string,
  bcp47: string,
  gender: VoiceGender,
  onDone?: () => void,
): void {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    onDone?.();
    return;
  }

  window.speechSynthesis.cancel();

  const utter = new SpeechSynthesisUtterance(text);
  utter.lang  = bcp47;
  utter.rate  = 0.88;
  // Female: slightly higher pitch; Male: slightly lower
  utter.pitch = gender === 'female' ? 1.18 : 0.82;

  const pickAndSpeak = () => {
    const voices = window.speechSynthesis.getVoices();
    // 1st choice: exact locale match
    // 2nd choice: same language family (e.g. en-GB for en-IN fallback)
    // 3rd choice: no filter — use OS default with the lang tag set
    const langBase = bcp47.split('-')[0];
    const best =
      voices.find((v) => v.lang === bcp47) ??
      voices.find((v) => v.lang.startsWith(langBase + '-IN')) ??
      voices.find((v) => v.lang.startsWith(langBase));

    if (best) utter.voice = best;
    utter.onend   = () => onDone?.();
    utter.onerror = () => onDone?.();
    window.speechSynthesis.speak(utter);
  };

  // getVoices() is populated asynchronously on Chrome / Edge
  const voices = window.speechSynthesis.getVoices();
  if (voices.length > 0) {
    pickAndSpeak();
  } else {
    window.speechSynthesis.addEventListener('voiceschanged', pickAndSpeak, { once: true });
  }
}

// ─── Native ───────────────────────────────────────────────────────────────────

async function speakMobile(
  text: string,
  bcp47: string,
  gender: VoiceGender,
  onDone?: () => void,
): Promise<void> {
  try {
    await Speech.stop();
    Speech.speak(text, {
      language: bcp47,
      pitch:    gender === 'female' ? 1.15 : 0.88,
      rate:     0.88,
      onDone:   onDone,
      onError:  () => onDone?.(),
    });
  } catch {
    onDone?.();
  }
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Speak `text` using the device's native TTS engine.
 *
 * @param text    The text to speak.
 * @param lang    Short language code from the app's language store (e.g. 'en', 'te').
 * @param gender  'female' (default) or 'male' — adjusts pitch.
 * @param onDone  Called once speech finishes or errors.
 */
export function speakNative(
  text: string,
  lang = 'en',
  gender: VoiceGender = 'female',
  onDone?: () => void,
): void {
  const bcp47 = toBCP47(lang);
  if (Platform.OS === 'web') {
    speakWeb(text, bcp47, gender, onDone);
  } else {
    speakMobile(text, bcp47, gender, onDone);
  }
}

/** Stop any in-progress native TTS immediately. */
export function stopNativeTTS(): void {
  if (Platform.OS === 'web') {
    try { window.speechSynthesis?.cancel(); } catch {}
  } else {
    Speech.stop().catch(() => {});
  }
}
