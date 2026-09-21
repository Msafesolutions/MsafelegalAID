/**
 * Voice FIR Drafting Assistant — Intake Flow
 * Citizen describes an incident by voice; produces a print-ready FIR draft.
 *
 * - 10 guided questions, each capturable by voice or typed text
 * - Persists draft locally (AsyncStorage) for offline-tolerant resume
 * - Syncs to backend fir_drafts collection when connected
 * - Phase 3 safety branch fires after the main narrative step
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, StyleSheet,
  ActivityIndicator, Platform, Alert, KeyboardAvoidingView, Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth, API_BASE } from '@/src/auth';
import {
  useAudioRecorder, RecordingPresets, setAudioModeAsync, AudioModule,
} from 'expo-audio';
import { whisperTranscribeFile } from '@/src/voice/stt';
import { File, Paths } from 'expo-file-system';

const NAVY  = '#14365A';
const GOLD  = '#D3B675';
const RED   = '#DC2626';
const GREEN = '#059669';

const FIR_LANG_KEY = 'fir_draft_lang';

// ─── Language options for FIR (3 required + English) ──────────────────────
const FIR_LANGUAGES = [
  { code: 'en', label: 'English',  native: 'English',  sttLang: 'en-IN' },
  { code: 'hi', label: 'Hindi',    native: 'हिन्दी',   sttLang: 'hi-IN' },
  { code: 'mr', label: 'Marathi',  native: 'मराठी',    sttLang: 'mr-IN' },
  { code: 'ta', label: 'Tamil',    native: 'தமிழ்',    sttLang: 'ta-IN' },
];

// ─── 10 guided questions ──────────────────────────────────────────────────
const QUESTIONS = [
  {
    id: 'incident_type',
    label: 'What type of incident do you want to report?',
    hint: 'e.g., theft, assault, cheating, domestic violence, cybercrime…',
    type: 'text' as const,
    required: true,
  },
  {
    id: 'what_happened',
    label: 'Describe what happened in as much detail as possible.',
    hint: 'Who did what? Speak freely — you can edit afterwards.',
    type: 'textarea' as const,
    required: true,
    voicePrompt: true,  // primary voice question
  },
  {
    id: 'incident_datetime',
    label: 'When did the incident happen?',
    hint: 'Date, time, and day if you remember. e.g., 10 June 2026, around 8 PM, Monday',
    type: 'text' as const,
    required: true,
  },
  {
    id: 'location',
    label: 'Where did it happen?',
    hint: 'Area / locality / city in Maharashtra. e.g., Dadar, Mumbai',
    type: 'text' as const,
    required: true,
  },
  {
    id: 'accused',
    label: 'Do you know who did this? Describe the person(s) involved.',
    hint: 'Name, relationship, description — or "Not known"',
    type: 'textarea' as const,
    required: false,
  },
  {
    id: 'injury_loss',
    label: 'Was anyone injured, or was any property taken/damaged?',
    hint: 'Describe injuries and estimated value of loss. Say "None" if not applicable.',
    type: 'textarea' as const,
    required: false,
  },
  {
    id: 'witnesses',
    label: 'Were there any witnesses?',
    hint: 'Names and contact numbers if available. Say "None" if not applicable.',
    type: 'text' as const,
    required: false,
  },
  {
    id: 'evidence',
    label: 'What evidence do you have?',
    hint: 'Photos, videos, messages, medical certificate, receipts, CCTV…',
    type: 'text' as const,
    required: false,
  },
  {
    id: 'informant_name',
    label: 'Your full name (as it will appear on the FIR)',
    hint: 'This is the name of the person filing the complaint.',
    type: 'text' as const,
    required: true,
  },
  {
    id: 'informant_contact',
    label: 'Your address and contact number',
    hint: 'Address and mobile number for the police to reach you.',
    type: 'text' as const,
    required: true,
  },
];

// ─── Safety Card component ─────────────────────────────────────────────────
function SafetyCard({ flags, onContinue }: { flags: string[]; onContinue: () => void }) {
  const isPOCSO = flags.includes('POCSO');
  const isSexual = flags.includes('SEXUAL');
  const isDV = flags.includes('DV');

  return (
    <View style={sc.card}>
      <View style={sc.header}>
        <Ionicons name="alert-circle" size={28} color={RED} />
        <Text style={sc.title}>Important: Helplines & Legal Aid</Text>
      </View>
      <Text style={sc.body}>
        Based on your description, this may involve {isPOCSO ? 'child abuse (POCSO)' : isSexual ? 'sexual violence' : 'domestic violence'}.
        {'\n\n'}Please contact these services <Text style={{ fontWeight: '800' }}>FIRST</Text> — they provide free, confidential support:
      </Text>
      {(isPOCSO) && (
        <View style={sc.helpline}>
          <Ionicons name="call" size={18} color={RED} />
          <View style={{ flex: 1 }}>
            <Text style={sc.helplineTitle}>Childline — 1098 (24×7 FREE)</Text>
            <Text style={sc.helplineSub}>For children in distress. Mandatory reporting under POCSO Act.</Text>
          </View>
        </View>
      )}
      {(isSexual || isDV) && (
        <View style={sc.helpline}>
          <Ionicons name="call" size={18} color={RED} />
          <View style={{ flex: 1 }}>
            <Text style={sc.helplineTitle}>Women Helpline — 181 (24×7 FREE)</Text>
            <Text style={sc.helplineSub}>Women in distress, domestic violence, sexual assault.</Text>
          </View>
        </View>
      )}
      <View style={sc.helpline}>
        <Ionicons name="briefcase-outline" size={18} color={NAVY} />
        <View style={{ flex: 1 }}>
          <Text style={sc.helplineTitle}>NALSA Legal Aid — 15100 (toll-free)</Text>
          <Text style={sc.helplineSub}>Free legal advice and lawyer referral. Available 24×7.</Text>
        </View>
      </View>
      <View style={sc.helpline}>
        <Ionicons name="shield-checkmark-outline" size={18} color={NAVY} />
        <View style={{ flex: 1 }}>
          <Text style={sc.helplineTitle}>Zero FIR Right</Text>
          <Text style={sc.helplineSub}>You can file an FIR at ANY police station. They must accept it under Section 173(1) BNSS.</Text>
        </View>
      </View>
      <Pressable style={sc.btn} onPress={onContinue}>
        <Text style={sc.btnText}>I have noted this — Continue to FIR Draft</Text>
      </Pressable>
    </View>
  );
}

// ─── Main Screen ──────────────────────────────────────────────────────────
export default function FIRDraftIntake() {
  const { token, user } = useAuth();
  const router = useRouter();

  const [step, setStep]         = useState(0);  // 0 = lang select, 1-10 = questions
  const [lang, setLang]         = useState('en');
  const [answers, setAnswers]   = useState<Record<string, string>>({});
  const [draftId, setDraftId]   = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [syncing, setSyncing]   = useState(false);
  const [safetyFlags, setSafetyFlags] = useState<string[]>([]);
  const [showSafety, setShowSafety] = useState(false);
  const [safetyAcknowledged, setSafetyAcknowledged] = useState(false);

  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);

  // Restore in-progress draft from local storage
  useEffect(() => {
    AsyncStorage.getItem('fir_draft_state').then(raw => {
      if (raw) {
        try {
          const saved = JSON.parse(raw);
          if (saved.userId === user?.id) {
            setAnswers(saved.answers || {});
            setDraftId(saved.draftId || null);
            setLang(saved.lang || 'en');
            setStep(saved.step || 0);
          }
        } catch {}
      }
    });
  }, [user?.id]);

  // Auto-save to local storage on every change
  useEffect(() => {
    AsyncStorage.setItem('fir_draft_state', JSON.stringify({
      userId: user?.id, answers, draftId, lang, step,
    })).catch(() => {});
  }, [answers, draftId, lang, step, user?.id]);

  const syncToBackend = useCallback(async (updatedAnswers: Record<string, string>, status = 'in_progress') => {
    if (!token || !user?.id) return;
    setSyncing(true);
    try {
      const r = await fetch(`${API_BASE}/api/fir/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ draft_id: draftId, user_id: user.id, language: lang, answers: updatedAnswers, status }),
      }).catch(() => null);
      if (r?.ok) {
        const d = await r.json();
        if (d.draft_id && !draftId) setDraftId(d.draft_id);
      }
    } catch {} finally { setSyncing(false); }
  }, [token, user?.id, draftId, lang]);

  const startRecording = async () => {
    try {
      await AudioModule.requestRecordingPermissionsAsync();
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.record();
      setIsRecording(true);
    } catch (e) {
      Alert.alert('Microphone Error', 'Cannot access microphone. Please check permissions.');
    }
  };

  const stopAndTranscribe = async (qId: string) => {
    if (!isRecording) return;
    setIsRecording(false);
    setTranscribing(true);
    try {
      const uri = await recorder.stop();
      if (!uri) { setTranscribing(false); return; }

      const sttLang = FIR_LANGUAGES.find(l => l.code === lang)?.sttLang ?? 'en-IN';
      const tempFile = new File(Paths.cache, `fir_q_${Date.now()}.m4a`);
      // Transcribe
      const result = await whisperTranscribeFile(uri, token ?? '', sttLang);
      const text = typeof result === 'string' ? result : (result as any)?.transcript ?? '';
      if (text) {
        setAnswers(prev => ({ ...prev, [qId]: (prev[qId] ? prev[qId] + ' ' : '') + text.trim() }));
      }
    } catch {
      Alert.alert('Transcription Error', 'Could not transcribe. Please type your answer.');
    } finally {
      setTranscribing(false);
      setAudioModeAsync({ allowsRecording: false, playsInSilentMode: false }).catch(() => {});
    }
  };

  const checkSafety = async (narrative: string) => {
    if (safetyAcknowledged) return;
    try {
      const r = await fetch(`${API_BASE}/api/fir/classify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ narrative }),
      }).catch(() => null);
      if (r?.ok) {
        const d = await r.json();
        const flags: string[] = d?.classification?.safety_flags ?? [];
        if (flags.length > 0) {
          setSafetyFlags(flags);
          setShowSafety(true);
        }
      }
    } catch {}
  };

  const nextStep = async () => {
    if (step === 0) {
      // Lang selected
      setStep(1);
      return;
    }
    const q = QUESTIONS[step - 1];
    if (q.required && !answers[q.id]?.trim()) {
      Alert.alert('Required', `Please answer: "${q.label}"`);
      return;
    }
    // After "what happened" (question 2, step 2), run safety check
    if (q.id === 'what_happened' && !safetyAcknowledged) {
      await checkSafety(answers['what_happened'] ?? '');
    }
    // Sync to backend (best-effort, no block)
    syncToBackend(answers).catch(() => {});

    if (step >= QUESTIONS.length) {
      // Done — go to result
      await syncToBackend(answers, 'completed');
      router.push({ pathname: '/fir-draft/result', params: { draftId: draftId ?? '', lang } } as any);
    } else {
      setStep(s => s + 1);
    }
  };

  const currentQ = step > 0 ? QUESTIONS[step - 1] : null;
  const progress = step === 0 ? 0 : step / QUESTIONS.length;

  if (showSafety && !safetyAcknowledged) {
    return (
      <SafeAreaView style={s.safe}>
        <View style={s.header}>
          <Pressable onPress={() => router.back()} style={{ marginRight: 12 }}>
            <Ionicons name="arrow-back" size={22} color="#fff" />
          </Pressable>
          <Text style={s.headerTitle}>Safety First</Text>
        </View>
        <ScrollView contentContainerStyle={{ padding: 16 }}>
          <SafetyCard
            flags={safetyFlags}
            onContinue={() => { setSafetyAcknowledged(true); setShowSafety(false); }}
          />
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <SafeAreaView style={s.safe}>
        {/* Header */}
        <View style={s.header}>
          <Pressable onPress={() => step > 0 ? setStep(s => s - 1) : router.back()} style={{ marginRight: 12 }}>
            <Ionicons name={step > 0 ? 'chevron-back' : 'arrow-back'} size={22} color="#fff" />
          </Pressable>
          <View style={{ flex: 1 }}>
            <Text style={s.headerTitle}>FIR Draft Assistant</Text>
            <Text style={s.headerSub}>Powered by DHARA AI</Text>
          </View>
          {syncing && <ActivityIndicator size="small" color={GOLD} />}
        </View>

        {/* Progress */}
        {step > 0 && (
          <View style={s.progressWrap}>
            <View style={[s.progressBar, { width: `${progress * 100}%` }]} />
            <Text style={s.progressLabel}>Step {step} of {QUESTIONS.length}</Text>
          </View>
        )}

        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          {step === 0 ? (
            // Language selection
            <View style={{ gap: 16 }}>
              <View style={s.introCard}>
                <Ionicons name="document-text-outline" size={40} color={GOLD} />
                <Text style={s.introTitle}>Voice FIR Draft Assistant</Text>
                <Text style={s.introBody}>
                  Describe your incident by voice. DHARA will generate a ready-to-present FIR draft with the correct BNS sections and suggest your nearest police station.
                </Text>
                <View style={s.disclaimer}>
                  <Ionicons name="information-circle-outline" size={16} color="#6B7280" />
                  <Text style={s.disclaimerText}>
                    This is a citizen draft — NOT a registered FIR. Accuracy of suggested sections depends on your description.
                    <Text style={{ color: RED }}> [Disclaimer pending legal counsel review]</Text>
                  </Text>
                </View>
              </View>
              <Text style={s.sectionLabel}>Select your language</Text>
              {FIR_LANGUAGES.map(l => (
                <Pressable key={l.code} style={[s.langCard, lang === l.code && s.langCardActive]} onPress={() => setLang(l.code)}>
                  <Text style={[s.langCardLabel, lang === l.code && { color: NAVY }]}>{l.native}</Text>
                  <Text style={s.langCardSub}>{l.label}</Text>
                  {lang === l.code && <Ionicons name="checkmark-circle" size={22} color={NAVY} />}
                </Pressable>
              ))}
              <Pressable style={s.nextBtn} onPress={nextStep}>
                <Text style={s.nextBtnText}>Start — Describe Incident</Text>
                <Ionicons name="arrow-forward" size={20} color="#fff" />
              </Pressable>
            </View>
          ) : currentQ ? (
            <View style={{ gap: 14 }}>
              <View style={s.questionCard}>
                <Text style={s.questionLabel}>
                  {currentQ.label}
                  {currentQ.required && <Text style={{ color: RED }}> *</Text>}
                </Text>
                {currentQ.hint ? <Text style={s.questionHint}>{currentQ.hint}</Text> : null}
              </View>

              {/* Voice button + TextInput */}
              <View style={{ gap: 8 }}>
                {Platform.OS !== 'web' && (
                  <Pressable
                    style={[s.voiceBtn, isRecording && s.voiceBtnActive]}
                    onPress={isRecording ? () => stopAndTranscribe(currentQ.id) : startRecording}
                    disabled={transcribing}
                  >
                    {transcribing
                      ? <><ActivityIndicator color="#fff" size="small" /><Text style={s.voiceBtnText}>Transcribing…</Text></>
                      : isRecording
                        ? <><Ionicons name="stop-circle" size={24} color="#fff" /><Text style={s.voiceBtnText}>Tap to Stop &amp; Transcribe</Text></>
                        : <><Ionicons name="mic" size={24} color={NAVY} /><Text style={[s.voiceBtnText, { color: NAVY }]}>Hold to Speak</Text></>
                    }
                  </Pressable>
                )}
                <TextInput
                  style={[s.input, currentQ.type === 'textarea' && s.textarea]}
                  value={answers[currentQ.id] ?? ''}
                  onChangeText={t => setAnswers(prev => ({ ...prev, [currentQ.id]: t }))}
                  placeholder={currentQ.hint}
                  placeholderTextColor="#9CA3AF"
                  multiline={currentQ.type === 'textarea'}
                  numberOfLines={currentQ.type === 'textarea' ? 5 : 1}
                  textAlignVertical={currentQ.type === 'textarea' ? 'top' : 'center'}
                />
              </View>

              <Pressable style={s.nextBtn} onPress={nextStep}>
                <Text style={s.nextBtnText}>{step >= QUESTIONS.length ? 'Generate FIR Draft' : 'Next'}</Text>
                <Ionicons name={step >= QUESTIONS.length ? 'document-text' : 'arrow-forward'} size={20} color="#fff" />
              </Pressable>
            </View>
          ) : null}
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const sc = StyleSheet.create({
  card: { backgroundColor: '#FEF2F2', borderRadius: 16, padding: 20, gap: 14, borderWidth: 2, borderColor: '#FCA5A5' },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 4 },
  title: { fontSize: 18, fontWeight: '800', color: RED, flex: 1 },
  body: { fontSize: 14, color: '#374151', lineHeight: 22 },
  helpline: { flexDirection: 'row', gap: 12, alignItems: 'flex-start', backgroundColor: '#fff', borderRadius: 10, padding: 12 },
  helplineTitle: { fontSize: 14, fontWeight: '700', color: '#1F2937' },
  helplineSub: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  btn: { backgroundColor: NAVY, borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginTop: 4 },
  btnText: { color: '#fff', fontWeight: '800', fontSize: 15 },
});

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F9FAFB' },
  header: { backgroundColor: NAVY, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14, gap: 12 },
  headerTitle: { fontSize: 17, fontWeight: '800', color: '#fff' },
  headerSub: { fontSize: 11, color: GOLD },
  progressWrap: { height: 6, backgroundColor: '#E5E7EB', position: 'relative' },
  progressBar: { height: 6, backgroundColor: GOLD, position: 'absolute', left: 0, top: 0 },
  progressLabel: { display: 'none' },
  scroll: { padding: 20, paddingBottom: 40, gap: 0 },
  introCard: { backgroundColor: NAVY, borderRadius: 16, padding: 24, alignItems: 'center', gap: 12 },
  introTitle: { fontSize: 20, fontWeight: '800', color: '#fff', textAlign: 'center' },
  introBody: { fontSize: 14, color: '#D1D5DB', textAlign: 'center', lineHeight: 22 },
  disclaimer: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 10, padding: 12 },
  disclaimerText: { fontSize: 11, color: '#D1D5DB', flex: 1, lineHeight: 18 },
  sectionLabel: { fontSize: 15, fontWeight: '700', color: '#1F2937', marginTop: 8 },
  langCard: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16, borderRadius: 12, borderWidth: 1.5, borderColor: '#E5E7EB', backgroundColor: '#fff' },
  langCardActive: { borderColor: NAVY, backgroundColor: '#EEF2FF' },
  langCardLabel: { fontSize: 20, color: '#374151', flex: 1 },
  langCardSub: { fontSize: 13, color: '#6B7280' },
  questionCard: { backgroundColor: NAVY, borderRadius: 14, padding: 20, gap: 8 },
  questionLabel: { fontSize: 17, fontWeight: '800', color: '#fff', lineHeight: 26 },
  questionHint: { fontSize: 13, color: GOLD, lineHeight: 20 },
  voiceBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 16, borderRadius: 12, borderWidth: 2, borderColor: NAVY, backgroundColor: '#F0F4FF' },
  voiceBtnActive: { backgroundColor: RED, borderColor: RED },
  voiceBtnText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  input: { backgroundColor: '#fff', borderWidth: 1.5, borderColor: '#D1D5DB', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, color: '#1F2937', marginTop: 8 },
  textarea: { minHeight: 120, paddingTop: 14 },
  nextBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, backgroundColor: NAVY, borderRadius: 14, paddingVertical: 16, marginTop: 8 },
  nextBtnText: { fontSize: 16, fontWeight: '800', color: '#fff' },
});
