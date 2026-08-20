import { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Linking, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { theme } from '@/src/theme';

/**
 * Golden-hour cyber fraud checklist.
 *
 * Everything here is free and works offline — a fraud victim has minutes, not
 * money, and the steps/deadlines are fixed facts from the verified corpus
 * (MHA reporting portal + helpline 1930, RBI 3-working-day zero-liability rule).
 * Progress and the start time are kept in AsyncStorage so the countdown
 * survives the app being closed mid-panic.
 */
const KEY = 'dhara_fraud_checklist_v1';

type Step = {
  id: string;
  title: string;
  detail: string;
  action?: { label: string; url: string; icon: 'call' | 'globe-outline' | 'business-outline' };
};

const STEPS: Step[] = [
  {
    id: 'call1930',
    title: 'Call 1930 now',
    detail:
      'The national cyber-crime helpline puts your transaction on the shared banking platform so the receiving account can be put on hold. Every minute matters.',
    action: { label: 'Call 1930', url: 'tel:1930', icon: 'call' },
  },
  {
    id: 'portal',
    title: 'File on cybercrime.gov.in',
    detail:
      'Register the complaint on the National Cyber Crime Reporting Portal with the transaction reference, amount, date and the number that contacted you. Save the acknowledgement number.',
    action: { label: 'Open the portal', url: 'https://cybercrime.gov.in/', icon: 'globe-outline' },
  },
  {
    id: 'bank',
    title: 'Tell your bank IN WRITING within 3 working days',
    detail:
      'Report the unauthorised transaction to the bank in writing (email + branch acknowledgement). Reported within three working days, your liability is ZERO and the bank must credit the amount within ten working days.',
    action: { label: 'Bank helpline', url: 'tel:1800', icon: 'business-outline' },
  },
  {
    id: 'block',
    title: 'Block the card, UPI and net banking',
    detail:
      'Freeze the debit/credit card, disable UPI on the affected handle and change your net-banking password. Do not reinstall any app the caller asked you to install.',
  },
  {
    id: 'evidence',
    title: 'Save the evidence',
    detail:
      'Screenshot the SMS/UPI alert, the caller number, the WhatsApp or Telegram chat, the payment reference (UTR) and the bank statement line. Do not delete anything.',
  },
  {
    id: 'ack',
    title: 'Keep the acknowledgement safe',
    detail:
      'Note the portal acknowledgement number, the 1930 complaint number and the bank complaint number in one place — you need them for every follow-up.',
  },
  {
    id: 'followup',
    title: 'Follow up on the 10th working day',
    detail:
      'If the bank has not credited the amount within ten working days of your report, escalate in writing to the bank nodal officer and then to the RBI Ombudsman.',
  },
];

export default function FraudChecklist() {
  const router = useRouter();
  const [done, setDone] = useState<Record<string, boolean>>({});
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(KEY);
        if (raw) {
          const parsed = JSON.parse(raw);
          setDone(parsed.done || {});
          setStartedAt(parsed.startedAt || null);
        }
      } catch {}
    })();
  }, []);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const persist = useCallback(async (nextDone: Record<string, boolean>, started: number | null) => {
    try {
      await AsyncStorage.setItem(KEY, JSON.stringify({ done: nextDone, startedAt: started }));
    } catch {}
  }, []);

  const toggle = (id: string) => {
    const started = startedAt ?? Date.now();
    const next = { ...done, [id]: !done[id] };
    setStartedAt(started);
    setDone(next);
    persist(next, started);
  };

  const reset = () => {
    setDone({});
    setStartedAt(null);
    persist({}, null);
  };

  const open = async (url: string) => {
    try {
      await Linking.openURL(url);
    } catch {
      Alert.alert('Could not open', url);
    }
  };

  const completed = STEPS.filter((s) => done[s.id]).length;
  const elapsed = startedAt ? Math.floor((now - startedAt) / 1000) : 0;
  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const ss = String(elapsed % 60).padStart(2, '0');

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="fraud-checklist-screen">
      <View style={styles.header}>
        <Pressable testID="fraud-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={theme.colors.onBrandPrimary} />
        </Pressable>
        <Text style={styles.h1}>Fraud golden hour</Text>
        <View style={{ width: 26 }} />
      </View>

      <View style={styles.timerBar} testID="fraud-timer">
        <View>
          <Text style={styles.timerLabel}>{startedAt ? 'Time since you started' : 'Tick the first step to start'}</Text>
          <Text style={styles.timer}>{startedAt ? `${mm}:${ss}` : '--:--'}</Text>
        </View>
        <View style={styles.progressPill}>
          <Text style={styles.progressText}>{completed} / {STEPS.length} done</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.intro}>
          Money is recoverable only if you move fast. Work down this list in order — the first two
          steps get the fraudster&apos;s account frozen, the third protects your liability.
        </Text>

        {STEPS.map((s, i) => {
          const isDone = !!done[s.id];
          return (
            <View key={s.id} style={[styles.card, isDone && styles.cardDone]}>
              <Pressable
                testID={`fraud-step-${s.id}`}
                style={styles.cardTop}
                onPress={() => toggle(s.id)}
                hitSlop={6}
              >
                <Ionicons
                  name={isDone ? 'checkmark-circle' : 'ellipse-outline'}
                  size={26}
                  color={isDone ? theme.colors.success : theme.colors.brand}
                />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.stepTitle, isDone && styles.stepTitleDone]}>
                    {i + 1}. {s.title}
                  </Text>
                  <Text style={styles.stepDetail}>{s.detail}</Text>
                </View>
              </Pressable>
              {!!s.action && (
                <Pressable
                  testID={`fraud-action-${s.id}`}
                  style={styles.actionBtn}
                  onPress={() => open(s.action!.url)}
                >
                  <Ionicons name={s.action.icon} size={16} color={theme.colors.onBrandSecondary} />
                  <Text style={styles.actionText}>{s.action.label}</Text>
                </Pressable>
              )}
            </View>
          );
        })}

        <Pressable testID="fraud-reset" style={styles.reset} onPress={reset}>
          <Ionicons name="refresh" size={16} color={theme.colors.onSurfaceSecondary} />
          <Text style={styles.resetText}>Start a new checklist</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.surface },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: theme.spacing.lg, backgroundColor: theme.colors.brand,
  },
  h1: { fontFamily: theme.fonts.display, fontSize: 19, color: theme.colors.onBrandPrimary, fontWeight: '700' },
  timerBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: theme.spacing.lg, paddingVertical: theme.spacing.md,
    backgroundColor: theme.colors.goldSoft, borderBottomWidth: 1, borderBottomColor: theme.colors.gold,
  },
  timerLabel: { color: theme.colors.brand, fontSize: 12, fontWeight: '600' },
  timer: { color: theme.colors.brand, fontSize: 26, fontWeight: '800', fontVariant: ['tabular-nums'] },
  progressPill: {
    backgroundColor: theme.colors.brand, borderRadius: theme.radius.pill,
    paddingHorizontal: theme.spacing.md, paddingVertical: 6,
  },
  progressText: { color: theme.colors.onBrandPrimary, fontWeight: '700', fontSize: 12 },
  scroll: { padding: theme.spacing.lg, gap: theme.spacing.md, paddingBottom: theme.spacing.xxxl },
  intro: { color: theme.colors.onSurfaceSecondary, fontSize: 14, lineHeight: 21 },
  card: {
    backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.md,
    borderWidth: 1, borderColor: theme.colors.border, padding: theme.spacing.lg, gap: theme.spacing.md,
  },
  cardDone: { borderColor: theme.colors.success, backgroundColor: '#F0F7F3' },
  cardTop: { flexDirection: 'row', gap: theme.spacing.md, alignItems: 'flex-start', minHeight: 48 },
  stepTitle: { color: theme.colors.brand, fontWeight: '800', fontSize: 15 },
  stepTitleDone: { textDecorationLine: 'line-through', color: theme.colors.success },
  stepDetail: { color: theme.colors.onSurfaceSecondary, fontSize: 13, lineHeight: 19, marginTop: 4 },
  actionBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: theme.colors.brandSecondary, borderRadius: theme.radius.md, minHeight: 46,
  },
  actionText: { color: theme.colors.onBrandSecondary, fontWeight: '800', fontSize: 14 },
  reset: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    minHeight: 48, marginTop: theme.spacing.md,
  },
  resetText: { color: theme.colors.onSurfaceSecondary, fontWeight: '600', fontSize: 13 },
});
