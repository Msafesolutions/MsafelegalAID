/**
 * Visitor Mode — Two-Way Interpreter
 * Tourist ↔ Hindi live translation via Whisper STT + Claude Haiku TTS.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View, Text, Pressable, StyleSheet, ScrollView,
  ActivityIndicator, Alert, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Speech from 'expo-speech';
import { theme } from '@/src/theme';
import { loadVisitorSession, VisitorSession } from '@/src/visitor/session';
import { API_BASE, useAuth } from '@/src/auth';
import { whisperTranscribeFile, sttErrorToMessage } from '@/src/voice/stt';

const C = theme.colors;

type Mode = 'tourist' | 'official';
type Turn = { speaker: Mode; original: string; translated: string };
type Phase = 'idle' | 'recording' | 'transcribing' | 'translating' | 'speaking';

// Whisper language hint — map tourist ISO 639-1 to BCP-47 for recording hint
const ISO_TO_BCP47: Record<string, string> = {
  en: 'en', fr: 'fr', de: 'de', es: 'es', pt: 'pt', it: 'it',
  ja: 'ja', ko: 'ko', zh: 'zh', ar: 'ar', ru: 'ru', hi: 'hi',
};

export default function InterpreterScreen() {
  const { token } = useAuth();
  const [session, setSession] = useState<VisitorSession | null>(null);
  const [mode, setMode] = useState<Mode>('tourist');
  const [phase, setPhase] = useState<Phase>('idle');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [currentTranslation, setCurrentTranslation] = useState('');
  const [statusText, setStatusText] = useState('');
  const scrollRef = useRef<ScrollView>(null);

  // expo-audio recorder ref (loaded lazily)
  const recorderRef = useRef<any>(null);
  const audioModRef = useRef<any>(null);

  useEffect(() => {
    loadVisitorSession().then(s => setSession(s));
    // Pre-load expo-audio
    import('expo-audio').then(m => { audioModRef.current = m; }).catch(() => {});
  }, []);

  const touristLang = session?.touristLang.code || 'en';
  const touristLangName = session?.touristLang.label || 'English';

  // Determine source / target lang for each mode
  const srcLang = mode === 'tourist' ? touristLang : 'hi';
  const tgtLang = mode === 'tourist' ? 'hi' : touristLang;
  const srcLabel = mode === 'tourist' ? touristLangName : 'Hindi';
  const tgtLabel = mode === 'tourist' ? 'Hindi' : touristLangName;

  // ── Translate via backend ─────────────────────────────────────────────────
  const translateText = useCallback(async (text: string, src: string, tgt: string): Promise<string> => {
    const res = await fetch(`${API_BASE}/api/visitor/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text, source_lang: src, target_lang: tgt }),
    });
    if (!res.ok) throw new Error('Translation failed');
    const data = await res.json();
    return data.translated_text || '';
  }, [token]);

  // ── TTS playback ──────────────────────────────────────────────────────────
  // Native (iOS/Android): expo-speech speaks the translated text directly —
  // avoids window.Audio which is browser-only and silent on APK builds.
  // Web: fall back to the backend TTS endpoint + HTMLAudioElement.
  const playTTS = useCallback(async (text: string, lang: string) => {
    if (Platform.OS !== 'web') {
      // Map ISO 639-1 to a BCP-47 tag expo-speech understands (e.g. 'hi' → 'hi-IN')
      const bcp47: Record<string, string> = {
        hi: 'hi-IN', en: 'en-IN', fr: 'fr-FR', de: 'de-DE',
        es: 'es-ES', pt: 'pt-PT', it: 'it-IT', ja: 'ja-JP',
        ko: 'ko-KR', zh: 'zh-CN', ar: 'ar-SA', ru: 'ru-RU',
      };
      return new Promise<void>((resolve) => {
        Speech.stop(); // stop any previous utterance
        Speech.speak(text, {
          language: bcp47[lang] ?? lang,
          onDone:  () => resolve(),
          onError: () => resolve(), // never block the conversation on TTS error
        });
      });
    }
    // Web fallback: stream from backend TTS endpoint
    const res = await fetch(`${API_BASE}/api/voice/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text, language: lang, voice: 'alloy' }),
    });
    if (!res.ok) throw new Error('TTS failed');
    const blob = await res.blob();
    return new Promise<void>((resolve, reject) => {
      const url = URL.createObjectURL(blob);
      const audio = new (window as any).Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
      audio.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Audio playback failed')); };
      audio.play().catch(reject);
    });
  }, [token]);

  // ── Main recording + translation flow ────────────────────────────────────
  const startRecording = useCallback(async () => {
    if (!token) { Alert.alert('Sign in required', 'Sign in to DHARA to use Interpreter.'); return; }
    const mod = audioModRef.current;
    if (!mod) { Alert.alert('Not available', 'expo-audio not loaded.'); return; }

    try {
      const perm = await mod.AudioModule.requestRecordingPermissionsAsync();
      if (!perm.granted) { Alert.alert('Microphone permission denied'); return; }
      await mod.setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });

      // Fallback: use RecordingPresets if direct recorder API is available
      const rec = new mod.Recording();
      await rec.prepareToRecordAsync(mod.RecordingOptionsPresets?.HIGH_QUALITY || {
        android: { extension: '.m4a', outputFormat: 2, audioEncoder: 3, sampleRate: 16000, numberOfChannels: 1, bitRate: 128000 },
        ios:     { extension: '.m4a', outputFormat: 'aac', audioQuality: 127, sampleRate: 16000, numberOfChannels: 1, bitRate: 128000, linearPCMBitDepth: 16, linearPCMIsBigEndian: false, linearPCMIsFloat: false },
        web:     { mimeType: 'audio/webm', bitsPerSecond: 128000 },
      });
      await rec.startAsync();
      recorderRef.current = rec;
      setPhase('recording');
      setStatusText(`Recording ${srcLabel}… (tap stop when done)`);
      setCurrentTranscript('');
      setCurrentTranslation('');
    } catch (e: any) {
      Alert.alert('Recording error', e?.message || String(e));
    }
  }, [token, srcLabel]);

  const stopAndProcess = useCallback(async () => {
    const rec = recorderRef.current;
    if (!rec) return;
    setPhase('transcribing');
    setStatusText('Transcribing…');
    try {
      await rec.stopAndUnloadAsync();
      const uri = rec.getURI?.() || '';
      recorderRef.current = null;

      if (!uri) throw new Error('No recording URI');
      const langHint = ISO_TO_BCP47[srcLang] || 'en';
      const { text } = await whisperTranscribeFile(API_BASE, token!, uri, langHint);
      setCurrentTranscript(text);

      setPhase('translating');
      setStatusText('Translating…');
      const translated = await translateText(text, srcLang, tgtLang);
      setCurrentTranslation(translated);

      setPhase('speaking');
      setStatusText(`Playing ${tgtLabel}…`);
      await playTTS(translated, tgtLang);

      const turn: Turn = { speaker: mode, original: text, translated };
      setTurns(prev => [...prev, turn]);
      setPhase('idle');
      setStatusText('');
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (e: any) {
      setPhase('idle');
      setStatusText('');
      Alert.alert('Voice error', sttErrorToMessage(e));
    }
  }, [mode, srcLang, tgtLang, tgtLabel, token, translateText, playTTS]);

  const cancelRecording = useCallback(async () => {
    const rec = recorderRef.current;
    if (rec) {
      try { await rec.stopAndUnloadAsync(); } catch {}
      recorderRef.current = null;
    }
    setPhase('idle');
    setStatusText('');
  }, []);

  if (!session) {
    return (
      <SafeAreaView style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={C.primary} />
      </SafeAreaView>
    );
  }

  const isRecording = phase === 'recording';
  const isBusy = phase !== 'idle' && phase !== 'recording';

  return (
    <SafeAreaView style={s.safe} edges={['bottom']}>
      {/* Header */}
      <View style={s.header}>
        <View style={s.langBadge}>
          <Text style={s.langBadgeText}>{touristLangName}</Text>
          <Ionicons name="swap-horizontal" size={16} color={C.gold} />
          <Text style={s.langBadgeText}>Hindi</Text>
        </View>
        <Text style={s.headerSub}>Tap mic → speak → plays translation</Text>
      </View>

      {/* Mode toggle */}
      <View style={s.modeRow}>
        {(['tourist', 'official'] as Mode[]).map(m => (
          <Pressable
            key={m}
            style={[s.modeBtn, mode === m && s.modeBtnActive]}
            onPress={() => { if (phase === 'idle') setMode(m); }}
            disabled={phase !== 'idle'}
          >
            <Ionicons
              name={m === 'tourist' ? 'person-outline' : 'shield-checkmark-outline'}
              size={16}
              color={mode === m ? '#fff' : C.onSurfaceTertiary}
            />
            <Text style={[s.modeBtnText, mode === m && s.modeBtnTextActive]}>
              {m === 'tourist' ? `I speak (${touristLangName})` : 'Official speaks (Hindi)'}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Conversation history */}
      <ScrollView ref={scrollRef} style={s.history} contentContainerStyle={s.historyContent}>
        {turns.length === 0 && (
          <View style={s.emptyHint}>
            <Ionicons name="language-outline" size={40} color={C.border} />
            <Text style={s.emptyText}>Conversation will appear here</Text>
          </View>
        )}
        {turns.map((turn, i) => (
          <View key={i} style={[s.bubble, turn.speaker === 'tourist' ? s.bubbleTourist : s.bubbleOfficial]}>
            <Text style={s.bubbleLabel}>
              {turn.speaker === 'tourist' ? `${touristLangName} → Hindi` : `Hindi → ${touristLangName}`}
            </Text>
            <Text style={s.bubbleOriginal}>{turn.original}</Text>
            <View style={s.bubbleDivider} />
            <Text style={s.bubbleTranslated}>{turn.translated}</Text>
          </View>
        ))}

        {/* Live status */}
        {(currentTranscript || currentTranslation || statusText) && (
          <View style={s.liveCard}>
            {statusText ? <Text style={s.liveStatus}>{statusText}</Text> : null}
            {currentTranscript ? <Text style={s.liveTranscript}>{currentTranscript}</Text> : null}
            {currentTranslation ? (
              <Text style={s.liveTranslation}>{currentTranslation}</Text>
            ) : null}
          </View>
        )}
      </ScrollView>

      {/* Mic button */}
      <View style={s.micRow}>
        {isRecording ? (
          <>
            <Pressable style={s.cancelBtn} onPress={cancelRecording}>
              <Ionicons name="close" size={22} color={C.error} />
            </Pressable>
            <Pressable style={[s.micBtn, s.micBtnRecording]} onPress={stopAndProcess}>
              <Ionicons name="stop" size={36} color="#fff" />
            </Pressable>
          </>
        ) : (
          <Pressable
            style={[s.micBtn, isBusy && s.micBtnDisabled]}
            onPress={startRecording}
            disabled={isBusy}
          >
            {isBusy
              ? <ActivityIndicator size="large" color="#fff" />
              : <Ionicons name="mic" size={36} color="#fff" />}
          </Pressable>
        )}
      </View>
      <Text style={s.micHint}>
        {isRecording
          ? `Speaking in ${srcLabel} → tap ■ to stop`
          : isBusy ? statusText
          : `Tap mic · ${srcLabel} → ${tgtLabel}`}
      </Text>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.background },

  header: { padding: 16, alignItems: 'center', borderBottomWidth: 1, borderBottomColor: C.divider },
  langBadge: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 4 },
  langBadgeText: { fontSize: 16, fontWeight: '800', color: C.primary },
  headerSub:     { fontSize: 12, color: C.onSurfaceTertiary },

  modeRow:          { flexDirection: 'row', gap: 8, padding: 12, paddingBottom: 8 },
  modeBtn:          {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 8,
    backgroundColor: C.surface, borderWidth: 1, borderColor: C.border,
  },
  modeBtnActive:    { backgroundColor: C.primary, borderColor: C.primary },
  modeBtnText:      { fontSize: 12, fontWeight: '600', color: C.onSurfaceTertiary },
  modeBtnTextActive:{ color: '#fff' },

  history:        { flex: 1 },
  historyContent: { padding: 12, paddingBottom: 8 },

  emptyHint: { alignItems: 'center', paddingVertical: 40, gap: 10 },
  emptyText: { fontSize: 13, color: C.border },

  bubble:          { borderRadius: 14, padding: 14, marginBottom: 10, maxWidth: '90%' },
  bubbleTourist:   { backgroundColor: C.navySoft, alignSelf: 'flex-end' },
  bubbleOfficial:  { backgroundColor: '#F0FFF4', alignSelf: 'flex-start', borderWidth: 1, borderColor: '#A7F3D0' },
  bubbleLabel:     { fontSize: 10, fontWeight: '700', color: C.onSurfaceTertiary, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 },
  bubbleOriginal:  { fontSize: 14, color: C.onSurface, lineHeight: 20 },
  bubbleDivider:   { height: 1, backgroundColor: C.divider, marginVertical: 6 },
  bubbleTranslated:{ fontSize: 14, color: C.primary, fontWeight: '600', lineHeight: 20 },

  liveCard: {
    backgroundColor: C.surface, borderRadius: 14, padding: 14,
    borderWidth: 1, borderColor: C.border, marginBottom: 8, gap: 6,
  },
  liveStatus:     { fontSize: 12, color: C.onSurfaceTertiary, fontStyle: 'italic' },
  liveTranscript: { fontSize: 14, color: C.onSurface },
  liveTranslation:{ fontSize: 14, color: '#059669', fontWeight: '700' },

  micRow:          { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 12, gap: 20 },
  micBtn:          {
    width: 80, height: 80, borderRadius: 40, backgroundColor: C.primary,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: C.primary, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 8,
  },
  micBtnRecording: { backgroundColor: C.error },
  micBtnDisabled:  { backgroundColor: C.border },
  cancelBtn:       {
    width: 48, height: 48, borderRadius: 24, backgroundColor: C.surface,
    alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: C.error,
  },
  micHint: { fontSize: 12, color: C.onSurfaceTertiary, textAlign: 'center', paddingBottom: 16 },
});
