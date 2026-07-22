import { useState, useRef, useEffect, useCallback } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Speech from 'expo-speech';
import { AudioModule, RecordingPresets, setAudioModeAsync, useAudioRecorder } from 'expo-audio';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';

type Msg = { id: string; role: 'user' | 'assistant'; content: string };

const SUGGESTIONS = [
  'What are my rights during a police stop?',
  'How do I file an FIR?',
  'Can police arrest me without warrant?',
  'What is Article 21 of the Constitution?',
];

export default function ChatScreen() {
  const { token, user, language, model } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [showBanner, setShowBanner] = useState(true);
  const scrollRef = useRef<ScrollView>(null);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);

  // Configure audio mode ONCE for playback through the loudspeaker (not earpiece).
  useEffect(() => {
    (async () => {
      try {
        if (Platform.OS !== 'web') {
          await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
        }
      } catch {}
    })();
    return () => { Speech.stop(); };
  }, []);

  const send = useCallback(async (text: string) => {
    const q = text.trim();
    if (!q || streaming || !token) return;
    const userId = Math.random().toString(36).slice(2);
    const assistantId = Math.random().toString(36).slice(2);
    setMessages(prev => [...prev, { id: userId, role: 'user', content: q }, { id: assistantId, role: 'assistant', content: '' }]);
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
        }),
      });
      if (!res.ok || !res.body) {
        const err = await res.text();
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: `Error: ${err}` } : m));
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
            if (payload.type === 'session') setSessionId(payload.session_id);
            else if (payload.type === 'delta') {
              acc += payload.content;
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: acc } : m));
              scrollRef.current?.scrollToEnd({ animated: true });
            } else if (payload.type === 'error') {
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: `⚠️ ${payload.error}` } : m));
            }
          } catch {}
        }
      }
    } catch (e: any) {
      setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: `Error: ${e?.message || 'stream failed'}` } : m));
    } finally {
      setStreaming(false);
    }
  }, [streaming, token, sessionId, language, model]);

  const speak = useCallback(async (msgId: string, text: string) => {
    if (speakingId === msgId) {
      Speech.stop();
      setSpeakingId(null);
      return;
    }
    Speech.stop();
    // Force loudspeaker: switch audio mode back to playback (not recording).
    try {
      if (Platform.OS !== 'web') {
        await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false, shouldPlayInBackground: false });
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
  }, [speakingId, language]);

  const startRecording = useCallback(async () => {
    try {
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
  }, [recorder]);

  const stopRecording = useCallback(async () => {
    try {
      setRecording(false);
      setTranscribing(true);
      await recorder.stop();
      const uri = recorder.uri;
      // Immediately switch audio mode back to loudspeaker playback
      try {
        if (Platform.OS !== 'web') {
          await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
        }
      } catch {}
      if (!uri) { setTranscribing(false); return; }

      const form = new FormData();
      // @ts-expect-error - RN FormData file
      form.append('audio', { uri, name: 'audio.m4a', type: 'audio/m4a' });

      const res = await fetch(`${API_BASE}/api/voice/transcribe`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const data = await res.json();
      setTranscribing(false);
      if (data.text) {
        send(data.text);
      } else {
        Alert.alert('Could not transcribe', data.detail || 'Try again');
      }
    } catch (e: any) {
      setTranscribing(false);
      Alert.alert('Transcription failed', e?.message || 'Try again');
    }
  }, [recorder, token, send]);

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="chat-screen">
      <View style={styles.header}>
        <View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Text style={styles.title}>Dhara</Text>
            {user?.is_pro && (
              <View testID="pro-badge" style={styles.proBadge}>
                <Ionicons name="star" size={11} color={theme.colors.onBrandSecondary} />
                <Text style={styles.proBadgeText}>PRO</Text>
              </View>
            )}
          </View>
          <Text style={styles.subtitle}>{language.native} • {model.label}</Text>
        </View>
        <View style={styles.badge}><Text style={styles.badgeText}>BNS · संविधान</Text></View>
      </View>

      {showBanner && (
        <View testID="disclaimer-banner" style={styles.banner}>
          <Ionicons name="warning-outline" size={18} color={theme.colors.warning} />
          <Text style={styles.bannerText}>
            Legal information — not legal advice. AI answers may be wrong. For real matters consult an advocate. Emergency: 112.
          </Text>
          <Pressable testID="dismiss-banner" onPress={() => setShowBanner(false)} hitSlop={10}>
            <Ionicons name="close" size={18} color={theme.colors.onSurfaceSecondary} />
          </Pressable>
        </View>
      )}

      {!user?.is_pro && messages.length > 2 && (
        <Pressable testID="chat-upgrade-cta" style={styles.upgradeBanner} onPress={() => router.push('/upgrade')}>
          <Ionicons name="star" size={16} color={theme.colors.onBrandSecondary} />
          <Text style={styles.upgradeBannerText}>Upgrade to Pro for lawyer-style depth</Text>
          <Ionicons name="chevron-forward" size={16} color={theme.colors.onBrandSecondary} />
        </Pressable>
      )}

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={80}>
        <ScrollView ref={scrollRef} contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {messages.length === 0 ? (
            <View style={styles.empty}>
              <View style={styles.emblem}><Ionicons name="library" size={40} color={theme.colors.brandSecondary} /></View>
              <Text style={styles.emptyTitle}>Ask any question about your rights</Text>
              <Text style={styles.emptySub}>Bharatiya Nyaya Sanhita • Constitution • Supreme Court judgments — quoted exactly.</Text>
              <View style={{ marginTop: theme.spacing.xl, gap: theme.spacing.sm }}>
                {SUGGESTIONS.map((s, i) => (
                  <Pressable key={i} testID={`suggestion-${i}`} style={styles.suggestion} onPress={() => send(s)}>
                    <Ionicons name="sparkles-outline" size={16} color={theme.colors.brand} />
                    <Text style={styles.suggestionText}>{s}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ) : (
            messages.map(m => (
              <View key={m.id} style={[styles.msg, m.role === 'user' ? styles.userMsg : styles.aiMsg]}>
                <View style={styles.msgHeader}>
                  <Text style={[styles.msgRole, m.role === 'user' ? styles.userRole : styles.aiRole]}>
                    {m.role === 'user' ? 'You' : 'Dhara'}
                  </Text>
                  {m.role === 'assistant' && m.content.length > 0 && (
                    <Pressable testID={`speak-${m.id}`} onPress={() => speak(m.id, m.content)} hitSlop={10}>
                      <Ionicons name={speakingId === m.id ? 'stop-circle' : 'volume-high-outline'} size={22} color={theme.colors.brand} />
                    </Pressable>
                  )}
                </View>
                <Text style={[styles.msgText, m.role === 'user' ? styles.userText : styles.aiText]}>
                  {m.content || (streaming && m.role === 'assistant' ? '…' : '')}
                </Text>
              </View>
            ))
          )}
          {streaming && <ActivityIndicator style={{ marginTop: 12 }} color={theme.colors.brand} />}
        </ScrollView>

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
                <Ionicons name={recording ? 'stop' : 'mic'} size={26} color={theme.colors.onBrandPrimary} />
              )}
            </Pressable>
          ) : (
            <Pressable testID="send-button" onPress={() => send(input)} disabled={streaming} style={styles.send}>
              <Ionicons name="arrow-up" size={24} color={theme.colors.onBrandPrimary} />
            </Pressable>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.surface },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: theme.spacing.xl, paddingVertical: theme.spacing.md, borderBottomWidth: 1, borderBottomColor: theme.colors.divider, backgroundColor: theme.colors.surface },
  title: { fontFamily: theme.fonts.display, fontSize: 26, fontWeight: '700', color: theme.colors.brand },
  subtitle: { color: theme.colors.onSurfaceSecondary, fontSize: 12, marginTop: 2 },
  badge: { backgroundColor: theme.colors.surfaceTertiary, borderRadius: theme.radius.pill, paddingHorizontal: theme.spacing.md, paddingVertical: theme.spacing.xs },
  badgeText: { color: theme.colors.brand, fontSize: 11, fontWeight: '700' },
  scroll: { padding: theme.spacing.lg, paddingBottom: theme.spacing.xl },
  empty: { flex: 1, alignItems: 'center', paddingTop: theme.spacing.xxl, paddingHorizontal: theme.spacing.md },
  emblem: { width: 88, height: 88, borderRadius: 44, backgroundColor: theme.colors.surfaceSecondary, alignItems: 'center', justifyContent: 'center' },
  emptyTitle: { fontFamily: theme.fonts.display, fontSize: 22, color: theme.colors.onSurface, marginTop: theme.spacing.lg, textAlign: 'center', fontWeight: '700' },
  emptySub: { color: theme.colors.onSurfaceSecondary, textAlign: 'center', marginTop: theme.spacing.sm, lineHeight: 22 },
  suggestion: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: theme.spacing.lg, backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border },
  suggestionText: { color: theme.colors.onSurface, flex: 1 },
  msg: { marginBottom: theme.spacing.lg, borderRadius: theme.radius.lg, padding: theme.spacing.lg },
  userMsg: { backgroundColor: theme.colors.brand, alignSelf: 'flex-end', maxWidth: '90%', borderBottomRightRadius: 4 },
  aiMsg: { backgroundColor: theme.colors.surfaceSecondary, alignSelf: 'flex-start', maxWidth: '100%', borderBottomLeftRadius: 4, borderWidth: 1, borderColor: theme.colors.border },
  msgHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: theme.spacing.xs },
  msgRole: { fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  userRole: { color: theme.colors.brandSecondary },
  aiRole: { color: theme.colors.brand },
  msgText: { fontSize: 15, lineHeight: 22 },
  userText: { color: theme.colors.onBrandPrimary },
  aiText: { color: theme.colors.onSurface },
  inputBar: { flexDirection: 'row', alignItems: 'flex-end', padding: theme.spacing.md, gap: theme.spacing.sm, borderTopWidth: 1, borderTopColor: theme.colors.divider, backgroundColor: theme.colors.surface },
  input: { flex: 1, minHeight: 48, maxHeight: 120, borderRadius: theme.radius.lg, backgroundColor: theme.colors.surfaceSecondary, paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.md, paddingBottom: theme.spacing.md, color: theme.colors.onSurface, fontSize: 15, borderWidth: 1, borderColor: theme.colors.border },
  mic: { width: 52, height: 52, borderRadius: 26, backgroundColor: theme.colors.brandSecondary, alignItems: 'center', justifyContent: 'center' },
  micActive: { backgroundColor: theme.colors.error },
  send: { width: 52, height: 52, borderRadius: 26, backgroundColor: theme.colors.brand, alignItems: 'center', justifyContent: 'center' },
  proBadge: { flexDirection: 'row', alignItems: 'center', gap: 2, backgroundColor: theme.colors.brandSecondary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: theme.radius.pill },
  proBadgeText: { color: theme.colors.onBrandSecondary, fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  banner: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm, padding: theme.spacing.md, backgroundColor: '#FFF6E5', borderBottomWidth: 1, borderBottomColor: '#F0D68A' },
  bannerText: { flex: 1, color: '#7A4C00', fontSize: 12, lineHeight: 16 },
  upgradeBanner: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm, backgroundColor: theme.colors.brandSecondary, paddingHorizontal: theme.spacing.lg, paddingVertical: theme.spacing.md },
  upgradeBannerText: { flex: 1, color: theme.colors.onBrandSecondary, fontWeight: '700', fontSize: 13 },
});
