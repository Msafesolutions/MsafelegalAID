import { useState, useRef, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ScrollView,
  Platform,
  ActivityIndicator,
  Alert,
  Modal,
  Switch,
} from 'react-native';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  createAudioPlayer,
  type AudioPlayer,
} from 'expo-audio';
import { File, Paths } from 'expo-file-system';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';
import { getConfiguredSTT, whisperTranscribeFile } from '@/src/voice/stt';
import { SOSButton } from '@/src/components/SOSButton';

type Citation = {
  key: string;
  citation: string;
  short_label: string;
  act: string;
  official_text: string;
  source_url: string;
  verified_at: string;
};

type Msg = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  mode?: 'basic' | 'pro';
  citations?: Citation[];
};

const BASIC_SUGGESTIONS: { text: string; icon: React.ComponentProps<typeof Ionicons>['name'] }[] = [
  { text: 'What is the RTI application fee and word limit?', icon: 'document-text-outline' },
  { text: 'Can Amazon charge me a cancellation fee?', icon: 'cart-outline' },
  { text: 'Must rear-seat passengers wear seat belts?', icon: 'car-outline' },
  { text: 'What is the helmet law for a child on a bike?', icon: 'shield-checkmark-outline' },
];

const PRO_SUGGESTIONS: { text: string; icon: React.ComponentProps<typeof Ionicons>['name'] }[] = [
  { text: 'Draft a first appeal for an unanswered RTI', icon: 'create-outline' },
  { text: 'Step-by-step complaint against a defective online product', icon: 'list-outline' },
  { text: 'Draft an RTI asking for a certified FIR copy', icon: 'file-tray-outline' },
  { text: 'Full escalation path for a domestic violence case', icon: 'trending-up-outline' },
];

export default function ChatScreen() {
  const { token, user, language, model, autoSpeak, refreshUser } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [proMode, setProMode] = useState(false);
  const [paywall, setPaywall] = useState<null | {
    samples_used: number;
    samples_limit: number;
    pro_price_label: string;
    pro_price_usd_label: string;
    message: string;
  }>(null);
  const [samplesRemaining, setSamplesRemaining] = useState<number | null>(null);
  const [, setSttProviderLabel] = useState<string>('');
  // WhatsApp-style voice UX state
  const [transcriptPreview, setTranscriptPreview] = useState<string>('');
  const [showTranscriptModal, setShowTranscriptModal] = useState<boolean>(false);
  const [holdElapsed, setHoldElapsed] = useState<number>(0);
  // TTS playback speed — cycles 1x → 1.5x → 2x → back
  const [speechRate, setSpeechRate] = useState<number>(1.0);
  const holdTimerRef = useRef<any>(null);
  const scrollRef = useRef<ScrollView>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const nativeSTTHandleRef = useRef<{ stop: () => Promise<any> } | null>(null);
  // Race-condition guard: onPressIn is synchronous, startRecording is async.
  // If the user releases the mic BEFORE the async permission/init finishes,
  // the onPressOut closure captures a stale `recording === false` and misses
  // stopping the recording, which then runs silently forever ("loop" bug).
  // This ref is set synchronously on press-in/out and consulted throughout
  // the async flow so we always know the user's current intent.
  const isMicHeldRef = useRef<boolean>(false);
  // Cloud TTS player + cleanup — we lazily create an AudioPlayer per playback
  // and keep the ref so we can stop it (user taps stop / speaks another
  // message / navigates away).
  const ttsPlayerRef = useRef<AudioPlayer | null>(null);
  const ttsPlayerReleaseTimerRef = useRef<any>(null);
  // Mirror `speakingId` in a ref so async cleanup callbacks can see the
  // latest value without stale-closure issues.
  const speakingIdRef = useRef<string | null>(null);
  useEffect(() => {
    speakingIdRef.current = speakingId;
  }, [speakingId]);
  // Forward-declared ref to `speak` so auto-speak logic inside `send` can call it
  // without a circular dependency (speak is defined AFTER send in this file).
  const speakRef = useRef<((msgId: string, text: string) => void) | null>(null);

  // Global unmount cleanup — critical for preventing app crashes when the user
  // navigates away while the mic is still recording. Without this, the STT
  // module keeps a live audio input stream that the OS eventually kills with
  // a native exception (which manifests as "Something went wrong with Msafe
  // DHARA" on some Android ROMs).
  useEffect(() => {
    return () => {
      // Stop any active STT handle
      if (nativeSTTHandleRef.current) {
        try {
          nativeSTTHandleRef.current.stop();
        } catch {}
        nativeSTTHandleRef.current = null;
      }
      // Kill the hold-to-talk elapsed-time interval
      if (holdTimerRef.current) {
        clearInterval(holdTimerRef.current);
        holdTimerRef.current = null;
      }
      // Stop any ongoing cloud TTS playback
      try {
        const p = ttsPlayerRef.current;
        if (p) {
          try { p.pause(); } catch {}
          try { p.remove(); } catch {}
        }
      } catch {}
      ttsPlayerRef.current = null;
      if (ttsPlayerReleaseTimerRef.current) {
        clearTimeout(ttsPlayerReleaseTimerRef.current);
        ttsPlayerReleaseTimerRef.current = null;
      }
    };
  }, []);

  const isPro = !!user?.is_pro;
  const remaining =
    samplesRemaining !== null
      ? samplesRemaining
      : (user?.pro_samples_remaining ?? user?.pro_samples_limit ?? 5);

  // Configure audio mode for playback
  useEffect(() => {
    (async () => {
      try {
        if (Platform.OS !== 'web') {
          await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
        }
      } catch {}
    })();
    return () => {
      // Cloud TTS cleanup handled by the earlier unmount effect above.
    };
  }, []);

  const send = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q || streaming || !token) return;
      const userId = Math.random().toString(36).slice(2);
      const assistantId = Math.random().toString(36).slice(2);
      const modeToSend: 'basic' | 'pro' = proMode ? 'pro' : 'basic';
      setMessages((prev) => [
        ...prev,
        { id: userId, role: 'user', content: q },
        { id: assistantId, role: 'assistant', content: '', mode: modeToSend },
      ]);
      setInput('');
      setStreaming(true);

      try {
        const res = await fetch(`${API_BASE}/api/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            message: q,
            session_id: sessionId,
            language: language.code,
            language_name: language.name,
            language_native: language.native,
            model_provider: model.provider,
            model_name: model.name,
            mode: modeToSend,
          }),
        });

        // Paywall (HTTP 402) — pro-mode sample quota exhausted
        if (res.status === 402) {
          const body = await res.json();
          const pw = body?.detail || body;
          setPaywall({
            samples_used: pw.samples_used,
            samples_limit: pw.samples_limit,
            pro_price_label: pw.pro_price_label,
            pro_price_usd_label: pw.pro_price_usd_label,
            message: pw.message,
          });
          setMessages((prev) => prev.filter((m) => m.id !== assistantId && m.id !== userId));
          return;
        }

        if (!res.ok) {
          // Never render raw response bodies. Show a sanitized human message.
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: 'Something went wrong. Please try again.' }
                : m
            )
          );
          return;
        }

        /**
         * Parse SSE frames. Handles: session (control), citation (verified source),
         * delta (streaming text), final (sanitized full text — overwrites), error.
         * Only text-bearing frames update the UI. Metadata frames are handled internally.
         */
        const parseSseBuffer = (
          buf: string,
          prevAcc: string,
          prevFinal: string | null,
          prevCitations: Citation[],
        ): {
          acc: string;
          final: string | null;
          citations: Citation[];
          rest: string;
          hadError: boolean;
        } => {
          let acc = prevAcc;
          let finalText = prevFinal;
          let citations = [...prevCitations];
          let hadError = false;
          const parts = buf.split('\n\n');
          const rest = parts.pop() || '';
          for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed.startsWith('data:')) continue;
            const jsonStr = trimmed.slice(5).trim();
            if (!jsonStr) continue;
            let payload: any;
            try {
              payload = JSON.parse(jsonStr);
            } catch {
              continue;
            }
            if (!payload || typeof payload !== 'object' || !('type' in payload)) continue;
            switch (payload.type) {
              case 'session':
                if (payload.session_id) setSessionId(payload.session_id);
                if (typeof payload.samples_remaining_after === 'number') {
                  setSamplesRemaining(payload.samples_remaining_after);
                }
                break;
              case 'citation':
                if (payload.citation && typeof payload.citation === 'object') {
                  citations.push(payload.citation as Citation);
                }
                break;
              case 'delta':
                if (typeof payload.content === 'string') acc += payload.content;
                break;
              case 'final':
                // Sanitized full text — overwrites any accumulated delta output.
                if (typeof payload.content === 'string') finalText = payload.content;
                break;
              case 'error':
                hadError = true;
                break;
              default:
                break;
            }
          }
          return { acc, final: finalText, citations, rest, hadError };
        };

        // Native React Native fetch returns res.body === null (no streaming).
        // Web fetch returns a ReadableStream. Handle both.
        const canStream = !!(res.body && typeof (res.body as any).getReader === 'function');

        let acc = '';
        let finalText: string | null = null;
        let citations: Citation[] = [];
        let hadError = false;

        try {
          if (canStream) {
            const reader = (res.body as any).getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });
              const parsed = parseSseBuffer(buffer, acc, finalText, citations);
              acc = parsed.acc;
              finalText = parsed.final;
              citations = parsed.citations;
              buffer = parsed.rest;
              if (parsed.hadError) hadError = true;
              const displayText = finalText !== null ? finalText : acc;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: displayText, citations } : m,
                ),
              );
              scrollRef.current?.scrollToEnd({ animated: true });
            }
            if (buffer.trim()) {
              const parsed = parseSseBuffer(buffer + '\n\n', acc, finalText, citations);
              acc = parsed.acc;
              finalText = parsed.final;
              citations = parsed.citations;
              if (parsed.hadError) hadError = true;
            }
          } else {
            // React Native path: read the full response and parse all frames at once.
            const fullText = await res.text();
            const parsed = parseSseBuffer(fullText + '\n\n', '', null, []);
            acc = parsed.acc;
            finalText = parsed.final;
            citations = parsed.citations;
            hadError = parsed.hadError;
          }
        } catch {
          hadError = true;
        }

        const displayText = finalText !== null ? finalText : acc;

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: displayText.trim().length
                    ? displayText
                    : (hadError
                        ? 'Something went wrong. Please try again.'
                        : 'No response received. Please try again.'),
                  citations,
                }
              : m,
          ),
        );

        // Auto-speak the reply if the user has that setting on and we got real text
        if (autoSpeak && displayText.trim().length && !hadError) {
          // slight delay so the message renders before speech starts
          setTimeout(() => {
            speakRef.current?.(assistantId, displayText);
          }, 250);
        }

        try {
          await refreshUser();
        } catch {}
      } catch {
        // Never render raw errors, stream contents, or JSON to the user.
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: 'Network error. Please check your connection and try again.' }
              : m
          )
        );
      } finally {
        setStreaming(false);
      }
    },
    [streaming, token, sessionId, language, model, proMode, refreshUser, autoSpeak]
  );

  /**
   * Cloud TTS via /api/voice/tts. Records audio bytes returned by the backend
   * (which uses OpenAI TTS through the Emergent LLM Key) into a temp cache
   * file, then plays it back with expo-audio. Works on ALL devices — no OS
   * voice pack required. This is the "WhatsApp-style" fix for the fact that
   * on-device expo-speech silently no-ops on many Android OEMs (Samsung,
   * Xiaomi, etc.) that ship non-Google TTS engines by default.
   */
  const stopCloudTTS = useCallback(() => {
    // Debounce / cleanup helper for the AudioPlayer ref.
    try {
      const p = ttsPlayerRef.current;
      if (p) {
        try { p.pause(); } catch {}
        try { p.remove(); } catch {}
      }
    } catch {}
    ttsPlayerRef.current = null;
    if (ttsPlayerReleaseTimerRef.current) {
      clearTimeout(ttsPlayerReleaseTimerRef.current);
      ttsPlayerReleaseTimerRef.current = null;
    }
    setSpeakingId(null);
  }, []);

  const speak = useCallback(
    async (msgId: string, text: string) => {
      // Toggle: tapping speaker of currently-speaking message stops playback
      if (speakingId === msgId) {
        stopCloudTTS();
        return;
      }
      // Any other playback → stop it first
      stopCloudTTS();

      if (!text || !text.trim() || !token) return;

      // Force iOS silent-switch playback and disable recording-mode conflicts
      try {
        if (Platform.OS !== 'web') {
          await setAudioModeAsync({
            playsInSilentMode: true,
            allowsRecording: false,
            shouldPlayInBackground: false,
          });
        }
      } catch {}

      setSpeakingId(msgId);

      try {
        // 1. Ask backend to synthesise speech (OpenAI TTS → MP3 bytes)
        const res = await fetch(`${API_BASE}/api/voice/tts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            text: text.slice(0, 3800), // safety cap; backend also truncates
            language: language?.code || 'en',
            voice: 'alloy',
          }),
        });
        if (!res.ok) {
          const errTxt = await res.text().catch(() => '');
          throw new Error(`TTS server returned ${res.status}: ${errTxt.slice(0, 120)}`);
        }
        // 2. Read the MP3 payload as a base64 string so we can persist it to
        // a temp file without pulling in a Blob polyfill.
        const arrayBuf = await res.arrayBuffer();
        if (!arrayBuf || arrayBuf.byteLength === 0) {
          throw new Error('TTS server returned empty audio.');
        }
        // Convert ArrayBuffer → base64 without depending on Buffer / btoa
        // (RN's global.btoa exists on newer versions but is inconsistent).
        const bytes = new Uint8Array(arrayBuf);
        let bin = '';
        const CHUNK = 0x8000;
        for (let i = 0; i < bytes.length; i += CHUNK) {
          bin += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + CHUNK)) as any);
        }
        const g: any = globalThis;
        const b64 = g.btoa
          ? g.btoa(bin)
          : Buffer.from(bin, 'binary').toString('base64');

        // 3. Persist to the app cache directory (auto-cleared by OS)
        const file = new File(Paths.cache, `dhara-tts-${Date.now()}.mp3`);
        // File may already exist from a very rapid double-tap — safe overwrite
        try { file.delete(); } catch {}
        file.create();
        file.write(b64, { encoding: 'base64' });

        // 4. Race guard: user may have tapped stop / played something else
        // while we were awaiting the network + disk write. If the state has
        // moved on, silently discard this playback.
        if (msgId !== speakingIdRef.current) {
          try { file.delete(); } catch {}
          return;
        }

        // 5. Create the player, wire up load-readiness + completion handling.
        //
        // KNOWN RACE CONDITION (github.com/expo/expo/discussions/18869):
        // calling player.play() immediately after createAudioPlayer() can
        // silently no-op on some Android OEMs because the native player has
        // not finished decoding the source yet. This is the root cause of
        // the "sound sometimes plays, sometimes doesn't" bug reported in
        // the built APK. Fix: only call play() once the player reports
        // isLoaded === true (via the status event, or immediately if it is
        // already true), with a short hard-fallback timer as a safety net.
        const player = createAudioPlayer({ uri: file.uri });
        ttsPlayerRef.current = player;
        try {
          player.setPlaybackRate(speechRate, 'high');
        } catch {}

        let hasStartedPlayback = false;
        const tryStartPlayback = () => {
          if (hasStartedPlayback) return;
          if (ttsPlayerRef.current !== player) return; // superseded by newer playback
          hasStartedPlayback = true;
          try {
            player.play();
          } catch {
            // Retry once — some Android OEMs throw on the very first play()
            // call right after decode completes.
            setTimeout(() => {
              try { player.play(); } catch {}
            }, 150);
          }
        };

        try {
          (player as any).addListener?.('playbackStatusUpdate', (s: any) => {
            if (!hasStartedPlayback && s?.isLoaded) {
              tryStartPlayback();
            }
            if (s?.didJustFinish || (s?.duration > 0 && s?.currentTime >= s?.duration - 0.05)) {
              stopCloudTTS();
              try { file.delete(); } catch {}
            }
          });
        } catch {}

        // Some platforms flip `isLoaded` synchronously for small local
        // files, before the first status event ever fires — check directly.
        if ((player as any).isLoaded) {
          tryStartPlayback();
        }

        // Hard fallback: if we never see isLoaded become true (missed
        // native event) within 2.5s, force-start anyway so a tap never
        // results in permanent silence.
        setTimeout(() => {
          if (!hasStartedPlayback) tryStartPlayback();
        }, 2500);

        // Fallback cleanup — if we somehow never get the finish event, release
        // after 90s max (long enough for a 3000-char reply at slow speech).
        ttsPlayerReleaseTimerRef.current = setTimeout(() => {
          stopCloudTTS();
          try { file.delete(); } catch {}
        }, 90_000);
      } catch (e: any) {
        setSpeakingId(null);
        Alert.alert(
          'Speaker unavailable',
          e?.message?.includes('Network')
            ? 'Could not reach the speech server. Please check your internet connection.'
            : 'Could not play audio right now. Please try again in a moment.',
        );
      }
    },
    [speakingId, language, speechRate, token, stopCloudTTS],
  );
  // Keep the forward-declared ref up to date whenever `speak` changes.
  speakRef.current = speak;

  /** Start listening — records audio and uploads to Whisper cloud STT.
   *  Hardcoded to Whisper for reliability across all Android OEMs (Samsung /
   *  Xiaomi / Realme / etc.). Native SpeechRecognizer is intentionally NOT
   *  used because it silently fails on many OEM devices where the default
   *  voice engine is not Google's. See getConfiguredSTT() docstring. */
  const startRecording = useCallback(async () => {
    if (!token) return;
    // Defensive: recording needs exclusive audio-session access. If TTS is
    // still speaking a previous answer, stop it first — otherwise the OS
    // audio session switch (playback -> record) can leave the speaker
    // player in a stuck "paused" state on some Android OEMs.
    stopCloudTTS();
    try {
      const { provider, fellBack } = await getConfiguredSTT(API_BASE, token);
      setSttProviderLabel(fellBack ? `${provider.displayName} (fallback)` : provider.displayName);

      // Cloud Whisper — record audio, transcribe on send
      const perm = await AudioModule.requestRecordingPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Microphone permission', 'Please enable microphone to speak your question.');
        return;
      }
      // Race guard: user may have already released while we awaited permission.
      if (!isMicHeldRef.current) return;
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
      // Defensive: release any lingering prepared/recording session from a
      // previous quick tap before preparing a new one — otherwise Expo Audio
      // throws "AudioRecorder has already been prepared".
      try {
        await recorder.stop();
      } catch {}
      await recorder.prepareToRecordAsync();
      // Race guard again: prepareToRecordAsync can take another 100-500ms.
      if (!isMicHeldRef.current) {
        try { await recorder.stop(); } catch {}
        return;
      }
      recorder.record();
      setRecording(true);
    } catch (e: any) {
      Alert.alert('Recording failed', e?.message || 'Try again');
    }
  }, [recorder, token, stopCloudTTS]);

  const stopRecording = useCallback(async () => {
    // Stop the elapsed-time ticker
    if (holdTimerRef.current) {
      clearInterval(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    setHoldElapsed(0);

    // If native STT was running (only possible on stale APK builds), finish
    // it safely — this branch is otherwise dead since getConfiguredSTT is
    // hardcoded to Whisper. We keep the cleanup for defence-in-depth only.
    if (nativeSTTHandleRef.current) {
      try {
        setTranscribing(true);
        setRecording(false);
        await nativeSTTHandleRef.current.stop();
      } catch {}
      nativeSTTHandleRef.current = null;
      setTranscribing(false);
      // Fall through to the Whisper path below? No — on stale native builds
      // there is no audio recording running, so nothing to transcribe. Just
      // clean up and return silently.
      return;
    }

    // Whisper fallback path — stop audio recorder + POST to backend → show modal
    try {
      setRecording(false);
      setTranscribing(true);
      await recorder.stop();
      const uri = recorder.uri;
      try {
        if (Platform.OS !== 'web') {
          await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
        }
      } catch {}
      if (!uri) {
        setTranscribing(false);
        return;
      }
      if (!token) {
        setTranscribing(false);
        return;
      }
      const text = await whisperTranscribeFile(API_BASE, token, uri, language?.code);
      setTranscribing(false);
      const heardText = (text || '').trim();
      if (heardText) {
        setTranscriptPreview(heardText);
        setShowTranscriptModal(true);
      } else {
        Alert.alert('Could not transcribe', 'Please try again.');
      }
    } catch (e: any) {
      setTranscribing(false);
      Alert.alert('Transcription failed', e?.message || 'Try again');
    }
  }, [recorder, token, language]);

  // WhatsApp-style hold-to-talk handlers
  const onMicPressIn = useCallback(() => {
    // Synchronously mark the mic as held BEFORE any async work — this is the
    // signal that startRecording checks after each await to know whether the
    // user is still holding the button.
    isMicHeldRef.current = true;
    // Start hold timer + kick off recording
    setHoldElapsed(0);
    holdTimerRef.current = setInterval(() => {
      setHoldElapsed((prev) => prev + 1);
    }, 1000);
    startRecording();
  }, [startRecording]);

  const onMicPressOut = useCallback(() => {
    // Synchronously drop the held flag so any in-flight startRecording aborts.
    isMicHeldRef.current = false;
    // Always clear the timer
    if (holdTimerRef.current) {
      clearInterval(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    setHoldElapsed(0);
    // If any recording actually started, stop it. We check BOTH `recording`
    // state AND the STT handle ref so we don't miss a recording that just
    // started but whose state flush hasn't landed yet.
    if (recording || nativeSTTHandleRef.current) {
      stopRecording();
    }
  }, [recording, stopRecording]);

  const cancelTranscript = useCallback(() => {
    setShowTranscriptModal(false);
    setTranscriptPreview('');
  }, []);

  const sendTranscript = useCallback(() => {
    const t = transcriptPreview.trim();
    setShowTranscriptModal(false);
    setTranscriptPreview('');
    if (t) send(t);
  }, [transcriptPreview, send]);

  const editTranscriptInComposer = useCallback(() => {
    // Push transcript into the text input so the user can edit before sending
    setInput(transcriptPreview);
    setShowTranscriptModal(false);
    setTranscriptPreview('');
  }, [transcriptPreview]);

  const cycleSpeechRate = useCallback(() => {
    // 1.0 → 1.5 → 2.0 → 1.0
    setSpeechRate((prev) => {
      if (prev < 1.25) return 1.5;
      if (prev < 1.75) return 2.0;
      return 1.0;
    });
  }, []);

  const startNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setInput('');
  }, []);

  const activeSuggestions = proMode ? PRO_SUGGESTIONS : BASIC_SUGGESTIONS;

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="chat-screen">
      <View style={styles.header}>
        <View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Text style={styles.title}>Dhara</Text>
            {isPro && (
              <View testID="pro-badge" style={styles.proBadge}>
                <Ionicons name="star" size={11} color={theme.colors.onBrandSecondary} />
                <Text style={styles.proBadgeText}>PRO</Text>
              </View>
            )}
          </View>
          <Text style={styles.subtitle}>
            {language.native}
          </Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', flexWrap: 'wrap', gap: 8, flexShrink: 1 }}>
          <SOSButton />
          <Pressable testID="new-chat-button" style={styles.newChatBtn} onPress={startNewChat}>
            <Ionicons name="add" size={16} color={theme.colors.brand} />
            <Text style={styles.newChatText}>New Chat</Text>
          </Pressable>
        </View>
      </View>

      {/* Pro-mode toggle row */}
      <View style={styles.modeRow} testID="mode-row">
        <View style={{ flex: 1 }}>
          <Text style={styles.modeLabel}>
            {proMode ? '⚖️  Pro answer mode' : '📖  Basic mode (unlimited)'}
          </Text>
          <Text style={styles.modeSub}>
            {proMode
              ? isPro
                ? 'Lawyer-style deep answers, drafts, action plans.'
                : `Free samples remaining: ${remaining} of ${user?.pro_samples_limit ?? 5}`
              : 'Free forever. Simple answers with law citations.'}
          </Text>
        </View>
        <Switch
          testID="pro-mode-switch"
          value={proMode}
          onValueChange={(v) => {
            setProMode(v);
            if (v && !isPro && remaining <= 0) {
              // Preemptively show paywall
              setPaywall({
                samples_used: user?.pro_samples_limit ?? 5,
                samples_limit: user?.pro_samples_limit ?? 5,
                pro_price_label: '₹50',
                pro_price_usd_label: '$5',
                message:
                  "You've used all your free Pro-quality samples. Upgrade to Pro to unlock unlimited lawyer-style deep answers, drafts, action plans and escalation paths.",
              });
            }
          }}
          trackColor={{ true: theme.colors.brandSecondary, false: theme.colors.borderStrong }}
          thumbColor={theme.colors.surface}
        />
      </View>

      {/* Static upgrade hint for non-Pro users */}
      {!isPro && !proMode && (
        <Pressable
          testID="chat-upgrade-cta"
          style={styles.upgradeBanner}
          onPress={() => router.push('/upgrade')}
        >
          <Ionicons name="star" size={16} color={theme.colors.onBrandSecondary} />
          <Text style={styles.upgradeBannerText}>Upgrade to Pro — ₹50 / $5 — unlimited depth</Text>
          <Ionicons name="chevron-forward" size={16} color={theme.colors.onBrandSecondary} />
        </Pressable>
      )}

      {/*
        keyboardVerticalOffset MUST be 0 here — it is not "the height of the chrome
        below us". The library computes the lift as
            frame.y + frame.height - (screenHeight - keyboardHeight - offset)
        and `frame` comes from onLayout, i.e. it is already measured relative to
        this screen's SafeAreaView, whose origin sits at window y=0. So
        `frame.y + frame.height` is the composer's real on-screen bottom and the
        tab bar + disclaimer banner below it are ALREADY subtracted automatically.
        Any non-zero offset is added on top and simply floats the composer that
        many pixels above the keyboard — the previous 64/88 left a visible gap.
        Keeping it 0 also means the variable-height disclaimer banner (it wraps to
        3-4 lines on narrow phones) needs no hardcoded constant to track.
      */}
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior="translate-with-padding"
        keyboardVerticalOffset={0}
      >
        <ScrollView
          ref={scrollRef}
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {messages.length === 0 ? (
            <View style={styles.empty}>
              <View style={styles.emblem}>
                <Ionicons name="library" size={40} color={theme.colors.brandSecondary} />
              </View>
              <Text style={styles.emptyTitle}>Ask any question about your rights</Text>
              <Text style={styles.emptySub}>
                Bharatiya Nyaya Sanhita · Constitution · Supreme Court judgments — quoted exactly.
              </Text>
              <View style={{ marginTop: theme.spacing.xl, gap: theme.spacing.sm, alignSelf: 'stretch', width: '100%' }}>
                {activeSuggestions.map((s, i) => (
                  <Pressable
                    key={i}
                    testID={`suggestion-${i}`}
                    style={styles.suggestion}
                    onPress={() => send(s.text)}
                  >
                    <Ionicons name={s.icon} size={20} color={theme.colors.brand} />
                    <Text style={styles.suggestionText} numberOfLines={2}>{s.text}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ) : (
            messages.map((m) => (
              <View
                key={m.id}
                style={[styles.msg, m.role === 'user' ? styles.userMsg : styles.aiMsg]}
              >
                <View style={styles.msgHeader}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <Text
                      style={[
                        styles.msgRole,
                        m.role === 'user' ? styles.userRole : styles.aiRole,
                      ]}
                    >
                      {m.role === 'user' ? 'You' : 'Dhara'}
                    </Text>
                    {m.role === 'assistant' && m.mode === 'pro' && (
                      <View style={styles.proTag}>
                        <Text style={styles.proTagText}>PRO</Text>
                      </View>
                    )}
                  </View>
                  {m.role === 'assistant' && m.content.length > 0 && (
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                      {/* Playback speed toggle — cycles 1x → 1.5x → 2x */}
                      <Pressable
                        testID={`speed-${m.id}`}
                        onPress={cycleSpeechRate}
                        hitSlop={8}
                        style={styles.speedChip}
                      >
                        <Text style={styles.speedChipText}>
                          {speechRate === 1.0 ? '1x' : speechRate === 1.5 ? '1.5x' : '2x'}
                        </Text>
                      </Pressable>
                      <Pressable testID={`speak-${m.id}`} onPress={() => speak(m.id, m.content)} hitSlop={10}>
                        <Ionicons
                          name={speakingId === m.id ? 'stop-circle' : 'volume-high-outline'}
                          size={24}
                          color={theme.colors.brand}
                        />
                      </Pressable>
                    </View>
                  )}
                </View>
                <Text
                  style={[
                    styles.msgText,
                    m.role === 'user' ? styles.userText : styles.aiText,
                  ]}
                >
                  {m.content || (streaming && m.role === 'assistant' ? '…' : '')}
                </Text>
                {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                  <View style={styles.citationsWrap} testID={`citations-${m.id}`}>
                    <Text style={styles.citationsHeader}>📚 Verified sources</Text>
                    {m.citations.map((c) => (
                      <View key={c.key} style={styles.citationCard}>
                        <View style={styles.citationHead}>
                          <View style={styles.citationChip}>
                            <Text style={styles.citationChipText}>{c.short_label}</Text>
                          </View>
                          <Text style={styles.citationVerified}>Verified {c.verified_at}</Text>
                        </View>
                        <Text style={styles.citationTitle}>{c.citation}</Text>
                        <Text style={styles.citationText} numberOfLines={8}>
                          {c.official_text}
                        </Text>
                        <Text
                          style={styles.citationSource}
                          numberOfLines={1}
                          onPress={() => {
                            import('expo-linking').then((L) => L.openURL(c.source_url));
                          }}
                        >
                          Source: indiacode.nic.in ↗
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ))
          )}
          {streaming && <ActivityIndicator style={{ marginTop: 12 }} color={theme.colors.brand} />}
        </ScrollView>

        {recording && (
          <View style={styles.recHud} testID="rec-hud">
            <View style={styles.recDot} />
            <Text style={styles.recTimeText}>
              {String(Math.floor(holdElapsed / 60)).padStart(2, '0')}:
              {String(holdElapsed % 60).padStart(2, '0')}
            </Text>
            <Text style={styles.recHintText}>
              Listening in {language.name} · release to send
            </Text>
          </View>
        )}

        <View style={styles.inputBar}>
          <TextInput
            testID="chat-input"
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder={`Ask in ${language.native}…`}
            placeholderTextColor={theme.colors.onSurfaceTertiary}
            multiline
            editable={!streaming && !transcribing}
          />
          {input.trim().length === 0 ? (
            <Pressable
              testID="mic-button"
              onPressIn={onMicPressIn}
              onPressOut={onMicPressOut}
              disabled={transcribing}
              style={[styles.mic, recording && styles.micActive]}
            >
              {transcribing ? (
                <ActivityIndicator color={theme.colors.onBrandPrimary} />
              ) : (
                <Ionicons
                  name={recording ? 'radio' : 'mic'}
                  size={26}
                  color={theme.colors.onBrandPrimary}
                />
              )}
            </Pressable>
          ) : (
            <Pressable
              testID="send-button"
              onPress={() => send(input)}
              disabled={streaming}
              style={styles.send}
            >
              <Ionicons name="arrow-up" size={24} color={theme.colors.onBrandPrimary} />
            </Pressable>
          )}
        </View>
      </KeyboardAvoidingView>

      {/* Transcript confirmation modal — shown after voice input is transcribed */}
      <Modal
        visible={showTranscriptModal}
        transparent
        animationType="fade"
        onRequestClose={cancelTranscript}
      >
        <View style={styles.pwOverlay}>
          <View style={styles.tcCard} testID="transcript-modal">
            <View style={styles.tcHeader}>
              <Ionicons name="mic-circle" size={26} color={theme.colors.brand} />
              <Text style={styles.tcTitle}>We heard</Text>
            </View>
            <Text style={styles.tcText} testID="transcript-text">
              {`\u201C${transcriptPreview}\u201D`}
            </Text>

            <Pressable
              testID="transcript-send-btn"
              style={styles.tcSendBtn}
              onPress={sendTranscript}
            >
              <Ionicons name="send" size={16} color={theme.colors.onBrandPrimary} />
              <Text style={styles.tcSendText}>Correct — send</Text>
            </Pressable>

            <View style={styles.tcRow}>
              <Pressable
                testID="transcript-edit-btn"
                style={styles.tcSecondaryBtn}
                onPress={editTranscriptInComposer}
              >
                <Ionicons name="pencil" size={14} color={theme.colors.brand} />
                <Text style={styles.tcSecondaryText}>Edit</Text>
              </Pressable>
              <Pressable
                testID="transcript-cancel-btn"
                style={styles.tcSecondaryBtn}
                onPress={cancelTranscript}
              >
                <Ionicons name="mic-off" size={14} color={theme.colors.brand} />
                <Text style={styles.tcSecondaryText}>Re-record</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

      {/* Paywall Modal — shown when Pro-mode samples exhausted */}
      <Modal
        visible={paywall !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setPaywall(null)}
      >
        <View style={styles.pwOverlay}>
          <View style={styles.pwCard} testID="paywall-modal">
            <View style={styles.pwCrown}>
              <Ionicons name="lock-closed" size={28} color={theme.colors.brandSecondary} />
            </View>
            <Text style={styles.pwTitle}>Free samples used</Text>
            <Text style={styles.pwBody}>{paywall?.message}</Text>
            <View style={styles.pwPriceRow}>
              <Text style={styles.pwPrice}>{paywall?.pro_price_label}</Text>
              <Text style={styles.pwPriceOr}>or</Text>
              <Text style={styles.pwPrice}>{paywall?.pro_price_usd_label}</Text>
            </View>
            <Text style={styles.pwPriceMeta}>one-time · lifetime Pro access</Text>

            <Pressable
              testID="paywall-upgrade-btn"
              style={styles.pwUpgrade}
              onPress={() => {
                setPaywall(null);
                router.push('/upgrade');
              }}
            >
              <Ionicons name="star" size={18} color={theme.colors.onBrandPrimary} />
              <Text style={styles.pwUpgradeText}>Upgrade to Pro</Text>
            </Pressable>

            <Pressable
              testID="paywall-continue-basic-btn"
              onPress={() => {
                setPaywall(null);
                setProMode(false);
              }}
            >
              <Text style={styles.pwContinue}>Continue in Basic mode (free, unlimited) →</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.surface },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.xl,
    paddingVertical: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.divider,
    backgroundColor: theme.colors.surface,
  },
  title: { fontFamily: theme.fonts.display, fontSize: 26, fontWeight: '700', color: theme.colors.brand },
  subtitle: { color: theme.colors.onSurfaceSecondary, fontSize: 12, marginTop: 2 },
  badge: {
    backgroundColor: theme.colors.surfaceTertiary,
    borderRadius: theme.radius.pill,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
  },
  badgeText: { color: theme.colors.brand, fontSize: 11, fontWeight: '700' },
  newChatBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.pill,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    backgroundColor: theme.colors.surface,
    minHeight: 32,
  },
  newChatText: { color: theme.colors.brand, fontSize: 12, fontWeight: '700' },
  modeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.sm,
    backgroundColor: theme.colors.surfaceSecondary,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.divider,
  },
  modeLabel: { color: theme.colors.brand, fontWeight: '700', fontSize: 13 },
  modeSub: { color: theme.colors.onSurfaceSecondary, fontSize: 11, marginTop: 2 },
  scroll: { padding: theme.spacing.lg, paddingBottom: theme.spacing.xl },
  empty: { flex: 1, alignItems: 'center', paddingTop: theme.spacing.xxl, paddingHorizontal: theme.spacing.md },
  emblem: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: theme.colors.surfaceSecondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyTitle: {
    fontFamily: theme.fonts.display,
    fontSize: 22,
    color: theme.colors.onSurface,
    marginTop: theme.spacing.lg,
    textAlign: 'center',
    fontWeight: '700',
  },
  emptySub: { color: theme.colors.onSurfaceSecondary, textAlign: 'center', marginTop: theme.spacing.sm, lineHeight: 22 },
  suggestion: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.surfaceSecondary,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    width: '100%',
    minHeight: 56,
  },
  suggestionText: { color: theme.colors.onSurface, flex: 1, fontSize: 15, flexShrink: 1 },
  msg: { marginBottom: theme.spacing.lg, borderRadius: theme.radius.lg, padding: theme.spacing.lg },
  userMsg: {
    backgroundColor: theme.colors.brand,
    alignSelf: 'flex-end',
    maxWidth: '90%',
    borderBottomRightRadius: 4,
  },
  aiMsg: {
    backgroundColor: theme.colors.surfaceSecondary,
    alignSelf: 'flex-start',
    maxWidth: '100%',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  msgHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: theme.spacing.xs },
  msgRole: { fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  userRole: { color: theme.colors.brandSecondary },
  aiRole: { color: theme.colors.brand },
  msgText: { fontSize: 15, lineHeight: 22 },
  userText: { color: theme.colors.onBrandPrimary },
  aiText: { color: theme.colors.onSurface },
  citationsWrap: {
    marginTop: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  citationsHeader: {
    fontSize: 11,
    fontWeight: '800',
    color: theme.colors.brand,
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  citationCard: {
    borderWidth: 1,
    borderColor: theme.colors.brandSecondary,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    backgroundColor: '#FFFBEC',
    gap: 6,
  },
  citationHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  citationChip: {
    backgroundColor: theme.colors.brand,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: theme.radius.pill,
  },
  citationChipText: {
    color: theme.colors.onBrandPrimary,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  citationVerified: { fontSize: 10, color: theme.colors.onSurfaceTertiary },
  citationTitle: { fontSize: 12, fontWeight: '700', color: theme.colors.brand },
  citationText: { fontSize: 12, color: theme.colors.onSurface, lineHeight: 17, fontStyle: 'italic' },
  citationSource: {
    fontSize: 11,
    color: theme.colors.brand,
    fontWeight: '600',
    textDecorationLine: 'underline',
    marginTop: 4,
  },
  proTag: {
    backgroundColor: theme.colors.brandSecondary,
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 4,
  },
  proTagText: { color: theme.colors.onBrandSecondary, fontSize: 9, fontWeight: '800', letterSpacing: 0.5 },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: theme.spacing.md,
    gap: theme.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: theme.colors.divider,
    backgroundColor: theme.colors.surface,
  },
  input: {
    flex: 1,
    minHeight: 48,
    maxHeight: 120,
    borderRadius: theme.radius.lg,
    backgroundColor: theme.colors.surfaceSecondary,
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.md,
    paddingBottom: theme.spacing.md,
    color: theme.colors.onSurface,
    fontSize: 15,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  mic: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: theme.colors.brandSecondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  micActive: { backgroundColor: theme.colors.error },
  send: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: theme.colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  proBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    backgroundColor: theme.colors.brandSecondary,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: theme.radius.pill,
  },
  proBadgeText: { color: theme.colors.onBrandSecondary, fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  upgradeBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    backgroundColor: theme.colors.brandSecondary,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
  },
  upgradeBannerText: { flex: 1, color: theme.colors.onBrandSecondary, fontWeight: '700', fontSize: 13 },
  sttHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'center',
    backgroundColor: theme.colors.surfaceSecondary,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radius.pill,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  sttHintText: { color: theme.colors.brand, fontSize: 11, fontWeight: '600' },
  // WhatsApp-style recording HUD
  recHud: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    alignSelf: 'center',
    backgroundColor: theme.colors.brand,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: theme.radius.pill,
    marginBottom: 8,
  },
  recDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: theme.colors.error },
  recTimeText: {
    color: theme.colors.onBrandPrimary,
    fontVariant: ['tabular-nums'],
    fontWeight: '700',
    fontSize: 13,
    minWidth: 40,
  },
  recHintText: { color: theme.colors.onBrandPrimary, fontSize: 11, opacity: 0.9 },
  // Playback speed chip
  speedChip: {
    backgroundColor: theme.colors.surfaceTertiary,
    borderRadius: theme.radius.pill,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  speedChipText: {
    color: theme.colors.brand,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  // Transcript confirmation modal
  tcCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.xl,
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: theme.colors.brandSecondary,
  },
  tcHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: theme.spacing.md,
  },
  tcTitle: {
    fontFamily: theme.fonts.display,
    fontSize: 18,
    fontWeight: '700',
    color: theme.colors.brand,
  },
  tcText: {
    color: theme.colors.onSurface,
    fontSize: 16,
    lineHeight: 22,
    fontStyle: 'italic',
    marginBottom: theme.spacing.lg,
  },
  tcSendBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: theme.colors.brand,
    borderRadius: theme.radius.md,
    paddingVertical: theme.spacing.lg,
    marginBottom: theme.spacing.md,
  },
  tcSendText: { color: theme.colors.onBrandPrimary, fontWeight: '800', fontSize: 15 },
  tcRow: { flexDirection: 'row', gap: theme.spacing.md },
  tcSecondaryBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    paddingVertical: theme.spacing.md,
    backgroundColor: theme.colors.surfaceSecondary,
  },
  tcSecondaryText: { color: theme.colors.brand, fontWeight: '700', fontSize: 13 },
  pwOverlay: {
    flex: 1,
    backgroundColor: 'rgba(10,28,58,0.85)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.xl,
  },
  pwCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.xl,
    alignItems: 'center',
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: theme.colors.brandSecondary,
  },
  pwCrown: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: theme.colors.surfaceSecondary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
  },
  pwTitle: {
    fontFamily: theme.fonts.display,
    fontSize: 22,
    fontWeight: '700',
    color: theme.colors.brand,
    marginBottom: theme.spacing.sm,
  },
  pwBody: {
    color: theme.colors.onSurfaceSecondary,
    fontSize: 14,
    lineHeight: 20,
    textAlign: 'center',
    marginBottom: theme.spacing.lg,
  },
  pwPriceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 10,
    marginTop: theme.spacing.sm,
  },
  pwPrice: {
    fontFamily: theme.fonts.display,
    fontSize: 32,
    fontWeight: '800',
    color: theme.colors.brand,
  },
  pwPriceOr: { color: theme.colors.onSurfaceTertiary, fontSize: 13 },
  pwPriceMeta: { color: theme.colors.onSurfaceTertiary, fontSize: 12, marginBottom: theme.spacing.lg },
  pwUpgrade: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: theme.colors.brandSecondary,
    borderRadius: theme.radius.md,
    paddingHorizontal: theme.spacing.xl,
    paddingVertical: theme.spacing.lg,
    minWidth: '80%',
    marginBottom: theme.spacing.md,
  },
  pwUpgradeText: { color: theme.colors.onBrandPrimary, fontWeight: '800', fontSize: 15 },
  pwContinue: {
    color: theme.colors.brand,
    fontSize: 13,
    textDecorationLine: 'underline',
    fontWeight: '600',
  },
});
