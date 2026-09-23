import { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, Modal, Pressable, ScrollView, StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { API_BASE } from '../auth';
import { theme } from '../theme';
import type { ConsentCopy } from '../consentCopy';

type Topic = { id: string; title: string; summary: string; law: string; points: string[] };
const colors = theme.colors;

/** Read-only public help, outside authenticated tabs; no personal information. */
export function ConsentPublicHelp({ mode, onClose, copy }: {
  mode: 'emergency' | 'rights' | null; onClose: () => void; copy: ConsentCopy;
}) {
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setError(null);
    if (mode !== 'rights') return;
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    setTopics(null);
    void fetch(`${API_BASE}/api/reference/topics`, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => { if (!Array.isArray(data)) throw new Error(); if (active) setTopics(data); })
      .catch(() => { if (active) setError('Could not load rights information. Check your connection and try again.'); })
      .finally(() => clearTimeout(timer));
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [mode, attempt]);
  const call = (number: string) => {
    void Linking.openURL(`tel:${number}`).catch(() => setError(`Please dial ${number} on your phone.`));
  };
  return (
    <Modal visible={mode !== null} animationType="slide" onRequestClose={onClose} testID="consent-help-modal">
      <SafeAreaView style={styles.safe}>
        <Text testID="consent-help-title" style={styles.title}>{mode === 'rights' ? copy.rights : copy.emergency}</Text>
        <ScrollView testID="consent-help-scroll" contentContainerStyle={styles.content}>
          {error && <Text testID="consent-help-error" accessibilityRole="alert" style={styles.error}>{error}</Text>}
          {mode === 'emergency' ? <>
            <Text testID="consent-helpline-info" style={styles.body}>In immediate danger, call 112. For help for a child, call 1098. No account is needed.</Text>
            {['112', '1098'].map(number => <Pressable key={number} testID={`consent-call-${number}`} accessibilityRole="button" style={styles.button} onPress={() => call(number)}><Text style={styles.buttonText}>Call {number}</Text></Pressable>)}
          </> : topics ? topics.map(topic => <Text key={topic.id} testID={`consent-rights-topic-${topic.id}`} selectable style={styles.body}>
            {`${topic.title}\n${topic.summary}\n${topic.law}\n\n${topic.points.map(p => `• ${p}`).join('\n\n')}\n`}
          </Text>) : error ? <Pressable testID="consent-help-retry" accessibilityRole="button" style={styles.button} onPress={() => setAttempt(v => v + 1)}><Text style={styles.buttonText}>{copy.retry}</Text></Pressable>
            : <ActivityIndicator testID="consent-help-loading" color={colors.primary} />}
        </ScrollView>
        <Pressable testID="consent-help-back" accessibilityRole="button" style={[styles.button, styles.back]} onPress={onClose}><Text style={styles.buttonText}>{copy.back}</Text></Pressable>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  title: { padding: 20, fontSize: 24, fontWeight: '700', color: colors.primary },
  content: { padding: 20, gap: 16 },
  body: { color: colors.onSurface, fontSize: 16, lineHeight: 26 },
  error: { color: colors.error, fontSize: 16, lineHeight: 24 },
  button: { padding: 16, minHeight: 48, alignItems: 'center', backgroundColor: colors.primary, borderRadius: 12 },
  buttonText: { color: colors.onBrandPrimary, fontSize: 16, fontWeight: '700' },
  back: { margin: 16 },
});