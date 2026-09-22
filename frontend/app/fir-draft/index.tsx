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
  ActivityIndicator, Platform, Alert, KeyboardAvoidingView, Modal, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth, API_BASE } from '@/src/auth';
import { t } from '@/src/i18n';
import {
  useAudioRecorder, RecordingPresets, setAudioModeAsync, AudioModule,
} from 'expo-audio';
import { whisperTranscribeFile } from '@/src/voice/stt';
// expo-file-system Paths removed (was used by dead code in stopAndTranscribe)

const NAVY  = '#14365A';
const GOLD  = '#D3B675';
const RED   = '#DC2626';
const GREEN = '#059669';

// Lightweight id generator for anonymous (not-logged-in) citizens using the
// FIR flow — no external uuid dependency needed for this local-only id.
function uuidv4Ish(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

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
    hint: 'Area / locality / city / state. e.g., Dadar, Mumbai or Panaji, Goa',
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
    id: 'informant_address',
    label: 'Your full address',
    hint: 'House/flat no., street, area, city, PIN code. e.g., 12 MG Road, Andheri West, Mumbai 400058',
    type: 'textarea' as const,
    required: true,
  },
  {
    id: 'informant_phone',
    label: 'Your contact number',
    hint: 'Mobile number the police can reach you on. e.g., 98765 43210',
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
  const { token, user, language } = useAuth();
  const router = useRouter();

  const [step, setStep]         = useState(0);  // 0 = lang select, 1-10 = questions
  const [lang, setLang]         = useState(() => language?.code || 'en');
  const [answers, setAnswers]   = useState<Record<string, string>>({});
  const [draftId, setDraftId]   = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [syncing, setSyncing]   = useState(false);
  const [safetyFlags, setSafetyFlags] = useState<string[]>([]);
  const [showSafety, setShowSafety] = useState(false);
  const [safetyAcknowledged, setSafetyAcknowledged] = useState(false);
  const [anonId, setAnonId] = useState<string | null>(null);
  const effectiveUserId = user?.id ?? anonId;

  // Full language list — fetched from API on mount, falls back to FIR_LANGUAGES
  const [firLanguages, setFirLanguages] = useState(FIR_LANGUAGES);

  // Voice-first input mode: 'voice' (mic idle) | 'text' (keyboard) | 'review' (post-transcription)
  const [inputMode, setInputMode] = useState<'voice' | 'text' | 'review'>('voice');
  // Global preferred input mode — persists across wizard steps so the user
  // doesn't have to tap "Type instead" on every question after choosing text once.
  const [preferredInputMode, setPreferredInputMode] = useState<'voice' | 'text'>('voice');
  const [reviewText, setReviewText] = useState('');
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const answersRef = useRef(answers);

  // Fix 1: VAD silence timer
  const [stillListening, setStillListening] = useState(false);
  const silenceTimerRef = useRef<any>(null);

  // Fix 2: LLM follow-up state
  const [followUpState, setFollowUpState] = useState<{
    question: string; parentQId: string; answer: string;
  } | null>(null);
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const followUpCheckedRef = useRef<Set<string>>(new Set());

  // ── Web Speech API (browser only) ─────────────────────────────────────
  const webRecognitionRef = useRef<any>(null);
  const [liveTranscript, setLiveTranscript] = useState('');

  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);

  useEffect(() => {
    if (user?.id) return;
    AsyncStorage.getItem('fir_anon_id').then(async existing => {
      if (existing) { setAnonId(existing); return; }
      const id = `anon-${uuidv4Ish()}`;
      await AsyncStorage.setItem('fir_anon_id', id).catch(() => {});
      setAnonId(id);
    });
  }, [user?.id]);

  // Restore in-progress draft from local storage; default lang to user's preference
  useEffect(() => {
    AsyncStorage.getItem('fir_draft_state').then(raw => {
      if (raw) {
        try {
          const saved = JSON.parse(raw);
          if (saved.userId === user?.id) {
            setAnswers(saved.answers || {});
            setDraftId(saved.draftId || null);
            // Only restore the saved language if the user has already moved
            // past the language-selection screen (step > 0). If they never
            // clicked "Start", use the current global language preference so
            // Settings changes are always reflected on a fresh visit.
            const restoredLang = (saved.step > 0 && saved.lang) ? saved.lang : (language?.code || 'en');
            setLang(restoredLang);
            setStep(saved.step || 0);
          }
        } catch {}
      }
    });
  }, [user?.id, language?.code]);

  // Fix 3: Fetch full language list from the API, fall back to local constant
  useEffect(() => {
    fetch(`${API_BASE}/api/reference/languages`)
      .then(r => r.json())
      .then((langs: Array<{ code: string; name: string; native: string; tts: string }>) => {
        const mapped = langs.map(l => ({
          code: l.code, label: l.name, native: l.native, sttLang: l.tts,
        }));
        if (mapped.length > 0) setFirLanguages(mapped);
      })
      .catch(() => {}); // keep defaults on error
  }, []);

  // Keep answersRef up-to-date so step-change effect sees fresh answers
  useEffect(() => { answersRef.current = answers; }, [answers]);

  // Reset input mode each time step changes
  useEffect(() => {
    if (step === 0) return;
    const qId = QUESTIONS[step - 1]?.id;
    const existing = answersRef.current[qId ?? ''];
    if (existing?.trim()) {
      setReviewText(existing);
      setInputMode('review');
    } else {
      // Respect the user's global preferred input mode instead of always
      // defaulting to 'voice'. If they switched to text on step 1, steps 2+
      // should also open in text mode — not force them back to voice every time.
      setInputMode(preferredInputMode);
      setReviewText('');
      setLiveTranscript('');
    }
  }, [step, preferredInputMode]);

  // Pulsing animation while recording
  useEffect(() => {
    if (isRecording) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.38, duration: 650, useNativeDriver: false }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 650, useNativeDriver: false }),
        ])
      ).start();
    } else {
      pulseAnim.stopAnimation();
      Animated.timing(pulseAnim, { toValue: 1, duration: 200, useNativeDriver: false }).start();
    }
  }, [isRecording, pulseAnim]);

  // Auto-save to local storage on every change
  useEffect(() => {
    AsyncStorage.setItem('fir_draft_state', JSON.stringify({
      userId: user?.id, answers, draftId, lang, step,
    })).catch(() => {});
  }, [answers, draftId, lang, step, user?.id]);

  const syncToBackend = useCallback(async (updatedAnswers: Record<string, string>, status = 'in_progress') => {
    // Anonymous-first: sync as long as we have SOME id (real user or local
    // anon id) — a missing auth token must never block this.
    if (!effectiveUserId) return;
    setSyncing(true);
    try {
      const r = await fetch(`${API_BASE}/api/fir/draft`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ draft_id: draftId, user_id: effectiveUserId, language: lang, answers: updatedAnswers, status }),
      }).catch(() => null);
      if (r?.ok) {
        const d = await r.json();
        if (d.draft_id && !draftId) setDraftId(d.draft_id);
      }
    } catch {} finally { setSyncing(false); }
  }, [token, effectiveUserId, draftId, lang]);

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
      // expo-audio 1.x: stop() returns void; the URI is on recorder.uri after stopping
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) {
        // Recording produced no file — user may have tapped too quickly or mic was blocked
        setTranscribing(false);
        setInputMode('voice');
        return;
      }

      // Language hint: ISO 639-1 code (e.g. "hi") for Whisper accuracy on Indian languages
      const langHint = lang?.split('-')[0] ?? 'hi';
      // Correct arg order: (apiBase, token, uri, languageHint)
      const result = await whisperTranscribeFile(API_BASE, token ?? '', uri, langHint);
      const text = (result as any)?.text ?? (typeof result === 'string' ? result : '');
      if (text?.trim()) {
        const cleaned = text.trim();
        setAnswers(prev => ({ ...prev, [qId]: cleaned }));
        setReviewText(cleaned);
        setInputMode('review');
      } else {
        // Empty transcript (silence / too short) — let user try again
        setInputMode('voice');
      }
    } catch (err: any) {
      const msg = err?.message || '';
      if (msg.includes('daily voice limit') || msg.includes('429')) {
        Alert.alert('Daily limit reached', msg);
      } else if (msg.includes('session_expired')) {
        Alert.alert('Session expired', 'Please sign in again.');
      } else {
        Alert.alert('Transcription Error', 'Could not transcribe. Please tap the mic and try again, or type your answer.');
      }
      setInputMode('text');
    } finally {
      setTranscribing(false);
      setAudioModeAsync({ allowsRecording: false, playsInSilentMode: false }).catch(() => {});
    }
  };

  // ── Web Speech API recording (browser only) ───────────────────────────
  const startWebRecording = (qId: string) => {
    if (typeof window === 'undefined') return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      Alert.alert(
        'Voice not supported',
        'Your browser does not support voice input. Please use Chrome or Safari, or type your answer.'
      );
      setInputMode('text');
      return;
    }
    const rec = new SR();
    rec.lang = firLanguages.find(l => l.code === lang)?.sttLang ?? 'en-IN';
    // Fix 1: continuous mode so natural pauses do NOT end the session
    rec.continuous      = true;
    rec.interimResults  = true;
    webRecognitionRef.current = rec;
    setLiveTranscript('');
    setStillListening(false);
    setIsRecording(true);

    const clearSilence = () => {
      if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    };

    rec.onresult = (e: any) => {
      // Reset the silence timer on every new speech chunk
      clearSilence();
      setStillListening(false);
      const interim = Array.from(e.results as any[])
        .map((r: any) => r[0].transcript)
        .join('');
      setLiveTranscript(interim);
      // Show "Still listening…" after 1 s of silence, then auto-stop after 2.5 s total
      silenceTimerRef.current = setTimeout(() => {
        setStillListening(true);
        silenceTimerRef.current = setTimeout(() => {
          setStillListening(false);
          webRecognitionRef.current?.stop();
        }, 1500);
      }, 1000);
    };

    rec.onend = () => {
      clearSilence();
      setStillListening(false);
      setIsRecording(false);
      webRecognitionRef.current = null;
      // Use functional state to grab the latest liveTranscript value
      setLiveTranscript(prev => {
        const final = prev.trim();
        if (final) {
          setAnswers(ans => ({ ...ans, [qId]: final }));
          setReviewText(final);
          setInputMode('review');
        } else {
          setInputMode('voice');
        }
        return '';
      });
    };

    rec.onerror = (e: any) => {
      clearSilence();
      setStillListening(false);
      setIsRecording(false);
      webRecognitionRef.current = null;
      setLiveTranscript('');
      if (e.error !== 'no-speech') {
        Alert.alert('Voice Error', 'Could not capture voice. Please try again or type your answer.');
      }
      setInputMode('voice');
    };

    rec.start();
  };

  const stopWebRecording = () => {
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    setStillListening(false);
    webRecognitionRef.current?.stop();
  };

  // Unified mic press handler — routes to the right engine
  const handleMicPress = (qId: string) => {
    if (Platform.OS === 'web') {
      startWebRecording(qId);
    } else {
      startRecording();
    }
  };

  const handleStopPress = (qId: string) => {
    if (Platform.OS === 'web') {
      stopWebRecording();
    } else {
      stopAndTranscribe(qId);
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

  // ── Fix 2: follow-up helpers ──────────────────────────────────────────
  const FOLLOW_UP_QIDS = ['what_happened', 'accused', 'injury_loss'];

  const advanceFromCurrentStep = async (latestAnswers: Record<string, string>) => {
    const q = QUESTIONS[step - 1];
    if (!q) return;
    if (q.id === 'what_happened' && !safetyAcknowledged) {
      await checkSafety(latestAnswers['what_happened'] ?? '');
    }
    syncToBackend(latestAnswers).catch(() => {});
    if (step >= QUESTIONS.length) {
      await syncToBackend(latestAnswers, 'completed');
      router.push({
        pathname: '/fir-draft/result',
        params: { draftId: draftId ?? '', lang, userId: effectiveUserId ?? '' },
      } as any);
    } else {
      setStep(s => s + 1);
    }
  };

  const handleFollowUpContinue = async () => {
    const latestAnswers = { ...answersRef.current };
    if (followUpState?.answer?.trim()) {
      const parentQId = followUpState.parentQId;
      latestAnswers[parentQId] =
        (latestAnswers[parentQId] || '') + '\n\nAdditional details: ' + followUpState.answer.trim();
      setAnswers(latestAnswers);
      answersRef.current = latestAnswers;
    }
    setFollowUpState(null);
    await advanceFromCurrentStep(latestAnswers);
  };

  const handleFollowUpSkip = async () => {
    setFollowUpState(null);
    await advanceFromCurrentStep(answersRef.current);
  };

  const nextStep = async () => {
    if (step === 0) { setStep(1); return; }
    const q = QUESTIONS[step - 1];
    const latestAnswers = answersRef.current;

    if (q.required && !latestAnswers[q.id]?.trim()) {
      Alert.alert('Required', `Please answer: "${q.label}"`);
      return;
    }

    // Fix 2: Check for LLM follow-up on key narrative questions (once per question)
    if (
      FOLLOW_UP_QIDS.includes(q.id) &&
      !followUpCheckedRef.current.has(q.id) &&
      latestAnswers[q.id]?.trim()
    ) {
      followUpCheckedRef.current.add(q.id);
      setFollowUpLoading(true);
      try {
        const langObj = firLanguages.find(l => l.code === lang);
        const r = await fetch(`${API_BASE}/api/fir/followup`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            answer:        latestAnswers[q.id],
            question_id:   q.id,
            language:      lang,
            language_name: langObj?.label || 'English',
          }),
        }).catch(() => null);
        if (r?.ok) {
          const data = await r.json();
          if (data.follow_up) {
            setFollowUpLoading(false);
            setFollowUpState({ question: data.follow_up, parentQId: q.id, answer: '' });
            return; // Wait for user to answer follow-up
          }
        }
      } catch {}
      setFollowUpLoading(false);
    }

    await advanceFromCurrentStep(latestAnswers);
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
            <Text style={s.headerTitle}>{t('fir.title', lang)}</Text>
            <Text style={s.headerSub}>{t('fir.subtitle', lang)}</Text>
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
                <Text style={s.introTitle}>{t('fir.title', lang)}</Text>
                <Text style={s.introBody}>
                  Describe your incident by voice. DHARA will generate a ready-to-present FIR draft with the correct BNS sections and suggest your nearest police station.
                </Text>
                <View style={s.disclaimer}>
                  <Ionicons name="information-circle-outline" size={16} color="#6B7280" />
                  <Text style={s.disclaimerText}>
                    This is a citizen draft — NOT a registered FIR. Accuracy of suggested sections depends on your description.
                  </Text>
                </View>
              </View>
              <Text style={s.sectionLabel}>{t('fir.selectLang', lang)}</Text>
              {firLanguages.map(l => (
                <Pressable key={l.code} style={[s.langCard, lang === l.code && s.langCardActive]} onPress={() => setLang(l.code)}>
                  <Text style={[s.langCardLabel, lang === l.code && { color: NAVY }]}>{l.native}</Text>
                  <Text style={s.langCardSub}>{l.label}</Text>
                  {lang === l.code && <Ionicons name="checkmark-circle" size={22} color={NAVY} />}
                </Pressable>
              ))}
              <Pressable style={s.nextBtn} onPress={nextStep}>
                <Text style={s.nextBtnText}>{t('fir.startBtn', lang)}</Text>
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

              {/* ─── Voice-first input section ─────────────────────────── */}
              <View style={s.inputSection}>

                {/* ── IDLE: large mic button (native + web) ── */}
                {inputMode === 'voice' && !isRecording && !transcribing && (
                  <View style={s.voiceIdle}>
                    <Animated.View style={[s.micRing, { transform: [{ scale: pulseAnim }] }]}>
                      <Pressable style={s.micBig} onPress={() => handleMicPress(currentQ.id)}>
                        <Ionicons name="mic" size={44} color="#fff" />
                      </Pressable>
                    </Animated.View>
                    <Text style={s.micIdleLabel}>{t('fir.tapMic', lang)}</Text>
                    {Platform.OS === 'web' && (
                      <Text style={s.micWebHint}>Works in Chrome & Safari</Text>
                    )}
                    <Pressable onPress={() => { setPreferredInputMode('text'); setInputMode('text'); }} style={s.switchModeBtn}>
                      <Ionicons name="create-outline" size={14} color="#6B7280" />
                      <Text style={s.switchModeText}>{t('fir.typeInstead', lang)}</Text>
                    </Pressable>
                  </View>
                )}

                {/* ── RECORDING: native pulsing stop button ── */}
                {Platform.OS !== 'web' && isRecording && (
                  <View style={s.voiceIdle}>
                    <Animated.View style={[s.micRing, s.micRingRecording, { transform: [{ scale: pulseAnim }] }]}>
                      <Pressable style={[s.micBig, s.micBigRecording]} onPress={() => handleStopPress(currentQ.id)}>
                        <Ionicons name="stop" size={40} color="#fff" />
                      </Pressable>
                    </Animated.View>
                    <Text style={s.recordingLabel}>● Recording…  Tap to stop</Text>
                  </View>
                )}

                {/* ── RECORDING: web — pulsing + live transcript + still-listening indicator ── */}
                {Platform.OS === 'web' && isRecording && (
                  <View style={s.voiceIdle}>
                    <Animated.View style={[s.micRing, s.micRingRecording, { transform: [{ scale: pulseAnim }] }]}>
                      <Pressable style={[s.micBig, s.micBigRecording]} onPress={() => handleStopPress(currentQ.id)}>
                        <Ionicons name="stop" size={40} color="#fff" />
                      </Pressable>
                    </Animated.View>
                    {stillListening ? (
                      <Text style={s.stillListeningLabel}>⏸ Still listening…</Text>
                    ) : (
                      <Text style={s.recordingLabel}>● Listening…  Tap to stop</Text>
                    )}
                    {liveTranscript ? (
                      <View style={s.liveBox}>
                        <Text style={s.liveText}>{liveTranscript}</Text>
                      </View>
                    ) : (
                      <Text style={s.liveHint}>Speak now — text will appear here</Text>
                    )}
                  </View>
                )}

                {/* ── TRANSCRIBING: native Whisper spinner ── */}
                {Platform.OS !== 'web' && transcribing && (
                  <View style={s.voiceIdle}>
                    <View style={[s.micBig, { backgroundColor: '#6B7280' }]}>
                      <ActivityIndicator color="#fff" size="large" />
                    </View>
                    <Text style={s.micIdleLabel}>Transcribing your voice…</Text>
                  </View>
                )}

                {/* ── REVIEW: "We heard…" card ── */}
                {inputMode === 'review' && !isRecording && !transcribing && (
                  <View style={s.reviewCard}>
                    <View style={s.reviewHeader}>
                      <Ionicons name="checkmark-circle" size={20} color={GREEN} />
                      <Text style={s.reviewHeaderText}>{t('fir.weHeard', lang)}</Text>
                    </View>
                    <Text style={s.reviewBodyText}>{reviewText}</Text>
                    <View style={s.reviewActions}>
                      <Pressable
                        style={s.rerecordBtn}
                        onPress={() => {
                          const qId = currentQ.id;
                          setAnswers(prev => { const n = { ...prev }; delete n[qId]; return n; });
                          setReviewText('');
                          setLiveTranscript('');
                          setInputMode('voice');
                        }}
                      >
                        <Ionicons name="mic-outline" size={15} color={RED} />
                        <Text style={s.rerecordText}>{t('fir.reRecord', lang)}</Text>
                      </Pressable>
                      <Pressable
                        style={s.editAnswerBtn}
                        onPress={() => setInputMode('text')}
                      >
                        <Ionicons name="create-outline" size={15} color={NAVY} />
                        <Text style={s.editAnswerText}>{t('fir.editText', lang)}</Text>
                      </Pressable>
                    </View>
                  </View>
                )}

                {/* ── TEXT (fallback / edit mode) ── */}
                {inputMode === 'text' && !isRecording && !transcribing && (
                  <View style={{ gap: 8 }}>
                    <TextInput
                      style={[s.input, currentQ.type === 'textarea' && s.textarea]}
                      value={answers[currentQ.id] ?? ''}
                      onChangeText={t => setAnswers(prev => {
                        const next = { ...prev, [currentQ.id]: t };
                        answersRef.current = next;
                        return next;
                      })}
                      placeholder={currentQ.hint}
                      placeholderTextColor="#9CA3AF"
                      multiline={currentQ.type === 'textarea'}
                      numberOfLines={currentQ.type === 'textarea' ? 5 : 1}
                      textAlignVertical={currentQ.type === 'textarea' ? 'top' : 'center'}
                      autoFocus
                    />
                    <Pressable onPress={() => { setPreferredInputMode('voice'); setLiveTranscript(''); setInputMode('voice'); }} style={s.switchModeBtn}>
                      <Ionicons name="mic-outline" size={14} color="#6B7280" />
                      <Text style={s.switchModeText}>{t('fir.useMic', lang)}</Text>
                    </Pressable>
                  </View>
                )}

              </View>

              {/* ── Fix 2: Follow-up clarification card ── */}
              {followUpLoading && (
                <View style={s.followUpLoading}>
                  <ActivityIndicator size="small" color={NAVY} />
                  <Text style={s.followUpLoadingText}>Just a moment…</Text>
                </View>
              )}

              {followUpState && (
                <View style={s.followUpCard}>
                  <View style={s.followUpHeader}>
                    <Ionicons name="chatbubble-ellipses-outline" size={18} color={NAVY} />
                    <Text style={s.followUpTitle}>One more thing:</Text>
                  </View>
                  <Text style={s.followUpQuestion}>{followUpState.question}</Text>
                  <TextInput
                    style={[s.input, s.textarea, { marginTop: 8 }]}
                    value={followUpState.answer}
                    onChangeText={t => setFollowUpState(prev => prev ? { ...prev, answer: t } : null)}
                    placeholder="Your answer (optional — tap Skip to continue)"
                    placeholderTextColor="#9CA3AF"
                    multiline
                    numberOfLines={3}
                    autoFocus
                  />
                  <View style={s.followUpActions}>
                    <Pressable style={s.followUpSkipBtn} onPress={handleFollowUpSkip}>
                      <Text style={s.followUpSkipText}>Skip</Text>
                    </Pressable>
                    <Pressable style={s.followUpContinueBtn} onPress={handleFollowUpContinue}>
                      <Ionicons name="arrow-forward" size={16} color="#fff" />
                      <Text style={s.followUpContinueText}>
                        {followUpState.answer.trim() ? 'Add & Continue' : 'Continue'}
                      </Text>
                    </Pressable>
                  </View>
                </View>
              )}

              {/* ── Next button (hidden while follow-up card is shown) ── */}
              {!followUpState && (
                <Pressable
                  style={[s.nextBtn, followUpLoading && { opacity: 0.6 }]}
                  onPress={nextStep}
                  disabled={followUpLoading}
                >
                  {followUpLoading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <>
                      <Text style={s.nextBtnText}>
                        {step >= QUESTIONS.length
                          ? t('fir.generateBtn', lang)
                          : inputMode === 'review'
                            ? t('fir.nextBtn', lang)
                            : t('fir.nextBtn', lang)}
                      </Text>
                      <Ionicons name={step >= QUESTIONS.length ? 'document-text' : 'arrow-forward'} size={20} color="#fff" />
                    </>
                  )}
                </Pressable>
              )}
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

  // ── Voice-first input styles ──────────────────────────────────────────
  inputSection: { gap: 0 },
  voiceIdle: { alignItems: 'center', paddingVertical: 28, gap: 14 },
  // Outer ring that animates (scale)
  micRing: {
    width: 104, height: 104, borderRadius: 52,
    backgroundColor: 'rgba(20,54,90,0.12)',
    alignItems: 'center', justifyContent: 'center',
  },
  micRingRecording: { backgroundColor: 'rgba(220,38,38,0.15)' },
  // Inner filled button
  micBig: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: NAVY,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: NAVY, shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3, shadowRadius: 8, elevation: 6,
  },
  micBigRecording: { backgroundColor: RED, shadowColor: RED },
  micIdleLabel: { fontSize: 16, fontWeight: '600', color: '#374151' },
  recordingLabel: { fontSize: 16, fontWeight: '700', color: RED },
  stillListeningLabel: {
    fontSize: 13, color: '#D97706', fontWeight: '600',
    backgroundColor: '#FEF3C7', paddingHorizontal: 12, paddingVertical: 4,
    borderRadius: 8, marginTop: 4,
  },
  // Follow-up card styles (Fix 2)
  followUpLoading: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, paddingVertical: 12,
  },
  followUpLoadingText: { fontSize: 13, color: '#6B7280' },
  followUpCard: {
    backgroundColor: '#EEF2FF', borderRadius: 14, padding: 16, gap: 8,
    borderWidth: 1.5, borderColor: '#A5B4FC',
  },
  followUpHeader: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  followUpTitle: { fontSize: 13, fontWeight: '700', color: NAVY },
  followUpQuestion: { fontSize: 16, color: '#1F2937', lineHeight: 24, fontWeight: '600' },
  followUpActions: { flexDirection: 'row', gap: 10, marginTop: 4 },
  followUpSkipBtn: {
    paddingHorizontal: 18, paddingVertical: 11, borderRadius: 10,
    borderWidth: 1.5, borderColor: '#D1D5DB', backgroundColor: '#fff',
  },
  followUpSkipText: { fontSize: 13, color: '#6B7280', fontWeight: '600' },
  followUpContinueBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 11, borderRadius: 10, backgroundColor: NAVY,
  },
  followUpContinueText: { fontSize: 13, fontWeight: '700', color: '#fff' },
  switchModeBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    paddingHorizontal: 14, paddingVertical: 8,
    borderRadius: 20, backgroundColor: '#F3F4F6',
  },
  switchModeText: { fontSize: 13, color: '#6B7280' },
  micWebHint: { fontSize: 12, color: '#9CA3AF', fontStyle: 'italic' },
  // Live transcript box shown while Web Speech API is recording
  liveBox: {
    maxWidth: 280, backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 10,
    marginTop: 4,
  },
  liveText: { fontSize: 14, color: '#1F2937', textAlign: 'center', fontStyle: 'italic', lineHeight: 22 },
  liveHint: { fontSize: 12, color: '#9CA3AF', fontStyle: 'italic' },
  // Review card
  reviewCard: {
    backgroundColor: '#F0FDF4', borderRadius: 14,
    padding: 16, gap: 10,
    borderWidth: 1.5, borderColor: '#86EFAC',
    marginVertical: 8,
  },
  reviewHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  reviewHeaderText: { fontSize: 14, fontWeight: '800', color: GREEN },
  reviewBodyText: { fontSize: 15, color: '#1F2937', lineHeight: 24, fontStyle: 'italic' },
  reviewActions: { flexDirection: 'row', gap: 10, marginTop: 4 },
  rerecordBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 10, borderRadius: 10,
    borderWidth: 1.5, borderColor: RED, backgroundColor: '#FEF2F2',
  },
  rerecordText: { fontSize: 13, fontWeight: '700', color: RED },
  editAnswerBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 10, borderRadius: 10,
    borderWidth: 1.5, borderColor: NAVY, backgroundColor: '#EEF2FF',
  },
  editAnswerText: { fontSize: 13, fontWeight: '700', color: NAVY },
});