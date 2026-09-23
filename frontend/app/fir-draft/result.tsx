/**
 * FIR Draft Result Screen (v3)
 * Displays the generated FIR complaint letter with share/export options.
 * Receives draft text and sessionId from the new Interview Engine.
 */

import React, { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, Share, Platform, Alert, Clipboard,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system/legacy';

// ── Theme ─────────────────────────────────────────────────────────────────────
const NAVY   = '#14365A';
const GOLD   = '#D3B675';
const CREAM  = '#F5F0E6';
const SURFACE = '#FDFBF7';
const MUTED  = '#4A5A6E';
const BORDER = '#D1D5DB';
const RED    = '#B91C1C';

const HELPLINES = [
  { label: 'Police',         number: '100',   icon: 'shield-outline' },
  { label: 'Women Helpline', number: '181',   icon: 'woman-outline' },
  { label: 'NALSA Legal Aid',number: '15100', icon: 'briefcase-outline' },
  { label: 'Cybercrime',     number: '1930',  icon: 'laptop-outline' },
  { label: 'Childline',      number: '1098',  icon: 'people-outline' },
];

export default function FIRResult() {
  const params = useLocalSearchParams<{ sessionId?: string; draft?: string }>();
  const router = useRouter();

  const [loading] = useState(false);
  const [copyDone, setCopyDone] = useState(false);
  const [sharing, setSharing] = useState(false);

  // Draft text: either passed as param, or loaded from session API
  const draftText = params.draft || '';

  // ── Copy to clipboard ──────────────────────────────────────────────────────
  const handleCopy = useCallback(() => {
    if (!draftText) return;
    if (Platform.OS === 'web') {
      // navigator.clipboard is available on web
      navigator.clipboard?.writeText(draftText).catch(() => {});
    } else {
      Clipboard.setString(draftText);
    }
    setCopyDone(true);
    setTimeout(() => setCopyDone(false), 2500);
  }, [draftText]);

  // ── Share as text ──────────────────────────────────────────────────────────
  const handleShare = useCallback(async () => {
    if (!draftText) return;
    setSharing(true);
    try {
      await Share.share({ message: draftText, title: 'FIR Complaint Draft (DHARA)' });
    } catch {
      Alert.alert('Share failed', 'Could not share the draft.');
    } finally {
      setSharing(false);
    }
  }, [draftText]);

  // ── Export as .txt file ────────────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    if (!draftText) return;
    if (Platform.OS === 'web') {
      const blob = new Blob([draftText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'FIR_Draft_DHARA.txt';
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    try {
      const dir = FileSystem.documentDirectory || FileSystem.cacheDirectory;
      if (!dir) throw new Error('No directory available');
      const fileUri = dir + `FIR_Draft_${Date.now()}.txt`;
      await FileSystem.writeAsStringAsync(fileUri, draftText, { encoding: FileSystem.EncodingType.UTF8 });
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(fileUri, { mimeType: 'text/plain', dialogTitle: 'Save FIR Draft' });
      } else {
        Alert.alert('Saved', 'Draft exported successfully.');
      }
    } catch {
      Alert.alert('Export failed', 'Could not export the draft. Use Share instead.');
    }
  }, [draftText]);

  if (loading) {
    return (
      <SafeAreaView style={styles.root}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={NAVY} />
          <Text style={styles.loadingText}>Loading your draft…</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!draftText) {
    return (
      <SafeAreaView style={styles.root}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={NAVY} />
          <Text style={styles.loadingText}>Loading your draft…</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
          <Ionicons name="arrow-back" size={22} color={SURFACE} />
        </Pressable>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>Your FIR Draft</Text>
          <Text style={styles.headerSub}>Ready to present at police station</Text>
        </View>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {/* Disclaimer banner */}
        <View style={styles.disclaimerCard}>
          <Ionicons name="alert-circle" size={18} color={RED} />
          <Text style={styles.disclaimerText}>
            <Text style={{ fontWeight: '700' }}>CITIZEN DRAFT — NOT A REGISTERED FIR.</Text>
            {' '}Present this at the police station for official registration under Section 173(1) BNSS.
          </Text>
        </View>

        {/* Zero FIR note */}
        <View style={styles.zeroFirCard}>
          <Ionicons name="information-circle" size={18} color={NAVY} />
          <Text style={styles.zeroFirText}>
            <Text style={{ fontWeight: '700' }}>Zero FIR Right: </Text>
            You can file this FIR at ANY police station in India. They are legally required to accept it (Section 173(1) BNSS).
          </Text>
        </View>

        {/* Draft text */}
        <View style={styles.draftCard}>
          <View style={styles.draftHeader}>
            <Ionicons name="document-text-outline" size={18} color={NAVY} />
            <Text style={styles.draftTitle}>Complaint Letter</Text>
          </View>
          <Text style={styles.draftText} selectable>{draftText}</Text>
        </View>

        {/* Action buttons */}
        <View style={styles.actions}>
          <Pressable style={styles.actionBtn} onPress={handleCopy}>
            <Ionicons name={copyDone ? 'checkmark-circle' : 'copy-outline'} size={20} color={NAVY} />
            <Text style={styles.actionBtnText}>{copyDone ? 'Copied!' : 'Copy Text'}</Text>
          </Pressable>
          <Pressable style={styles.actionBtn} onPress={handleShare} disabled={sharing}>
            {sharing
              ? <ActivityIndicator size="small" color={NAVY} />
              : <Ionicons name="share-outline" size={20} color={NAVY} />}
            <Text style={styles.actionBtnText}>Share</Text>
          </Pressable>
          <Pressable style={styles.actionBtn} onPress={handleExport}>
            <Ionicons name="download-outline" size={20} color={NAVY} />
            <Text style={styles.actionBtnText}>Export .txt</Text>
          </Pressable>
        </View>

        {/* Next steps */}
        <View style={styles.stepsCard}>
          <Text style={styles.stepsTitle}>What to do next</Text>
          {[
            'Print or save this draft on your phone.',
            'Visit the nearest police station (any station accepts Zero FIR).',
            'Give this document to the Station House Officer (SHO).',
            'Insist on getting a copy of the registered FIR — it\'s your right.',
            'Note the FIR number and officer\'s name for your records.',
          ].map((step, i) => (
            <View key={i} style={styles.stepRow}>
              <View style={styles.stepNum}><Text style={styles.stepNumText}>{i + 1}</Text></View>
              <Text style={styles.stepText}>{step}</Text>
            </View>
          ))}
        </View>

        {/* Helplines */}
        <View style={styles.helplinesCard}>
          <Text style={styles.helplinesTitle}>Emergency Helplines (Free)</Text>
          <View style={styles.helplinesGrid}>
            {HELPLINES.map(h => (
              <View key={h.number} style={styles.helplineItem}>
                <Ionicons name={h.icon as any} size={16} color={NAVY} />
                <Text style={styles.helplineNum}>{h.number}</Text>
                <Text style={styles.helplineLabel}>{h.label}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Start new complaint */}
        <Pressable
          style={styles.newComplaintBtn}
          onPress={() => router.replace('/fir-draft')}
        >
          <Ionicons name="add-circle-outline" size={20} color={NAVY} />
          <Text style={styles.newComplaintText}>Start New Complaint</Text>
        </Pressable>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: SURFACE },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  loadingText: { color: MUTED, fontSize: 15 },

  // Header
  header: {
    backgroundColor: NAVY, flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 16, paddingVertical: 12, gap: 12,
  },
  headerCenter: { flex: 1 },
  headerTitle: { fontSize: 16, fontWeight: '700', color: '#fff' },
  headerSub: { fontSize: 12, color: GOLD },
  backBtn: { padding: 4 },

  // Scroll
  scroll: { flex: 1 },
  scrollContent: { padding: 16, gap: 16, paddingBottom: 40 },

  // Disclaimer
  disclaimerCard: {
    flexDirection: 'row', gap: 10, backgroundColor: '#FEF2F2',
    borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#FECACA',
    alignItems: 'flex-start',
  },
  disclaimerText: { flex: 1, fontSize: 13, color: '#7F1D1D', lineHeight: 19 },

  // Zero FIR
  zeroFirCard: {
    flexDirection: 'row', gap: 10, backgroundColor: '#EFF6FF',
    borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#BFDBFE',
    alignItems: 'flex-start',
  },
  zeroFirText: { flex: 1, fontSize: 13, color: NAVY, lineHeight: 19 },

  // Draft
  draftCard: {
    backgroundColor: CREAM, borderRadius: 14, padding: 16,
    borderWidth: 1, borderColor: '#D6C9B0',
  },
  draftHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  draftTitle: { fontSize: 15, fontWeight: '700', color: NAVY },
  draftText: { fontSize: 13, color: '#2D2D2D', lineHeight: 22, fontFamily: Platform.OS === 'ios' ? 'Courier New' : 'monospace' },

  // Actions
  actions: { flexDirection: 'row', gap: 8 },
  actionBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, backgroundColor: CREAM, borderRadius: 10, paddingVertical: 12,
    borderWidth: 1.5, borderColor: BORDER,
  },
  actionBtnText: { fontSize: 13, color: NAVY, fontWeight: '600' },

  // Steps
  stepsCard: {
    backgroundColor: SURFACE, borderRadius: 14, padding: 16,
    borderWidth: 1, borderColor: BORDER,
  },
  stepsTitle: { fontSize: 15, fontWeight: '700', color: NAVY, marginBottom: 12 },
  stepRow: { flexDirection: 'row', gap: 10, marginBottom: 10, alignItems: 'flex-start' },
  stepNum: {
    width: 24, height: 24, borderRadius: 12, backgroundColor: NAVY,
    alignItems: 'center', justifyContent: 'center',
  },
  stepNumText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  stepText: { flex: 1, fontSize: 13, color: MUTED, lineHeight: 19 },

  // Helplines
  helplinesCard: {
    backgroundColor: NAVY, borderRadius: 14, padding: 16,
  },
  helplinesTitle: { fontSize: 14, fontWeight: '700', color: GOLD, marginBottom: 12 },
  helplinesGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  helplineItem: {
    backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 10, padding: 10,
    alignItems: 'center', minWidth: 80, gap: 4,
  },
  helplineNum: { fontSize: 16, fontWeight: '800', color: '#fff' },
  helplineLabel: { fontSize: 10, color: 'rgba(255,255,255,0.7)', textAlign: 'center' },

  // New complaint
  newComplaintBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, borderRadius: 12, paddingVertical: 14,
    backgroundColor: CREAM, borderWidth: 1.5, borderColor: BORDER,
  },
  newComplaintText: { color: NAVY, fontSize: 14, fontWeight: '600' },
});
