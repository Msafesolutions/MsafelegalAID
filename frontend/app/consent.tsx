/**
 * P0-Fix4 — DPDP / PIPEDA Consent Gate
 * Shown on first launch (after language selection, before OTP/login) and
 * whenever CONSENT_NOTICE_VERSION is newer than the user's stored version.
 *
 * Rules (from spec):
 *  • Age choice required (none pre-selected). Under-18 → blocked from account creation.
 *  • terms_checkbox + data_checkbox UNCHECKED by default; Continue disabled until both ticked + age chosen.
 *  • Optional analytics + updates toggles, both OFF by default.
 *  • Logs to /api/consent/log (append-only, anon_id for pre-login callers).
 *  • After consent, navigates to /login (or back, when re-shown for version bump).
 */
import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, Pressable, Switch, StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { consentStrings, CONSENT_NOTICE_VERSION, ConsentLang } from '@/src/consentStrings';
import { API_BASE, useAuth } from '@/src/auth';

const NAVY   = '#1E3A8A';
const SAFFRON = '#F59E0B';
const GREEN  = '#059669';
const RED    = '#DC2626';
const MUTED  = '#6B7280';
const BORDER = '#E2E8F0';
const BG     = '#F8FAFC';

// Key used to store accepted version locally (before / without login)
export const CONSENT_VERSION_KEY = 'gk_consent_version';
export const CONSENT_ANON_KEY    = 'gk_consent_anon_id';
export const CONSENT_PREFS_KEY   = 'gk_consent_prefs';

type AgeChoice = '18+' | 'under18' | null;

export default function ConsentScreen() {
  const router = useRouter();
  const { token, user, language } = useAuth();
  const params = useLocalSearchParams<{ mode?: string }>();
  const isUpdate = params.mode === 'update';   // re-shown for version bump
  const insets = useSafeAreaInsets();

  const PLACEHOLDERS: Record<string, string> = {
    '{{DATA_LOCATION}}':           'India (cloud-hosted, encrypted at rest)',
    '{{GRIEVANCE_OFFICER_NAME}}':  'Grievance Officer, Calviltech Digital Solutions Pvt Ltd',
    '{{GRIEVANCE_EMAIL}}':         'grievance@calviltech.com',
  };

  // Replace any template placeholders in a language block's string values
  function applyPlaceholders(obj: any): any {
    if (typeof obj === 'string') {
      return Object.entries(PLACEHOLDERS).reduce((s, [k, v]) => s.replace(k, v), obj);
    }
    if (Array.isArray(obj)) return obj.map(applyPlaceholders);
    if (obj && typeof obj === 'object') {
      return Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, applyPlaceholders(v)]));
    }
    return obj;
  }

  const langCode = language?.code || 'en';
  const rawStrings = consentStrings[langCode] || consentStrings['en'];
  const strings: ConsentLang = applyPlaceholders(rawStrings);

  const [age, setAge]           = useState<AgeChoice>(null);
  const [termsTicked, setTerms] = useState(false);
  const [dataTicked,  setData]  = useState(false);
  const [analytics,  setAnalyt] = useState(false);
  const [updates,    setUpdates] = useState(false);
  const [saving, setSaving]     = useState(false);

  const canContinue = age === '18+' && termsTicked && dataTicked;

  const handleContinue = useCallback(async () => {
    if (!canContinue) return;
    setSaving(true);
    try {
      const purposes = { core: true, analytics, updates };
      const appVersion = Constants.expoConfig?.version || '1.0.0';

      // Persist locally first (works even without internet)
      await AsyncStorage.setItem(CONSENT_VERSION_KEY, CONSENT_NOTICE_VERSION);
      await AsyncStorage.setItem(CONSENT_PREFS_KEY, JSON.stringify(purposes));

      // Build or reuse an anonymous ID for pre-login users
      let anonId = await AsyncStorage.getItem(CONSENT_ANON_KEY);
      if (!anonId) {
        anonId = `anon-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
        await AsyncStorage.setItem(CONSENT_ANON_KEY, anonId);
      }

      // POST to backend (best-effort — don't block the UX if offline)
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      fetch(`${API_BASE}/api/consent/log`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          notice_version:   CONSENT_NOTICE_VERSION,
          purposes,
          language:         langCode,
          age_confirmed_18: true,
          anon_id:          user ? null : anonId,
          app_version:      appVersion,
        }),
      }).catch(() => {/* offline — will sync on next request */});

      // Navigate forward
      if (isUpdate) {
        router.back();
      } else {
        router.replace('/login');
      }
    } finally {
      setSaving(false);
    }
  }, [canContinue, analytics, updates, langCode, token, user, isUpdate, router]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 32 }]}
        showsVerticalScrollIndicator={false}
      >
        {/* Title */}
        <View style={styles.titleRow}>
          <View style={styles.logoBox}>
            <Text style={styles.logoChar}>ध</Text>
          </View>
          <View style={{ flex: 1, marginLeft: 10 }}>
            <Text style={styles.title}>{strings.title}</Text>
          </View>
        </View>

        {/* Intro */}
        <Text style={styles.intro}>{strings.intro}</Text>

        {/* What we collect */}
        <Text style={styles.sectionHeading}>{strings.collect_heading}</Text>
        {(strings.collect_items || []).map((item, i) => (
          <View key={i} style={styles.bulletRow}>
            <Ionicons name="checkmark-circle-outline" size={16} color={GREEN} style={{ marginTop: 2 }} />
            <Text style={styles.bulletText}>{item}</Text>
          </View>
        ))}

        {/* What we never do */}
        <Text style={styles.sectionHeading}>{strings.never_heading}</Text>
        {(strings.never_items || []).map((item, i) => (
          <View key={i} style={styles.bulletRow}>
            <Ionicons name="close-circle-outline" size={16} color={RED} style={{ marginTop: 2 }} />
            <Text style={styles.bulletText}>{item}</Text>
          </View>
        ))}

        {/* Storage */}
        <View style={styles.infoBox}>
          <Text style={styles.infoText}>{strings.storage}</Text>
        </View>

        {/* Rights */}
        <Text style={styles.sectionHeading}>{strings.rights_heading}</Text>
        <Text style={styles.bodyText}>{strings.rights_body}</Text>

        {/* Grievance */}
        <View style={styles.infoBox}>
          <Text style={styles.infoText}>{strings.grievance}</Text>
        </View>

        {/* ── Age gate ─────────────────────────────────────────── */}
        <Text style={styles.sectionHeading}>{strings.age_heading}</Text>
        <View style={styles.radioGroup}>
          <Pressable
            style={[styles.radioBtn, age === '18+' && styles.radioBtnSelected]}
            onPress={() => setAge('18+')}
          >
            <View style={[styles.radioCircle, age === '18+' && styles.radioCircleSelected]}>
              {age === '18+' && <View style={styles.radioDot} />}
            </View>
            <Text style={[styles.radioLabel, age === '18+' && styles.radioLabelSelected]}>
              {strings.age_18_plus}
            </Text>
          </Pressable>

          <Pressable
            style={[styles.radioBtn, age === 'under18' && styles.radioBtnUnder]}
            onPress={() => setAge('under18')}
          >
            <View style={[styles.radioCircle, age === 'under18' && styles.radioCircleUnder]}>
              {age === 'under18' && <View style={styles.radioDotUnder} />}
            </View>
            <Text style={[styles.radioLabel, age === 'under18' && styles.radioLabelUnder]}>
              {strings.age_under_18}
            </Text>
          </Pressable>
        </View>

        {/* Under-18 message */}
        {age === 'under18' && (
          <View style={styles.under18Box}>
            <Ionicons name="information-circle-outline" size={20} color={NAVY} />
            <Text style={styles.under18Text}>{strings.age_under_message}</Text>
            <View style={styles.under18Btns}>
              <Pressable
                style={styles.under18Btn}
                onPress={() => router.push('/(tabs)/lookup' as any)}
              >
                <Text style={styles.under18BtnText}>{strings.emergency_btn}</Text>
              </Pressable>
              <Pressable
                style={[styles.under18Btn, { backgroundColor: '#EEF2FF', borderColor: NAVY }]}
                onPress={() => router.push('/(tabs)/rights' as any)}
              >
                <Text style={[styles.under18BtnText, { color: NAVY }]}>{strings.rights_btn}</Text>
              </Pressable>
            </View>
          </View>
        )}

        {/* ── Required checkboxes ──────────────────────────────── */}
        <View style={styles.divider} />

        <Pressable style={styles.checkRow} onPress={() => setTerms(v => !v)}>
          <View style={[styles.checkbox, termsTicked && styles.checkboxChecked]}>
            {termsTicked && <Ionicons name="checkmark" size={14} color="#fff" />}
          </View>
          <Text style={styles.checkLabel}>{strings.terms_checkbox}</Text>
        </Pressable>

        <Pressable style={styles.checkRow} onPress={() => setData(v => !v)}>
          <View style={[styles.checkbox, dataTicked && styles.checkboxChecked]}>
            {dataTicked && <Ionicons name="checkmark" size={14} color="#fff" />}
          </View>
          <Text style={styles.checkLabel}>{strings.data_checkbox}</Text>
        </Pressable>

        {/* ── Optional purposes ────────────────────────────────── */}
        <View style={styles.divider} />
        <Text style={styles.optionalHeading}>{strings.optional_heading}</Text>

        <View style={styles.toggleRow}>
          <Text style={styles.toggleLabel}>{strings.analytics_label}</Text>
          <Switch
            value={analytics}
            onValueChange={setAnalyt}
            trackColor={{ false: BORDER, true: SAFFRON }}
            thumbColor="#fff"
          />
        </View>

        <View style={styles.toggleRow}>
          <Text style={styles.toggleLabel}>{strings.updates_label}</Text>
          <Switch
            value={updates}
            onValueChange={setUpdates}
            trackColor={{ false: BORDER, true: SAFFRON }}
            thumbColor="#fff"
          />
        </View>

        {/* ── Continue button ───────────────────────────────────── */}
        <Pressable
          style={[styles.continueBtn, !canContinue && styles.continueBtnDisabled]}
          onPress={handleContinue}
          disabled={!canContinue || saving}
        >
          {saving
            ? <ActivityIndicator size="small" color="#fff" />
            : <Text style={styles.continueBtnText}>{strings.continue_btn}</Text>
          }
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:            { flex: 1, backgroundColor: BG },
  scroll:          { flex: 1 },
  content:         { padding: 20 },
  titleRow:        { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  logoBox:         { width: 40, height: 40, borderRadius: 10, backgroundColor: SAFFRON, alignItems: 'center', justifyContent: 'center' },
  logoChar:        { fontSize: 22, fontWeight: '800', color: NAVY },
  title:           { fontSize: 22, fontWeight: '800', color: NAVY },
  intro:           { fontSize: 14, color: '#374151', lineHeight: 22, marginBottom: 20 },
  sectionHeading:  { fontSize: 14, fontWeight: '700', color: NAVY, marginTop: 20, marginBottom: 8 },
  bodyText:        { fontSize: 13, color: '#374151', lineHeight: 20 },
  bulletRow:       { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 6 },
  bulletText:      { flex: 1, fontSize: 13, color: '#374151', lineHeight: 20 },
  infoBox:         { backgroundColor: 'rgba(30,58,138,0.05)', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(30,58,138,0.12)', padding: 12, marginTop: 12 },
  infoText:        { fontSize: 12, color: MUTED, lineHeight: 18 },
  // age gate
  radioGroup:      { gap: 10, marginTop: 4 },
  radioBtn:        { flexDirection: 'row', alignItems: 'center', gap: 10, borderWidth: 1.5, borderColor: BORDER, borderRadius: 10, padding: 14, backgroundColor: '#fff' },
  radioBtnSelected:{ borderColor: NAVY, backgroundColor: '#EEF2FF' },
  radioBtnUnder:   { borderColor: '#F97316', backgroundColor: '#FFF7ED' },
  radioCircle:     { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: BORDER, alignItems: 'center', justifyContent: 'center' },
  radioCircleSelected: { borderColor: NAVY },
  radioCircleUnder:{ borderColor: '#F97316' },
  radioDot:        { width: 10, height: 10, borderRadius: 5, backgroundColor: NAVY },
  radioDotUnder:   { width: 10, height: 10, borderRadius: 5, backgroundColor: '#F97316' },
  radioLabel:      { fontSize: 14, color: '#374151', fontWeight: '500' },
  radioLabelSelected: { color: NAVY, fontWeight: '700' },
  radioLabelUnder: { color: '#F97316', fontWeight: '700' },
  // under-18
  under18Box:      { marginTop: 16, borderRadius: 10, backgroundColor: '#FFF7ED', borderWidth: 1, borderColor: '#FED7AA', padding: 14, gap: 10 },
  under18Text:     { fontSize: 13, color: '#7C3AED', lineHeight: 20, flex: 1 },
  under18Btns:     { flexDirection: 'row', gap: 10 },
  under18Btn:      { flex: 1, backgroundColor: '#FEE2E2', borderWidth: 1, borderColor: '#F87171', borderRadius: 8, paddingVertical: 10, alignItems: 'center' },
  under18BtnText:  { fontSize: 13, fontWeight: '600', color: RED },
  // checkboxes
  divider:         { height: 1, backgroundColor: BORDER, marginVertical: 20 },
  checkRow:        { flexDirection: 'row', alignItems: 'flex-start', gap: 12, marginBottom: 14 },
  checkbox:        { width: 22, height: 22, borderRadius: 5, borderWidth: 2, borderColor: BORDER, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', marginTop: 1 },
  checkboxChecked: { backgroundColor: NAVY, borderColor: NAVY },
  checkLabel:      { flex: 1, fontSize: 13, color: '#374151', lineHeight: 20 },
  // optional toggles
  optionalHeading: { fontSize: 12, fontWeight: '700', color: MUTED, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 },
  toggleRow:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: BORDER },
  toggleLabel:     { flex: 1, fontSize: 13, color: '#374151', marginRight: 12 },
  // continue btn
  continueBtn:         { marginTop: 28, backgroundColor: NAVY, borderRadius: 12, paddingVertical: 16, alignItems: 'center' },
  continueBtnDisabled: { backgroundColor: '#CBD5E1' },
  continueBtnText:     { color: '#fff', fontSize: 16, fontWeight: '700' },
});
