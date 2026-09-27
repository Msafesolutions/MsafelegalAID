/**
 * Visitor Mode — V4: Lost Passport Workflow + V3: Speak For Me
 */
import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, Alert, Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '@/src/theme';
import { loadVisitorSession, VisitorSession } from '@/src/visitor/session';
import { LOST_PASSPORT_STEPS, EMBASSY_CONTACTS, WorkflowStep } from '@/src/visitor/content';
import { API_BASE, useAuth } from '@/src/auth';

const C = theme.colors;

export default function VisitorLostPassport() {
  const { token } = useAuth();
  const [session, setSession] = useState<VisitorSession | null>(null);
  const [speaking, setSpeaking] = useState<string | null>(null);

  useEffect(() => {
    loadVisitorSession().then(s => setSession(s));
  }, []);

  const lc   = session?.touristLang.code || 'en';
  const t    = (map: Record<string, string> | undefined) => map ? (map[lc] || map['en'] || '') : '';
  const emb  = EMBASSY_CONTACTS[lc] || EMBASSY_CONTACTS['en'];

  // V3: Speak For Me
  const speakForMe = useCallback(async (step: WorkflowStep) => {
    if (!step.speak_hi) return;
    if (!token) {
      Alert.alert('Sign in required', 'Sign in to DHARA to use Speak For Me.');
      return;
    }
    setSpeaking(step.id);
    try {
      const res = await fetch(`${API_BASE}/api/voice/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ text: step.speak_hi, language: 'hi', voice: 'alloy' }),
      });
      if (!res.ok) throw new Error('TTS failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new (window as any).Audio(url);
      audio.onended = () => { setSpeaking(null); URL.revokeObjectURL(url); };
      audio.onerror = () => setSpeaking(null);
      await audio.play();
    } catch {
      setSpeaking(null);
      Alert.alert('Speak For Me', step.speak_hi, [{ text: 'OK' }]);
    }
  }, [token]);

  if (!session) {
    return (
      <SafeAreaView style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={C.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={s.content}>
        {/* Header */}
        <View style={s.header}>
          <Ionicons name="document-outline" size={36} color="#fff" />
          <View style={s.headerText}>
            <Text style={s.headerTitle}>Lost Passport</Text>
            <Text style={s.headerSub}>{session.indianStateName} · {session.touristLang.label}</Text>
          </View>
        </View>

        {/* Embassy card */}
        <View style={s.embassyCard}>
          <View style={s.embassyRow}>
            <Ionicons name="flag" size={20} color={C.gold} />
            <Text style={s.embassyTitle}>{emb.name}</Text>
          </View>
          <Text style={s.embassyCity}>{emb.city}</Text>
          <Pressable
            style={s.embassyCall}
            onPress={() => Linking.openURL(`tel:${emb.phone.replace(/[\s-]/g,'')}`).catch(() => {})}
          >
            <Ionicons name="call" size={16} color={C.gold} />
            <Text style={s.embassyPhone}>{emb.phone}</Text>
          </Pressable>
        </View>

        {/* Steps */}
        {LOST_PASSPORT_STEPS.map((step, idx) => (
          <View key={step.id} style={s.stepCard}>
            <View style={s.stepNumRow}>
              <View style={s.stepNum}><Text style={s.stepNumText}>{idx + 1}</Text></View>
              <Text style={s.stepTitle}>{t(step.title)}</Text>
            </View>

            <Text style={s.stepBody}>{t(step.body)}</Text>

            {/* Call / URL button */}
            {step.callNumber && (
              <Pressable
                style={[s.actionBtn, { backgroundColor: C.primary }]}
                onPress={() => {
                  const num = step.callNumber!;
                  const url = num.startsWith('http') ? num : `tel:${num}`;
                  Linking.openURL(url).catch(() => {});
                }}
              >
                <Ionicons
                  name={step.callNumber.startsWith('http') ? 'globe-outline' : 'call'}
                  size={18} color="#fff"
                />
                <Text style={s.actionBtnText}>{t(step.callLabel!) || step.callNumber}</Text>
              </Pressable>
            )}

            {/* Speak For Me */}
            {step.speak_hi && (
              <View>
                <Text style={s.speakLabel}>🎙 SPEAK FOR ME (to official in Hindi):</Text>
                <View style={s.speakBox}>
                  <Text style={s.speakText}>{step.speak_hi}</Text>
                </View>
                <Pressable
                  style={[s.actionBtn, { backgroundColor: C.primaryMid, marginTop: 8 }]}
                  onPress={() => speakForMe(step)}
                  disabled={speaking === step.id}
                >
                  {speaking === step.id
                    ? <ActivityIndicator size="small" color="#fff" />
                    : <Ionicons name="volume-high-outline" size={18} color="#fff" />}
                  <Text style={s.actionBtnText}>
                    {speaking === step.id ? 'Playing…' : 'Play in Hindi'}
                  </Text>
                </Pressable>
              </View>
            )}
          </View>
        ))}

        {/* FIR shortcut */}
        <View style={s.firCard}>
          <Ionicons name="information-circle" size={20} color={C.primary} />
          <Text style={s.firText}>
            Need help drafting the police complaint? Use DHARA&apos;s FIR builder — tap <Text style={{ fontWeight: '700' }}>Complaints</Text> tab in the main app.
          </Text>
        </View>

        <Text style={s.footnote}>
          DHARA provides general guidance only. Always contact your embassy first for official assistance.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:    { flex: 1, backgroundColor: C.background },
  content: { padding: 16, paddingBottom: 40 },

  header:     {
    backgroundColor: C.primary, borderRadius: 16, padding: 18,
    flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 14,
  },
  headerText:  { flex: 1 },
  headerTitle: { fontSize: 18, fontWeight: '800', color: '#fff' },
  headerSub:   { fontSize: 12, color: '#C5CEEA', marginTop: 3 },

  embassyCard: {
    backgroundColor: C.primary, borderRadius: 14, padding: 16, marginBottom: 14,
    gap: 6,
  },
  embassyRow:  { flexDirection: 'row', alignItems: 'center', gap: 8 },
  embassyTitle:{ fontSize: 14, fontWeight: '700', color: '#fff', flex: 1 },
  embassyCity: { fontSize: 12, color: '#C5CEEA', marginLeft: 28 },
  embassyCall: { flexDirection: 'row', alignItems: 'center', gap: 8, marginLeft: 28, marginTop: 4 },
  embassyPhone:{ fontSize: 15, fontWeight: '700', color: C.gold },

  stepCard:   {
    backgroundColor: C.surface, borderRadius: 14, padding: 16,
    marginBottom: 12, borderWidth: 1, borderColor: C.divider,
  },
  stepNumRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  stepNum:    {
    width: 28, height: 28, borderRadius: 14, backgroundColor: C.primary,
    alignItems: 'center', justifyContent: 'center',
  },
  stepNumText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  stepTitle:   { flex: 1, fontSize: 15, fontWeight: '700', color: C.onSurface },
  stepBody:    { fontSize: 13, color: C.onSurfaceTertiary, lineHeight: 20, marginBottom: 12 },

  actionBtn:     {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, borderRadius: 10, paddingVertical: 12, marginBottom: 8,
  },
  actionBtnText: { fontSize: 14, fontWeight: '700', color: '#fff' },

  speakLabel: { fontSize: 11, fontWeight: '700', color: C.primary, letterSpacing: 0.5, marginBottom: 6 },
  speakBox:   {
    backgroundColor: C.navySoft, borderRadius: 10, padding: 12,
    borderLeftWidth: 3, borderLeftColor: C.primary,
  },
  speakText:  { fontSize: 14, color: C.primary, lineHeight: 22, fontStyle: 'italic' },

  firCard: {
    flexDirection: 'row', gap: 10, backgroundColor: '#EFF6FF',
    borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#BFDBFE',
    alignItems: 'flex-start', marginBottom: 12,
  },
  firText: { flex: 1, fontSize: 13, color: C.primary, lineHeight: 19 },

  footnote: {
    fontSize: 11, color: C.onSurfaceTertiary, textAlign: 'center',
    lineHeight: 17, marginTop: 4,
  },
});
