/**
 * Public intake flow — no login required.
 * Clients fill this in after receiving a link from their advocate.
 */
import React, { useEffect, useState } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, StyleSheet,
  ActivityIndicator, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const API = process.env.EXPO_PUBLIC_API_URL ?? '';
const NAVY = '#14365A';
const GOLD = '#D3B675';

type Step = 1 | 2 | 3 | 'confirm' | 'done' | 'expired';

export default function PublicIntake() {
  const { token } = useLocalSearchParams<{ token: string }>();
  const [step, setStep]     = useState<Step>(1);
  const [loading, setLoading]   = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [name, setName]     = useState('');
  const [situation, setSituation] = useState('');
  const [outcome, setOutcome]     = useState('');

  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/advocate/intake/${token}`)
      .then(r => r.json())
      .then(data => {
        if (data.expired || data.status === 'expired') setStep('expired');
        else if (data.status === 'complete') setStep('done');
        else setStep(1);
      })
      .catch(() => setStep('expired'))
      .finally(() => setLoading(false));
  }, [token]);

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/advocate/intake/${token}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: name.trim(), transcript: [situation.trim(), outcome.trim()] }),
      });
      if (!r.ok) throw new Error('Submission failed');
      setStep('done');
    } catch { alert('Something went wrong. Please try again.'); }
    setSubmitting(false);
  };

  if (loading) return (
    <SafeAreaView style={s.safe}>
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator color={NAVY} size="large" />
      </View>
    </SafeAreaView>
  );

  if (step === 'expired') return (
    <SafeAreaView style={s.safe}>
      <View style={s.errorCard}>
        <Ionicons name="time-outline" size={48} color="#DC2626" />
        <Text style={s.errorTitle}>This link has expired</Text>
        <Text style={s.errorSub}>Contact your advocate for a new intake link.</Text>
      </View>
    </SafeAreaView>
  );

  if (step === 'done') return (
    <SafeAreaView style={s.safe}>
      <View style={s.doneCard}>
        <Ionicons name="checkmark-circle" size={56} color={NAVY} />
        <Text style={s.doneTitle}>Information Sent</Text>
        <Text style={s.doneSub}>Your information has been sent to your advocate securely. No further action needed.</Text>
      </View>
      <Text style={s.footer}>Powered by DHARA · Legal Aid Platform</Text>
    </SafeAreaView>
  );

  const totalSteps = 3;
  const stepNum    = typeof step === 'number' ? step : 3;

  return (
    <SafeAreaView style={s.safe}>
      {/* Logo header */}
      <View style={s.topBar}>
        <Text style={s.brand}>DHARA</Text>
        <Text style={s.brandSub}>Secure Client Intake</Text>
      </View>

      {/* Step indicator */}
      {step !== 'confirm' && (
        <View style={s.stepRow}>
          {[1, 2, 3].map(n => (
            <View key={n} style={[s.stepDot, stepNum >= n && s.stepDotActive]} />
          ))}
        </View>
      )}

      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
        {step === 1 && (
          <>
            <Text style={s.question}>What should we call you?</Text>
            <Text style={s.questionSub}>Step 1 of 3 · Your name</Text>
            <TextInput
              style={s.input}
              placeholder="Your full name"
              placeholderTextColor="#9CA3AF"
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />
            <Pressable style={[s.btn, !name.trim() && s.btnDisabled]} disabled={!name.trim()} onPress={() => setStep(2)}>
              <Text style={s.btnText}>Next</Text>
              <Ionicons name="arrow-forward" size={18} color="#fff" />
            </Pressable>
          </>
        )}

        {step === 2 && (
          <>
            <Text style={s.question}>Tell us what happened</Text>
            <Text style={s.questionSub}>Step 2 of 3 · In your own words</Text>
            <TextInput
              style={[s.input, s.textarea]}
              placeholder="Describe the situation. You can write in Hindi or English."
              placeholderTextColor="#9CA3AF"
              value={situation}
              onChangeText={setSituation}
              multiline
              textAlignVertical="top"
            />
            <View style={s.navRow}>
              <Pressable style={s.backBtn} onPress={() => setStep(1)}>
                <Ionicons name="arrow-back" size={18} color={NAVY} />
                <Text style={s.backBtnText}>Back</Text>
              </Pressable>
              <Pressable style={[s.btn, { flex: 1 }, !situation.trim() && s.btnDisabled]} disabled={!situation.trim()} onPress={() => setStep(3)}>
                <Text style={s.btnText}>Next</Text>
                <Ionicons name="arrow-forward" size={18} color="#fff" />
              </Pressable>
            </View>
          </>
        )}

        {step === 3 && (
          <>
            <Text style={s.question}>What do you need help with?</Text>
            <Text style={s.questionSub}>Step 3 of 3 · Your goal</Text>
            <TextInput
              style={[s.input, s.textarea]}
              placeholder="What outcome are you hoping for?"
              placeholderTextColor="#9CA3AF"
              value={outcome}
              onChangeText={setOutcome}
              multiline
              textAlignVertical="top"
            />
            <View style={s.navRow}>
              <Pressable style={s.backBtn} onPress={() => setStep(2)}>
                <Ionicons name="arrow-back" size={18} color={NAVY} />
                <Text style={s.backBtnText}>Back</Text>
              </Pressable>
              <Pressable style={[s.btn, { flex: 1 }, !outcome.trim() && s.btnDisabled]} disabled={!outcome.trim()} onPress={() => setStep('confirm')}>
                <Text style={s.btnText}>Review</Text>
                <Ionicons name="checkmark" size={18} color="#fff" />
              </Pressable>
            </View>
          </>
        )}

        {step === 'confirm' && (
          <>
            <Text style={s.confirmTitle}>Review your answers</Text>
            {([{ label: 'Your name', value: name }, { label: 'What happened', value: situation }, { label: 'What you need', value: outcome }] as const).map(row => (
              <View key={row.label} style={s.confirmRow}>
                <Text style={s.confirmLabel}>{row.label}</Text>
                <Text style={s.confirmValue}>{row.value}</Text>
              </View>
            ))}
            <Pressable style={[s.btn, submitting && { opacity: 0.6 }]} disabled={submitting} onPress={submit}>
              {submitting
                ? <ActivityIndicator color="#fff" size="small" />
                : <><Text style={s.btnText}>Submit</Text><Ionicons name="send" size={16} color="#fff" /></>}
            </Pressable>
            <Pressable style={s.editBtn} onPress={() => setStep(1)}>
              <Text style={s.editBtnText}>Edit answers</Text>
            </Pressable>
          </>
        )}
      </ScrollView>
      <Text style={s.footer}>Powered by DHARA · Legal Aid Platform</Text>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:    { flex: 1, backgroundColor: '#FDFBF7' },
  topBar:  { alignItems: 'center', paddingVertical: 16, backgroundColor: NAVY },
  brand:   { fontSize: 20, fontWeight: '900', color: GOLD, letterSpacing: 3 },
  brandSub: { fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 2 },
  stepRow: { flexDirection: 'row', gap: 8, justifyContent: 'center', paddingVertical: 14 },
  stepDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#E5E7EB' },
  stepDotActive: { backgroundColor: NAVY },
  scroll:  { padding: 24, paddingBottom: 40 },
  question: { fontSize: 22, fontWeight: '800', color: NAVY, marginBottom: 4 },
  questionSub: { fontSize: 13, color: '#9CA3AF', marginBottom: 20 },
  input:   { borderWidth: 1.5, borderColor: '#D1D5DB', borderRadius: 12, padding: 14, fontSize: 15, color: '#1F2937', backgroundColor: '#fff', marginBottom: 20 },
  textarea: { minHeight: 130, paddingTop: 12 },
  navRow:  { flexDirection: 'row', gap: 12, alignItems: 'center' },
  btn:     { backgroundColor: NAVY, paddingVertical: 14, borderRadius: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 12 },
  btnDisabled: { opacity: 0.4 },
  btnText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  backBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 14, paddingHorizontal: 16, borderWidth: 1.5, borderColor: '#D1D5DB', borderRadius: 12 },
  backBtnText: { fontSize: 15, fontWeight: '600', color: NAVY },
  confirmTitle: { fontSize: 20, fontWeight: '800', color: NAVY, marginBottom: 20 },
  confirmRow: { backgroundColor: '#fff', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#E5E7EB' },
  confirmLabel: { fontSize: 11, fontWeight: '700', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 6 },
  confirmValue: { fontSize: 15, color: '#1F2937', lineHeight: 22 },
  editBtn: { alignItems: 'center', paddingVertical: 12 },
  editBtnText: { fontSize: 14, color: NAVY, fontWeight: '600' },
  errorCard: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 14 },
  errorTitle: { fontSize: 20, fontWeight: '800', color: '#DC2626', textAlign: 'center' },
  errorSub:   { fontSize: 14, color: '#6B7280', textAlign: 'center' },
  doneCard: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 14 },
  doneTitle: { fontSize: 22, fontWeight: '800', color: NAVY },
  doneSub:  { fontSize: 15, color: '#6B7280', textAlign: 'center', lineHeight: 22 },
  footer:  { textAlign: 'center', fontSize: 11, color: '#D1D5DB', paddingBottom: 16 },
});
