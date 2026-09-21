/**
 * FIR Draft Result Screen
 * Shows: safety card (if triggered) → FIR draft → document checklist → PDF export
 * Phase 5: template display, checklist, disclaimer
 * Phase 6: analytics events, PDF/print export
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, Share, Platform, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { useAuth, API_BASE } from '@/src/auth';

const NAVY  = '#14365A';
const GOLD  = '#D3B675';
const RED   = '#DC2626';
const GREEN = '#059669';

function SafetyBanner({ flags }: { flags: string[] }) {
  if (!flags.length) return null;
  return (
    <View style={sb.card}>
      <Ionicons name="alert-circle" size={22} color={RED} />
      <View style={{ flex: 1 }}>
        <Text style={sb.title}>Helplines — please save these numbers</Text>
        {flags.includes('POCSO') && <Text style={sb.line}>🆘 Childline: <Text style={sb.num}>1098</Text> (24×7 FREE)</Text>}
        {(flags.includes('SEXUAL') || flags.includes('DV')) && <Text style={sb.line}>👩 Women Helpline: <Text style={sb.num}>181</Text> (24×7 FREE)</Text>}
        <Text style={sb.line}>⚖️ NALSA Free Legal Aid: <Text style={sb.num}>15100</Text></Text>
        <Text style={sb.line}>🚔 Police: <Text style={sb.num}>100</Text></Text>
      </View>
    </View>
  );
}

export default function FIRResult() {
  const { draftId, lang } = useLocalSearchParams<{ draftId: string; lang: string }>();
  const { token, user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<any>(null);
  const [exporting, setExporting] = useState(false);
  const [followUpShown, setFollowUpShown] = useState(false);

  const generate = useCallback(async () => {
    // Always reset state before each attempt so errors from auth-loading
    // race don't persist after a successful retry or re-trigger.
    setError('');
    setLoading(true);
    if (!draftId || !user?.id || !token) { setError('Session expired — please restart.'); setLoading(false); return; }
    try {
      const r = await fetch(`${API_BASE}/api/fir/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ draft_id: draftId, user_id: user.id, language: lang ?? 'en' }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setData(d);
      // Phase 6: fire analytics event
      fetch(`${API_BASE}/api/fir/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ user_id: user.id, draft_id: draftId, event: 'fir_draft_generated' }),
      }).catch(() => {});
    } catch (e: any) {
      setError('Could not generate FIR draft. Check your connection and try again.');
    } finally { setLoading(false); }
  }, [draftId, user?.id, token, lang]);

  // Wait for auth to finish loading before triggering generate.
  // This prevents "Session expired" flash when AsyncStorage hasn't
  // resolved yet on first render.
  useEffect(() => {
    if (authLoading) return;
    generate();
  }, [generate, authLoading]);

  const exportPDF = async () => {
    if (!data?.draft_text) return;
    setExporting(true);
    try {
      // Build HTML with Unicode support for Devanagari / Tamil scripts
      const html = `<!DOCTYPE html>
<html lang="${lang ?? 'en'}">
<head>
  <meta charset="UTF-8"/>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari&family=Noto+Sans+Tamil&family=Noto+Sans&display=swap');
    body { font-family: 'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Tamil', sans-serif;
           font-size: 13px; line-height: 1.7; margin: 24px; color: #1a1a1a; }
    pre { white-space: pre-wrap; word-break: break-word; font-family: inherit; }
    .watermark { color: #dc2626; font-weight: 700; font-size: 11px; background: #fef2f2;
                 padding: 8px 12px; border-radius: 6px; margin-bottom: 16px; }
  </style>
</head>
<body>
  <div class="watermark">⚠️ CITIZEN DRAFT — NOT A REGISTERED FIR — PENDING LEGAL COUNSEL REVIEW</div>
  <pre>${data.draft_text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
</body>
</html>`;
      const { uri } = await Print.printToFileAsync({ html, base64: false });
      // Phase 6: analytics
      fetch(`${API_BASE}/api/fir/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ user_id: user?.id, draft_id: draftId, event: 'fir_draft_downloaded' }),
      }).catch(() => {});
      if (Platform.OS === 'web') {
        Alert.alert('PDF Saved', `Saved to: ${uri}`);
      } else {
        const canShare = await Sharing.isAvailableAsync();
        if (canShare) await Sharing.shareAsync(uri, { mimeType: 'application/pdf', dialogTitle: 'Save or Share FIR Draft' });
        else Alert.alert('PDF Ready', `Saved to: ${uri}`);
      }
    } catch (e) {
      Alert.alert('Export Failed', 'Could not create PDF. Please try again.');
    } finally { setExporting(false); }
  };

  const showFollowUp = () => {
    if (followUpShown) return;
    setFollowUpShown(true);
    Alert.alert(
      'Did the station accept your complaint?',
      'Your feedback helps us improve DHARA for other citizens.',
      [
        {
          text: 'Yes, FIR was registered', onPress: () =>
            fetch(`${API_BASE}/api/fir/event`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ user_id: user?.id, draft_id: draftId, event: 'fir_user_confirmed_filed', meta: { accepted: true } }),
            }).catch(() => {}),
        },
        {
          text: 'Station refused', onPress: () =>
            fetch(`${API_BASE}/api/fir/event`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ user_id: user?.id, draft_id: draftId, event: 'fir_user_confirmed_filed', meta: { accepted: false } }),
            }).catch(() => {}),
        },
        { text: 'Not yet', style: 'cancel' },
      ],
    );
  };

  if (loading) return (
    <SafeAreaView style={s.safe}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Generating FIR Draft…</Text>
      </View>
      <View style={s.center}>
        <ActivityIndicator color={NAVY} size="large" />
        <Text style={s.loadingText}>Classifying offences, finding police station…</Text>
      </View>
    </SafeAreaView>
  );

  if (error) return (
    <SafeAreaView style={s.safe}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={{ marginRight: 12 }}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </Pressable>
        <Text style={s.headerTitle}>Error</Text>
      </View>
      <View style={s.center}>
        <Ionicons name="alert-circle-outline" size={48} color={RED} />
        <Text style={s.errorText}>{error}</Text>
        <Pressable style={s.retryBtn} onPress={() => { setLoading(true); setError(''); generate(); }}>
          <Text style={s.retryBtnText}>Retry</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );

  const candidates = data?.classification?.candidates ?? [];
  const safety = data?.safety_flags ?? [];
  const ps = data?.police_station ?? {};
  const checklist = data?.document_checklist ?? [];

  return (
    <SafeAreaView style={s.safe}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={{ marginRight: 12 }}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={s.headerTitle}>Your FIR Draft</Text>
          <Text style={s.headerSub}>Tap export to save as PDF</Text>
        </View>
        <Pressable style={s.exportBtn} onPress={exportPDF} disabled={exporting}>
          {exporting
            ? <ActivityIndicator color="#fff" size="small" />
            : <Ionicons name="print-outline" size={20} color="#fff" />}
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={s.scroll}>
        {/* Safety banner — always at top if triggered */}
        <SafetyBanner flags={safety} />

        {/* Disclaimer */}
        <View style={s.disclaimerBox}>
          <Ionicons name="information-circle-outline" size={16} color={RED} />
          <Text style={s.disclaimerText}>
            This draft is a starting point to present at the police station — NOT a registered FIR and NOT legal advice.
            Suggested BNS sections are indicative only. The officer determines the final sections.
            {' '}<Text style={{ color: RED, fontWeight: '700' }}>[Disclaimer text pending legal counsel review — do not publish without approval]</Text>
          </Text>
        </View>

        {/* Police Station */}
        <View style={s.card}>
          <Text style={s.cardTitle}>📍 Suggested Police Station</Text>
          {ps.matched ? (
            <>
              <Text style={s.psName}>{ps.station}</Text>
              <Text style={s.psSub}>{ps.district} | {ps.address}</Text>
              <Text style={s.psSub}>Tel: {ps.phone}</Text>
              {ps.confidence === 'low' && <Text style={s.psNote}>⚠️ Low confidence match — confirm at local outpost</Text>}
            </>
          ) : (
            <Text style={s.psNote}>{ps.pilot_note ?? 'Location not matched — enter Maharashtra location'}</Text>
          )}
          <View style={s.zeroFirBox}>
            <Text style={s.zeroFirText}>{ps.zero_fir_note}</Text>
          </View>
        </View>

        {/* BNS Sections */}
        {candidates.length > 0 && (
          <View style={s.card}>
            <Text style={s.cardTitle}>⚖️ Suggested BNS Sections</Text>
            <Text style={s.cardNote}>Always framed as suggestions — the officer decides the final sections.</Text>
            {candidates.map((c: any, i: number) => (
              <View key={i} style={s.sectionRow}>
                <View style={s.sectionBadge}>
                  <Text style={s.sectionNum}>BNS {c.bns_section}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.sectionHead}>{c.bns_heading}</Text>
                  <Text style={s.sectionSub}>{c.ipc_equivalent} | Confidence: {c.confidence}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Document Checklist */}
        {checklist.length > 0 && (
          <View style={s.card}>
            <Text style={s.cardTitle}>📋 Document Checklist</Text>
            <Text style={s.cardNote}>Bring these to the police station for a stronger complaint:</Text>
            {checklist.map((item: string, i: number) => (
              <View key={i} style={s.checkItem}>
                <Ionicons name="checkbox-outline" size={18} color={GREEN} />
                <Text style={s.checkText}>{item}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Full Draft Text */}
        <View style={s.card}>
          <Text style={s.cardTitle}>📄 Full FIR Draft</Text>
          <Text selectable style={s.draftText}>{data?.draft_text ?? ''}</Text>
        </View>

        {/* Export + Follow-up */}
        <Pressable style={s.primaryBtn} onPress={exportPDF} disabled={exporting}>
          {exporting
            ? <ActivityIndicator color="#fff" size="small" />
            : <><Ionicons name="download-outline" size={20} color="#fff" /><Text style={s.primaryBtnText}>Export as PDF</Text></>
          }
        </Pressable>

        <Pressable style={s.secondaryBtn} onPress={showFollowUp}>
          <Ionicons name="checkmark-circle-outline" size={20} color={NAVY} />
          <Text style={s.secondaryBtnText}>Was the FIR accepted? (feedback)</Text>
        </Pressable>

        <Pressable style={[s.secondaryBtn, { marginTop: 0 }]} onPress={() => router.push('/fir-draft/drafts' as any)}>
          <Ionicons name="folder-outline" size={20} color={NAVY} />
          <Text style={s.secondaryBtnText}>View all my FIR drafts</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const sb = StyleSheet.create({
  card: { backgroundColor: '#FEF2F2', borderRadius: 12, padding: 14, flexDirection: 'row', gap: 10, alignItems: 'flex-start', marginBottom: 12, borderWidth: 1.5, borderColor: '#FCA5A5' },
  title: { fontSize: 14, fontWeight: '800', color: RED, marginBottom: 6 },
  line: { fontSize: 14, color: '#374151', marginBottom: 2 },
  num: { fontWeight: '800', color: RED },
});

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F9FAFB' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 16 },
  header: { backgroundColor: NAVY, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14, gap: 8 },
  headerTitle: { fontSize: 17, fontWeight: '800', color: '#fff', flex: 1 },
  headerSub: { fontSize: 11, color: GOLD },
  exportBtn: { padding: 8, backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 8 },
  scroll: { padding: 16, paddingBottom: 40, gap: 12 },
  disclaimerBox: { flexDirection: 'row', gap: 8, alignItems: 'flex-start', backgroundColor: '#FFF7ED', borderRadius: 10, padding: 12, borderWidth: 1, borderColor: '#FED7AA' },
  disclaimerText: { fontSize: 12, color: '#92400E', flex: 1, lineHeight: 18 },
  card: { backgroundColor: '#fff', borderRadius: 14, padding: 16, gap: 10, borderWidth: 1, borderColor: '#E5E7EB' },
  cardTitle: { fontSize: 15, fontWeight: '800', color: NAVY },
  cardNote: { fontSize: 12, color: '#6B7280' },
  psName: { fontSize: 17, fontWeight: '800', color: '#1F2937' },
  psSub: { fontSize: 13, color: '#4B5563' },
  psNote: { fontSize: 13, color: '#D97706', fontStyle: 'italic' },
  zeroFirBox: { backgroundColor: '#EFF6FF', borderRadius: 8, padding: 10, borderWidth: 1, borderColor: '#BFDBFE' },
  zeroFirText: { fontSize: 12, color: '#1E40AF', lineHeight: 18 },
  sectionRow: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', paddingVertical: 8, borderTopWidth: 1, borderTopColor: '#F3F4F6' },
  sectionBadge: { backgroundColor: NAVY, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  sectionNum: { fontSize: 12, fontWeight: '800', color: '#fff' },
  sectionHead: { fontSize: 14, fontWeight: '700', color: '#1F2937' },
  sectionSub: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  checkItem: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', paddingVertical: 4 },
  checkText: { fontSize: 13, color: '#374151', flex: 1, lineHeight: 20 },
  draftText: { fontSize: 12, color: '#1F2937', fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace', lineHeight: 20 },
  loadingText: { fontSize: 14, color: '#6B7280', textAlign: 'center' },
  errorText: { fontSize: 15, color: RED, textAlign: 'center' },
  retryBtn: { backgroundColor: NAVY, borderRadius: 12, paddingHorizontal: 24, paddingVertical: 12 },
  retryBtnText: { color: '#fff', fontWeight: '700' },
  primaryBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, backgroundColor: NAVY, borderRadius: 14, paddingVertical: 16 },
  primaryBtnText: { fontSize: 16, fontWeight: '800', color: '#fff' },
  secondaryBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderRadius: 14, paddingVertical: 14, borderWidth: 1.5, borderColor: NAVY, marginTop: 8 },
  secondaryBtnText: { fontSize: 14, fontWeight: '700', color: NAVY },
});
