/**
 * Missing Person — Interview Screen (18 questions: MP1-MP14, RP1-RP4)
 *
 * DATA POLICY (enforced):
 *  - All answers stored ONLY in AsyncStorage with 'missing_draft_' key prefix
 *  - No answers sent to any server endpoint
 *  - Server receives ONLY the analytics event name, no payload
 *
 * Route: /missing/interview
 */
import { useState, useCallback } from 'react';
import {
  View, Text, Pressable, TextInput, ScrollView, StyleSheet,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from '@/src/auth';
import interviewData from '@/src/content/missing_interview.json';

type Lang = 'en' | 'hi' | 'mr';

const NAVY = '#1B2B5B';
const GOLD = '#C9973A';
const RED  = '#CC0000';
const BG   = '#FAFAF8';

const STORAGE_KEY = 'missing_draft_answers_v1';

function t(obj: Record<string, string> | undefined, lang: Lang): string {
  if (!obj) return '';
  return obj[lang] || obj['en'] || '';
}

// ── Analytics stub — fires event name only, no payload ────────────────────────
async function trackMissingCompleted() {
  try {
    const prefs = await AsyncStorage.getItem('gk_consent_prefs');
    const parsed = prefs ? JSON.parse(prefs) : {};
    if (!parsed.analytics) return;
    console.log('[analytics] missing_completed');  // wire PostHog here
  } catch { /* silent */ }
}

type Question = {
  id: string;
  order: number;
  type: string;
  field: string;
  label: Record<string, string>;
  placeholder?: Record<string, string>;
  text?: Record<string, string>;
  options?: Array<{ id: string; text: Record<string, string> }>;
  is_minor_check?: boolean;
  if_yes_show?: Record<string, string>;
};

export default function MissingInterviewScreen() {
  const { language: rawLang, token } = useAuth();
  const lang: Lang = (['en', 'hi', 'mr'].includes(rawLang) ? rawLang : 'en') as Lang;
  const router = useRouter();

  const questions = interviewData.questions as unknown as Question[];

  const [qIdx,       setQIdx]       = useState(0);
  const [answers,    setAnswers]     = useState<Record<string, string>>({});
  const [inputVal,   setInputVal]    = useState('');
  const [saving,     setSaving]      = useState(false);
  const [minorAlert, setMinorAlert]  = useState(false);

  const currentQ  = questions[qIdx] ?? null;
  const progress  = questions.length > 0 ? ((qIdx) / questions.length) * 100 : 0;

  // ── Save answer to AsyncStorage (device only) — must be before any return ─
  const saveToDevice = useCallback(async (updatedAnswers: Record<string, string>) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(updatedAnswers));
    } catch { /* silent — device storage failure */ }
  }, []);

  // ── Submit an answer ──────────────────────────────────────────────────────
  const submitAnswer = useCallback(async (field: string, value: string) => {
    if (!value.trim()) return;
    const updated = { ...answers, [field]: value.trim() };
    setAnswers(updated);
    setInputVal('');

    // Save to device only — never to server
    await saveToDevice(updated);

    // Minor alert check (after MP9)
    if (field === 'is_minor' && value === 'YES') {
      setMinorAlert(true);
    }

    if (qIdx + 1 >= questions.length) {
      // All questions answered — navigate to result
      setSaving(true);
      await trackMissingCompleted();
      setSaving(false);
      router.push('/missing/result');
    } else {
      setQIdx(i => i + 1);
    }
  }, [answers, qIdx, questions.length, saveToDevice, router]);

  // Registration gate — show prompt if not logged in (after all hooks)
  if (!token) {
    return (
      <SafeAreaView style={st.safe} edges={['top']}>
        <Pressable onPress={() => router.back()} style={st.back}>
          <Text style={st.backText}>←</Text>
        </Pressable>
        <View style={st.gateCard}>
          <Text style={st.gateTitle}>
            {lang === 'hi' ? 'खाता आवश्यक है' : lang === 'mr' ? 'खाते आवश्यक आहे' : 'Account Required'}
          </Text>
          <Text style={st.gateBody}>
            {lang === 'hi'
              ? 'कृपया शिकायत तैयार करने के लिए साइन इन करें।'
              : lang === 'mr'
              ? 'कृपया तक्रार तयार करण्यासाठी साइन इन करा.'
              : 'Please sign in to prepare the complaint.'}
          </Text>
          <Pressable style={st.primaryBtn} onPress={() => router.replace('/login')}>
            <Text style={st.primaryBtnText}>
              {lang === 'hi' ? 'साइन इन करें' : lang === 'mr' ? 'साइन इन करा' : 'Sign In'}
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  if (saving) {
    return (
      <SafeAreaView style={st.safe} edges={['top']}>
        <View style={st.centred}>
          <ActivityIndicator size="large" color={NAVY} />
          <Text style={st.savingText}>
            {lang === 'hi' ? 'सहेजा जा रहा है...' : lang === 'mr' ? 'जतन होत आहे...' : 'Saving…'}
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!currentQ) return null;

  // Section heading
  const section = currentQ.id.startsWith('RP')
    ? (lang === 'hi' ? 'आपकी जानकारी' : lang === 'mr' ? 'तुमची माहिती' : 'About You (Complainant)')
    : (lang === 'hi' ? 'लापता व्यक्ति की जानकारी' : lang === 'mr' ? 'बेपत्ता व्यक्तीची माहिती' : 'About the Missing Person');

  return (
    <SafeAreaView style={st.safe} edges={['top']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={80}
      >
        <ScrollView contentContainerStyle={st.scroll} keyboardShouldPersistTaps="handled">
          {/* Header */}
          <Pressable onPress={() => router.back()} style={st.back}>
            <Text style={st.backText}>←</Text>
          </Pressable>

          {/* Progress */}
          <View style={st.progressRow}>
            <View style={st.progressBar}>
              <View style={[st.progressFill, { width: `${progress}%` as any }]} />
            </View>
            <Text style={st.progressText}>{qIdx + 1}/{questions.length}</Text>
          </View>

          {/* Section label */}
          <Text style={st.sectionLabel}>{section}</Text>

          {/* Minor alert banner */}
          {minorAlert && (
            <View style={st.minorBanner}>
              <Text style={st.minorBannerText}>
                {t((interviewData.questions.find(q => q.id === 'MP9') as any)?.if_yes_show, lang)}
              </Text>
              <Pressable onPress={() => setMinorAlert(false)} style={st.dismissBtn}>
                <Text style={st.dismissText}>✕</Text>
              </Pressable>
            </View>
          )}

          {/* Question bubble */}
          <View style={st.qBubble}>
            <Text style={st.qText}>{t(currentQ.label, lang)}</Text>
          </View>

          {/* Declaration */}
          {currentQ.type === 'declaration' && currentQ.text && (
            <>
              <Text style={st.declarationText}>{t(currentQ.text, lang)}</Text>
              <Pressable style={st.primaryBtn} onPress={() => submitAnswer(currentQ.field, 'confirmed')}>
                <Text style={st.primaryBtnText}>
                  {lang === 'hi' ? '✓ मैं सहमत हूँ' : lang === 'mr' ? '✓ मी सहमत आहे' : '✓ I Agree & Confirm'}
                </Text>
              </Pressable>
            </>
          )}

          {/* Single choice */}
          {currentQ.type === 'single_choice' && currentQ.options && (
            <View style={{ marginTop: 12 }}>
              {currentQ.options.map(opt => (
                <Pressable
                  key={opt.id}
                  style={st.optionBtn}
                  onPress={() => submitAnswer(currentQ.field, opt.id)}
                >
                  <Text style={st.optionText}>{t(opt.text, lang)}</Text>
                </Pressable>
              ))}
            </View>
          )}

          {/* Text input */}
          {currentQ.type === 'text' && (
            <View style={st.inputRow}>
              <TextInput
                style={st.textInput}
                placeholder={t(currentQ.placeholder, lang) || '…'}
                placeholderTextColor="#AAA"
                value={inputVal}
                onChangeText={setInputVal}
                multiline={currentQ.field === 'physical_description' || currentQ.field === 'reporter_address'}
                numberOfLines={currentQ.field === 'physical_description' ? 3 : 1}
                returnKeyType="next"
                onSubmitEditing={() => submitAnswer(currentQ.field, inputVal)}
              />
              <Pressable
                style={[st.nextBtn, !inputVal.trim() && st.nextBtnDisabled]}
                onPress={() => submitAnswer(currentQ.field, inputVal)}
                disabled={!inputVal.trim()}
              >
                <Text style={st.nextBtnText}>→</Text>
              </Pressable>
            </View>
          )}

          {/* Data protection notice */}
          <View style={st.privacyNote}>
            <Text style={st.privacyText}>
              🔒{' '}
              {lang === 'hi'
                ? 'यह जानकारी केवल इस डिवाइस पर सहेजी जाती है।'
                : lang === 'mr'
                ? 'ही माहिती फक्त या डिव्हाइसवर जतन केली जाते.'
                : 'This answer is saved on this device only.'}
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  safe:           { flex: 1, backgroundColor: BG },
  scroll:         { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 60 },
  centred:        { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },

  back:           { marginBottom: 8 },
  backText:       { color: NAVY, fontSize: 14, fontWeight: '600' },

  progressRow:    { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  progressBar:    { flex: 1, height: 4, backgroundColor: '#E5E7EB', borderRadius: 2, marginRight: 10 },
  progressFill:   { height: 4, backgroundColor: GOLD, borderRadius: 2 },
  progressText:   { fontSize: 12, color: '#999', minWidth: 38, textAlign: 'right' },

  sectionLabel:   { fontSize: 11, fontWeight: '700', color: '#999', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 },

  minorBanner:    {
    backgroundColor: '#FFF0F0', borderRadius: 10, padding: 14, marginBottom: 16,
    borderLeftWidth: 4, borderLeftColor: RED, flexDirection: 'row', alignItems: 'flex-start',
  },
  minorBannerText: { flex: 1, fontSize: 13, color: RED, lineHeight: 19, fontWeight: '600' },
  dismissBtn:     { marginLeft: 8, padding: 4 },
  dismissText:    { color: RED, fontSize: 16 },

  qBubble:        { backgroundColor: NAVY, borderRadius: 16, padding: 18, marginBottom: 16 },
  qText:          { fontSize: 17, fontWeight: '600', color: '#FFF', lineHeight: 26 },

  declarationText: {
    fontSize: 13, color: '#555', lineHeight: 20, marginBottom: 16,
    backgroundColor: '#FFF', borderRadius: 10, padding: 14,
    borderWidth: 1, borderColor: '#E5E7EB',
  },

  optionBtn:      {
    backgroundColor: '#FFF', borderRadius: 12, paddingVertical: 16, paddingHorizontal: 18,
    marginBottom: 10, borderWidth: 1.5, borderColor: '#E5E7EB',
  },
  optionText:     { fontSize: 15, color: '#222', lineHeight: 22 },

  inputRow:       { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 8 },
  textInput:      {
    flex: 1, backgroundColor: '#FFF', borderWidth: 1.5, borderColor: '#DDD',
    borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14, fontSize: 15, color: '#111',
  },
  nextBtn:        {
    backgroundColor: NAVY, borderRadius: 12, width: 52, height: 52,
    alignItems: 'center', justifyContent: 'center',
  },
  nextBtnDisabled: { backgroundColor: '#CCC' },
  nextBtnText:    { color: '#FFF', fontSize: 20, fontWeight: '700' },

  primaryBtn:     {
    backgroundColor: NAVY, borderRadius: 12, paddingVertical: 16,
    alignItems: 'center', marginBottom: 12,
  },
  primaryBtnText: { color: '#FFF', fontWeight: '700', fontSize: 16 },

  privacyNote:    {
    marginTop: 12, paddingHorizontal: 4, paddingVertical: 6,
    flexDirection: 'row', alignItems: 'center',
  },
  privacyText:    { fontSize: 11, color: '#AAA', lineHeight: 16 },

  savingText:     { color: NAVY, fontSize: 16, fontWeight: '600' },

  gateCard:       { margin: 20, backgroundColor: '#FFF', borderRadius: 16, padding: 24 },
  gateTitle:      { fontSize: 20, fontWeight: '700', color: NAVY, marginBottom: 12 },
  gateBody:       { fontSize: 15, color: '#555', lineHeight: 22, marginBottom: 24 },
});
