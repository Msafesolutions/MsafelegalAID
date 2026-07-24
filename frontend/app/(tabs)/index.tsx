import { useState, useRef, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  Modal,
  Switch,
} from 'react-native';
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
import { getConfiguredSTT, whisperTranscribeFile } from '@/src/voice/stt';

type Msg = { id: string; role: 'user' | 'assistant'; content: string; mode?: 'basic' | 'pro' };

const BASIC_SUGGESTIONS = [
  'What are my rights during a police stop?',
  'How do I file an FIR?',
  'Can police arrest me without warrant?',
  'What is Article 21 of the Constitution?',
];

const PRO_SUGGESTIONS = [
  'Draft a complaint letter to the SP against wrongful detention',
  'Give me a step-by-step action plan to file a consumer complaint',
  'Draft an RTI application asking for FIR copy',
  'Full escalation path for a domestic violence case',
];

export default function ChatScreen() {
  const { token, user, language, model, refreshUser } = useAuth();
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
  const [sttProviderLabel, setSttProviderLabel] = useState<string>('');
  const scrollRef = useRef<ScrollView>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const nativeSTTHandleRef = useRef<{ stop: () => Promise<any> } | null>(null);

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
          // remove the placeholder assistant bubble
          setMessages((prev) => prev.filter((m) => m.id !== assistantId && m.id !== userId));
          return;
        }

        if (!res.ok || !res.body) {
          const err = await res.text();
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: `Error: ${err}` } : m))
          );
          return;
        }

        const reader = (res.body as any).getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let acc = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';
          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith('data:')) continue;
            try {
              const payload = JSON.parse(line.slice(5).trim());
              if (payload.type === 'session') {
                setSessionId(payload.session_id);
                if (typeof payload.samples_remaining_after === 'number') {
                  setSamplesRemaining(payload.samples_remaining_after);
                }
              } else if (payload.type === 'delta') {
                acc += payload.content;
                setMessages((prev) =>
                  prev.map((m) => (m.id === assistantId ? { ...m, content: acc } : m))
                );
                scrollRef.current?.scrollToEnd({ animated: true });
              } else if (payload.type === 'error') {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: `⚠️ ${payload.error}` } : m
                  )
                );
              }
            } catch {}
          }
        }
        // sync counter from server
        try {
          await refreshUser();
        } catch {}
      } catch (e: any) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: `Error: ${e?.message || 'stream failed'}` } : m
          )
        );
      } finally {
        setStreaming(false);
      }
    },
    [streaming, token, sessionId, language, model, proMode, refreshUser]
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
      setSpeakingId(msgId);
      Speech.speak(text, {
        language: language.tts,
        volume: 1.0,
        onDone: () => setSpeakingId(null),
        onStopped: () => setSpeakingId(null),
        onError: () => setSpeakingId(null),
      });
    },
    [speakingId, language]
  );

  /** Start listening — uses the configured STT provider (native by default). */
  const startRecording = useCallback(async () => {
    if (!token) return;
    try {
      const { provider, providerId, fellBack } = await getConfiguredSTT(API_BASE, token);
      setSttProviderLabel(fellBack ? `${provider.displayName} (fallback)` : provider.displayName);

      if (providerId === 'native') {
        // Real on-device STT — best case
        try {
          const handle = await provider.start({
            languageTag: language.tts,
            onPartial: (r) => setInput(r.text),
            onError: (m) => Alert.alert('Voice error', m),
          });
          nativeSTTHandleRef.current = handle;
          setRecording(true);
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
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(true);
    } catch (e: any) {
      Alert.alert('Recording failed', e?.message || 'Try again');
    }
  }, [recorder, token, language]);

  const stopRecording = useCallback(async () => {
    // If native STT was running, finish it
    if (nativeSTTHandleRef.current) {
      try {
        setTranscribing(true);
        setRecording(false);
        const result = await nativeSTTHandleRef.current.stop();
        nativeSTTHandleRef.current = null;
        setTranscribing(false);
        if (result?.text) {
          send(result.text);
        }
      } catch (e: any) {
        setTranscribing(false);
        Alert.alert('Voice error', e?.message || 'Try again');
      }
      return;
    }

    // Whisper fallback path — stop audio recorder + POST to backend
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
      if (text) send(text);
      else Alert.alert('Could not transcribe', 'Please try again.');
    } catch (e: any) {
      setTranscribing(false);
      Alert.alert('Transcription failed', e?.message || 'Try again');
    }
  }, [recorder, token, send]);

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
            {language.native} · {model.label}
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
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={80}
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
              <View style={{ marginTop: theme.spacing.xl, gap: theme.spacing.sm }}>
                {activeSuggestions.map((s, i) => (
                  <Pressable
                    key={i}
                    testID={`suggestion-${i}`}
                    style={styles.suggestion}
                    onPress={() => send(s)}
                  >
                    <Ionicons name="sparkles-outline" size={16} color={theme.colors.brand} />
                    <Text style={styles.suggestionText}>{s}</Text>
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
                    <Pressable testID={`speak-${m.id}`} onPress={() => speak(m.id, m.content)} hitSlop={10}>
                      <Ionicons
                        name={speakingId === m.id ? 'stop-circle' : 'volume-high-outline'}
                        size={22}
                        color={theme.colors.brand}
                      />
                    </Pressable>
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
              </View>
            ))
          )}
          {streaming && <ActivityIndicator style={{ marginTop: 12 }} color={theme.colors.brand} />}
        </ScrollView>

        {recording && sttProviderLabel !== '' && (
          <View style={styles.sttHint} testID="stt-hint">
            <Ionicons name="mic" size={12} color={theme.colors.brand} />
            <Text style={styles.sttHintText}>
              Listening · {sttProviderLabel}
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
              onPress={recording ? stopRecording : startRecording}
              disabled={transcribing}
              style={[styles.mic, recording && styles.micActive]}
            >
              {transcribing ? (
                <ActivityIndicator color={theme.colors.onBrandPrimary} />
              ) : (
                <Ionicons
                  name={recording ? 'stop' : 'mic'}
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
    gap: 8,
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.surfaceSecondary,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  suggestionText: { color: theme.colors.onSurface, flex: 1 },
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
