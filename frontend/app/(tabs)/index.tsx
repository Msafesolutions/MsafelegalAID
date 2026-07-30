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
import * as Speech from 'expo-speech';
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
} from 'expo-audio';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';
import { getConfiguredSTT, whisperTranscribeFile, pickSupportedLocale } from '@/src/voice/stt';

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
  { text: 'What are my rights during a police stop?', icon: 'shield-checkmark-outline' },
  { text: 'How do I file an RTI application?', icon: 'document-text-outline' },
  { text: 'How to file a consumer complaint online?', icon: 'cart-outline' },
  { text: 'What are the rules for a road accident?', icon: 'car-outline' },
];

const PRO_SUGGESTIONS: { text: string; icon: React.ComponentProps<typeof Ionicons>['name'] }[] = [
  { text: 'Draft a complaint letter to the SP against wrongful detention', icon: 'create-outline' },
  { text: 'Give me a step-by-step action plan to file a consumer complaint', icon: 'list-outline' },
  { text: 'Draft an RTI application asking for FIR copy', icon: 'file-tray-outline' },
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
      // Stop any ongoing TTS playback
      try {
        Speech.stop();
      } catch {}
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
      Speech.stop();
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

  const speak = useCallback(
    async (msgId: string, text: string) => {
      if (speakingId === msgId) {
        Speech.stop();
        setSpeakingId(null);
        return;
      }
      Speech.stop();
      try {
        if (Platform.OS !== 'web') {
          await setAudioModeAsync({
            playsInSilentMode: true,
            allowsRecording: false,
            shouldPlayInBackground: false,
          });
        }
      } catch {}

      // Enumerate installed voices and pick the best match for the selected language.
      // This is what makes TTS actually SPEAK in the selected language instead of
      // silently falling back to English (the default browser/OS behavior when the
      // requested locale has no installed voice).
      let voiceId: string | undefined = undefined;
      let voiceLangTag: string = language.tts || 'en-IN';
      let voiceUnavailable = false;
      let fallbackNoticeLang: string | null = null; // set if we substitute a related-family voice
      const targetFull = (language.tts || 'en-IN').toLowerCase();
      const targetShort = targetFull.split('-')[0];

      // Script-family fallbacks for the 8 rare Indian languages whose voices are
      // rarely pre-installed on Android/iOS. When the user's exact voice is missing,
      // we substitute the closest phonetically-related language so the app still
      // SPEAKS. We disclose this to the user with a small alert so they know.
      const SCRIPT_FALLBACKS: Record<string, string[]> = {
        // Devanagari-script minor languages → Hindi voice
        kok: ['mr', 'hi'], mai: ['hi'], doi: ['hi'], brx: ['hi'],
        sa: ['hi'], ne: ['hi'],
        // Perso-Arabic + Devanagari mix → Urdu or Hindi
        ks: ['ur', 'hi'], sd: ['ur', 'hi'],
        // Bengali script for Manipuri; Ol Chiki (Santali) uses Bengali as closest fallback
        mni: ['bn'], sat: ['bn', 'hi'],
      };

      try {
        const voices = await Speech.getAvailableVoicesAsync();
        if (voices && voices.length > 0) {
          // 1) Exact locale match (e.g. hi-IN → hi-IN)
          const exact = voices.find((v: any) => (v.language || '').toLowerCase() === targetFull);
          // 2) Language-family match (e.g. hi-IN → any hi-*)
          const fam = voices.find(
            (v: any) => (v.language || '').toLowerCase().split('-')[0] === targetShort,
          );
          const primary = exact || fam;
          if (primary) {
            voiceId = (primary as any).identifier;
            voiceLangTag = (primary as any).language || voiceLangTag;
          } else if (SCRIPT_FALLBACKS[targetShort]) {
            // 3) Script-family fallback (Konkani → Marathi/Hindi, etc.)
            for (const alt of SCRIPT_FALLBACKS[targetShort]) {
              const altVoice = voices.find(
                (v: any) => (v.language || '').toLowerCase().split('-')[0] === alt,
              );
              if (altVoice) {
                voiceId = (altVoice as any).identifier;
                voiceLangTag = (altVoice as any).language || alt;
                fallbackNoticeLang = alt;
                break;
              }
            }
            if (!voiceId) voiceUnavailable = true;
          } else if (targetShort !== 'en') {
            voiceUnavailable = true;
          }
        }
      } catch {
        // Voice enumeration not supported (some web browsers) — fall through and
        // let Speech.speak try its best with the language tag alone.
      }

      if (voiceUnavailable) {
        Alert.alert(
          'Voice not installed',
          `${language.name} voice is not installed on this device.\n\n` +
            `To enable ${language.name} speech:\n` +
            (Platform.OS === 'android'
              ? '• Open Settings → General management → Text-to-speech\n• Tap the gear icon → Install voice data → download ' +
                language.name
              : Platform.OS === 'ios'
              ? '• Open Settings → Accessibility → Spoken Content → Voices → download ' +
                language.name
              : '• Install a browser or OS voice pack for ' + language.name),
        );
        // Do NOT play English silently for a language the user asked for — that would
        // create the "only English" bug we are fixing. Stop here.
        setSpeakingId(null);
        return;
      }

      // Disclose to the user that we're using a related-family voice, so they aren't
      // confused when the pronunciation sounds like Hindi/Marathi/Urdu/Bengali.
      if (fallbackNoticeLang) {
        const FALLBACK_NAMES: Record<string, string> = {
          hi: 'Hindi', mr: 'Marathi', ur: 'Urdu', bn: 'Bengali',
        };
        // Fire and forget — do not block playback
        setTimeout(() => {
          Alert.alert(
            'Using related voice',
            `${language.name} voice is not installed. Speaking with the ${FALLBACK_NAMES[fallbackNoticeLang!] || fallbackNoticeLang} voice (closest available). Install ${language.name} in device settings for native pronunciation.`,
          );
        }, 0);
      }

      setSpeakingId(msgId);
      Speech.speak(text, {
        language: voiceLangTag,
        voice: voiceId,
        volume: 1.0,
        rate: speechRate,
        onDone: () => setSpeakingId(null),
        onStopped: () => setSpeakingId(null),
        onError: () => setSpeakingId(null),
      });
    },
    [speakingId, language, speechRate],
  );
  // Keep the forward-declared ref up to date whenever `speak` changes.
  speakRef.current = speak;

  /** Start listening — uses the configured STT provider (native by default). */
  const startRecording = useCallback(async () => {
    if (!token) return;
    try {
      const { provider, providerId, fellBack } = await getConfiguredSTT(API_BASE, token);
      setSttProviderLabel(fellBack ? `${provider.displayName} (fallback)` : provider.displayName);

      if (providerId === 'native') {
        // Pre-flight: check whether the device's speech recognizer supports the
        // user's selected language BEFORE starting. This is the fix for "voice
        // not recording" on Hindi / other Indian languages on some Android
        // devices — previously the recognizer started with an unsupported
        // locale and silently returned no result.
        const pick = await pickSupportedLocale(language.tts);

        if (pick.chosen === null || (pick.usedFallback && pick.fallbackReason === 'english')) {
          // Strict language policy: if the user selected Tamil/Hindi/etc. and that
          // language is not installed on this device, refuse cleanly rather than
          // silently switching to English. This is what the user asked for.
          Alert.alert(
            `${language.name} voice not installed`,
            `Voice input for ${language.name} is not installed on this device.\n\n` +
              `To enable it:\n` +
              (Platform.OS === 'android'
                ? '• Open Settings → System → Languages → Add ' + language.name + '\n' +
                  '• Install "Speech Services by Google" from the Play Store\n' +
                  '• Restart the app'
                : '• Open Settings → General → Keyboard → Dictation → enable ' + language.name),
            [{ text: 'OK' }],
          );
          return;
        }

        // If we had to fall back to another language, tell the user before we
        // start listening so they know we're not speaking their language.
        const startNative = async (lang: string) => {
          try {
            const handle = await provider.start({
              languageTag: lang,
              onPartial: (r) => setInput(r.text),
              onError: (m) => {
                // Surface the actual OS error rather than a generic message so
                // the user knows what to do (install pack, grant permission, etc.).
                Alert.alert(
                  'Voice error',
                  `${m}\n\nTip: make sure "Speech Services by Google" is set as ` +
                    `your default speech engine in Settings → System → Text-to-speech.`,
                );
              },
            });
            nativeSTTHandleRef.current = handle;
            setRecording(true);
          } catch (e: any) {
            throw e;
          }
        };

        if (pick.usedFallback && pick.fallbackReason === 'english') {
          // Already handled above (strict-language policy refuses this path).
          return;
        }

        try {
          await startNative(pick.chosen!);
          return;
        } catch (e: any) {
          // fall through to whisper-cloud audio recorder as final fallback
          console.warn('native STT failed, falling back to whisper:', e?.message);
        }
      }

      // Cloud Whisper fallback (or explicit config) — record audio, transcribe on send
      const perm = await AudioModule.requestRecordingPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Microphone permission', 'Please enable microphone to speak your question.');
        return;
      }
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
      // Defensive: release any lingering prepared/recording session from a
      // previous quick tap before preparing a new one — otherwise Expo Audio
      // throws "AudioRecorder has already been prepared".
      try {
        await recorder.stop();
      } catch {}
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(true);
    } catch (e: any) {
      Alert.alert('Recording failed', e?.message || 'Try again');
    }
  }, [recorder, token, language]);

  const stopRecording = useCallback(async () => {
    // Stop the elapsed-time ticker
    if (holdTimerRef.current) {
      clearInterval(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    setHoldElapsed(0);

    // If native STT was running, finish it → show transcript confirmation modal
    if (nativeSTTHandleRef.current) {
      try {
        setTranscribing(true);
        setRecording(false);
        const result = await nativeSTTHandleRef.current.stop();
        nativeSTTHandleRef.current = null;
        setTranscribing(false);
        const heardText = (result?.text || '').trim();
        if (heardText) {
          setTranscriptPreview(heardText);
          setShowTranscriptModal(true);
        }
      } catch (e: any) {
        setTranscribing(false);
        Alert.alert('Voice error', e?.message || 'Try again');
      }
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
      const text = await whisperTranscribeFile(API_BASE, token, uri);
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
  }, [recorder, token]);

  // WhatsApp-style hold-to-talk handlers
  const onMicPressIn = useCallback(() => {
    // Start hold timer + kick off recording
    setHoldElapsed(0);
    holdTimerRef.current = setInterval(() => {
      setHoldElapsed((prev) => prev + 1);
    }, 1000);
    startRecording();
  }, [startRecording]);

  const onMicPressOut = useCallback(() => {
    // Release → stop recording (only if we were actually recording)
    if (recording || nativeSTTHandleRef.current) {
      stopRecording();
    } else {
      // Recording never actually started (e.g. permission dialog) — reset timer
      if (holdTimerRef.current) {
        clearInterval(holdTimerRef.current);
        holdTimerRef.current = null;
      }
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
        <View style={styles.badge}>
          <Text style={styles.badgeText}>BNS · संविधान</Text>
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

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior="translate-with-padding"
        keyboardVerticalOffset={Platform.OS === 'ios' ? 88 : 64}
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
