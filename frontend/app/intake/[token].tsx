import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, StyleSheet,
  ActivityIndicator, Platform, KeyboardAvoidingView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';
import { INTAKE_TEMPLATES, getTemplate, IntakeTemplate } from '@/src/intakeTemplates';

const NAVY = theme.colors.primary;
const GOLD = theme.colors.gold;

// Simple native STT helper — no auth needed (on-device)
async function startNativeSTT(
  onPartial: (t: string) => void,
  onFinal: (t: string) => void,
  onError: (e: string) => void,
): Promise<() => void> {
  if (Platform.OS === 'web') { onError('Voice input not available on web'); return () => {}; }
  try {
    const mod = await import('expo-speech-recognition');
    const { ExpoSpeechRecognitionModule, addSpeechRecognitionListener } = mod;
    const perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync?.();
    if (perm && !perm.granted) { onError('Microphone permission denied'); return () => {}; }
    let last = '';
    const subs: any[] = [];
    subs.push(addSpeechRecognitionListener('result', (ev: any) => {
      const t = ev?.results?.[0]?.transcript ?? '';
      if (ev?.isFinal) { onFinal(t); } else { last = t; onPartial(t); }
    }));
    subs.push(addSpeechRecognitionListener('end', () => { if (last) onFinal(last); subs.forEach(s => s?.remove?.()); }));
    subs.push(addSpeechRecognitionListener('error', (ev: any) => { onError(ev?.error || 'Voice error'); subs.forEach(s => s?.remove?.()); }));
    ExpoSpeechRecognitionModule.start({ lang: 'en-IN', interimResults: true, continuous: false, requiresOnDeviceRecognition: false });
    return () => { try { ExpoSpeechRecognitionModule.stop?.(); } catch {} subs.forEach(s => s?.remove?.()); };
  } catch (e: any) { onError(e?.message || 'Voice unavailable'); return () => {}; }
}

export default function ClientIntake() {
  const { token } = useLocalSearchParams<{ token: string }>();
  const [intake, setIntake] = useState<any>(null);
  const [template, setTemplate] = useState<IntakeTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [clientName, setClientName] = useState('');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [activeVoice, setActiveVoice] = useState<string | null>(null); // question id being recorded
  const [partialText, setPartialText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE}/api/advocate/intake/${token}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        setIntake(data);
        if (data?.template_id) {
          setTemplate(getTemplate(data.template_id) ?? INTAKE_TEMPLATES[0]);
        } else {
          setTemplate(INTAKE_TEMPLATES[0]);
        }
      })
      .catch(() => setIntake(null))
      .finally(() => setLoading(false));
  }, [token]);

  const toggleVoice = async (qId: string) => {
    if (activeVoice === qId) {
      // stop
      stopRef.current?.();
      stopRef.current = null;
      setActiveVoice(null);
      setPartialText('');
      return;
    }
    // stop any active
    stopRef.current?.();
    setActiveVoice(qId);
    setPartialText('');
    const stop = await startNativeSTT(
      (t) => setPartialText(t),
      (t) => {
        setAnswers(prev => ({ ...prev, [qId]: (prev[qId] ? prev[qId] + ' ' : '') + t }));
        setActiveVoice(null);
        setPartialText('');
        stopRef.current = null;
      },
      (err) => {
        setActiveVoice(null);
        setPartialText('');
        stopRef.current = null;
      },
    );
    stopRef.current = stop;
  };

  const handleSubmit = async () => {
    if (!clientName.trim()) { alert('Please enter your name.'); return; }
    const required = template?.questions.filter(q => q.required) ?? [];
    const missing = required.find(q => !answers[q.id]?.trim());
    if (missing) { alert(`Please answer: "${missing.label}"`); return; }
    setSubmitting(true);
    try {
      const r = await fetch(`${API_BASE}/api/advocate/intake/${token}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: clientName.trim(), transcript: Object.values(answers), answers }),
      });
      if (!r.ok) throw new Error();
      setDone(true);
    } catch { alert('Submission failed. Please try again.'); }
    setSubmitting(false);
  };

  if (loading) return (
    <SafeAreaView style={s.safe}><View style={s.center}><ActivityIndicator color={NAVY} size="large" /></View></SafeAreaView>
  );

  if (!intake || intake.expired) return (
    <SafeAreaView style={s.safe}>
      <View style={s.center}>
        <Ionicons name="alert-circle-outline" size={48} color="#DC2626" />
        <Text style={s.errorTitle}>{intake?.expired ? 'This link has expired' : 'Link not found'}</Text>
        <Text style={s.errorSub}>Please ask your advocate to send a new link.</Text>
      </View>
    </SafeAreaView>
  );

  if (intake.status === 'complete' || done) return (
    <SafeAreaView style={s.safe}>
      <View style={s.center}>
        <Ionicons name="checkmark-circle" size={64} color="#059669" />
        <Text style={s.doneTitle}>Submitted Successfully</Text>
        <Text style={s.doneSub}>Your information has been sent to your advocate securely. They will contact you shortly.</Text>
      </View>
    </SafeAreaView>
  );

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <SafeAreaView style={s.safe}>
        {/* Header */}
        <View style={s.header}>
          <View style={[s.headerIcon, { backgroundColor: (template?.color ?? NAVY) + '22' }]}>
            <Ionicons name={(template?.icon ?? 'document-text-outline') as any} size={20} color={template?.color ?? NAVY} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.headerTitle}>{template?.title ?? 'Client Intake'}</Text>
            <Text style={s.headerSub}>Powered by DHARA AI — Secure &amp; Confidential</Text>
          </View>
        </View>

        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          {/* Name */}
          <View style={s.fieldWrap}>
            <Text style={s.label}>Your Full Name <Text style={s.req}>*</Text></Text>
            <TextInput
              style={s.input}
              value={clientName}
              onChangeText={setClientName}
              placeholder="Enter your full name"
              placeholderTextColor="#9CA3AF"
              returnKeyType="next"
            />
          </View>

          {/* Template questions */}
          {template?.questions.map((q) => {
            const isRecording = activeVoice === q.id;
            const showMic = Platform.OS !== 'web';
            return (
              <View key={q.id} style={s.fieldWrap}>
                <Text style={s.label}>{q.label}{q.required ? <Text style={s.req}> *</Text> : null}</Text>
                <View style={s.inputRow}>
                  <TextInput
                    style={[s.input, q.type === 'textarea' && s.textarea, { flex: 1 }]}
                    value={isRecording && partialText ? answers[q.id] + (answers[q.id] ? ' ' : '') + partialText : answers[q.id] ?? ''}
                    onChangeText={t => setAnswers(prev => ({ ...prev, [q.id]: t }))}
                    placeholder={q.placeholder ?? ''}
                    placeholderTextColor="#9CA3AF"
                    multiline={q.type === 'textarea'}
                    numberOfLines={q.type === 'textarea' ? 3 : 1}
                    textAlignVertical={q.type === 'textarea' ? 'top' : 'center'}
                  />
                  {showMic && (
                    <Pressable style={[s.micBtn, isRecording && s.micBtnActive]} onPress={() => toggleVoice(q.id)}>
                      <Ionicons name={isRecording ? 'stop' : 'mic-outline'} size={20} color={isRecording ? '#fff' : NAVY} />
                    </Pressable>
                  )}
                </View>
                {isRecording && <Text style={s.recording}>🎙 Listening…</Text>}
              </View>
            );
          })}

          <Pressable style={[s.submitBtn, submitting && { opacity: 0.6 }]} onPress={handleSubmit} disabled={submitting}>
            {submitting
              ? <ActivityIndicator color="#fff" size="small" />
              : <><Ionicons name="send" size={18} color="#fff" /><Text style={s.submitText}>Submit to Advocate</Text></>
            }
          </Pressable>

          <Text style={s.privacy}>🔒 Your information is encrypted and only visible to your advocate.</Text>
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#FDFBF7' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 12 },
  header: { backgroundColor: NAVY, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14, gap: 12 },
  headerIcon: { width: 40, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 16, fontWeight: '800', color: '#fff' },
  headerSub: { fontSize: 11, color: GOLD, marginTop: 2 },
  scroll: { padding: 20, gap: 16, paddingBottom: 40 },
  fieldWrap: { gap: 6 },
  label: { fontSize: 14, fontWeight: '700', color: '#1F2937' },
  req: { color: '#DC2626' },
  inputRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  input: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, color: '#1F2937' },
  textarea: { minHeight: 80, paddingTop: 12 },
  micBtn: { width: 46, height: 46, borderRadius: 12, backgroundColor: '#F3F4F6', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#D1D5DB', marginTop: 0 },
  micBtnActive: { backgroundColor: '#DC2626', borderColor: '#DC2626' },
  recording: { fontSize: 12, color: '#DC2626', fontWeight: '600' },
  submitBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: NAVY, borderRadius: 14, paddingVertical: 16, marginTop: 8 },
  submitText: { fontSize: 16, fontWeight: '800', color: '#fff' },
  privacy: { fontSize: 12, color: '#9CA3AF', textAlign: 'center', marginTop: 4 },
  errorTitle: { fontSize: 18, fontWeight: '800', color: '#1F2937' },
  errorSub: { fontSize: 14, color: '#6B7280', textAlign: 'center' },
  doneTitle: { fontSize: 22, fontWeight: '800', color: '#059669' },
  doneSub: { fontSize: 14, color: '#374151', textAlign: 'center', lineHeight: 22 },
});
