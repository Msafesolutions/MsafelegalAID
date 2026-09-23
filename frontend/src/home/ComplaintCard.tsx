import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { theme } from '../theme';
import { Complaint, complaintTitle, complaintProgress, isDraftReady } from './complaints';

const colors = theme.colors;
export function ComplaintCard({ item, scope = 'home' }: { item: Complaint; scope?: string }) {
  const router = useRouter();
  const ready = isDraftReady(item);
  const progress = complaintProgress(item);
  const date = item.updated_at ? new Date(item.updated_at) : null;
  const dateLabel = date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : null;
  const open = () => router.push(ready
    ? { pathname: '/fir-draft/result', params: { sessionId: item.session_id } }
    : { pathname: '/fir-draft', params: { resumeId: item.session_id } });
  return (
    <View testID={`${scope}-complaint-${item.session_id}`} style={styles.card}>
      <View style={styles.heading}>
        <View style={[styles.icon, ready && styles.readyIcon]}><Ionicons name={ready ? 'document-text-outline' : 'folder-open-outline'} size={23} color={ready ? colors.success : colors.brandSecondary} /></View>
        <View style={styles.titleWrap}>
          <Text testID={`${scope}-complaint-title-${item.session_id}`} style={styles.title}>{complaintTitle(item)}</Text>
          <Text testID={`${scope}-complaint-stage-${item.session_id}`} style={styles.subtitle}>{progress.label}</Text>
        </View>
        <View style={[styles.badge, ready && styles.readyBadge]}>
          <Text testID={`${scope}-complaint-status-${item.session_id}`} style={[styles.badgeText, ready && styles.readyText]}>{ready ? 'Draft ready' : item.status === 'paused' ? 'Paused' : 'In progress'}</Text>
        </View>
      </View>
      {!ready && <View style={styles.progressWrap}>
        <Text testID={`${scope}-complaint-progress-label-${item.session_id}`} style={styles.step}>Interview · Step {progress.step} of {progress.total}</Text>
        <View testID={`${scope}-complaint-progress-${item.session_id}`} accessibilityRole="progressbar" accessibilityValue={{ min: 1, max: progress.total, now: progress.step }} style={styles.track}>
          <View style={[styles.fill, { width: `${progress.step / progress.total * 100}%` }]} />
        </View>
      </View>}
      <View style={styles.footer}>
        <Text testID={`${scope}-complaint-date-${item.session_id}`} style={styles.date}>{dateLabel ? `${ready ? 'Completed' : 'Updated'}: ${dateLabel}` : 'Saved complaint'}</Text>
        <Pressable testID={`${scope}-complaint-open-${item.session_id}`} accessibilityRole="button" onPress={open} style={({ pressed }) => [styles.button, ready && styles.secondaryButton, pressed && styles.pressed]}>
          <Text style={[styles.buttonText, ready && styles.secondaryText]}>{ready ? 'View draft' : 'Continue'}</Text>
          <Ionicons name={ready ? 'document-outline' : 'arrow-forward'} size={15} color={ready ? colors.primary : colors.onBrandPrimary} />
        </Pressable>
      </View>
    </View>
  );
}
const styles = StyleSheet.create({
  card: { padding: 12, backgroundColor: colors.surface, borderRadius: 18, borderWidth: 1, borderColor: colors.divider, gap: 8 },
  heading: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, flexWrap: 'wrap' },
  icon: { width: 38, height: 42, borderRadius: 10, backgroundColor: colors.goldMuted, alignItems: 'center', justifyContent: 'center' },
  readyIcon: { backgroundColor: colors.successSoft },
  titleWrap: { flex: 1, minWidth: 90 },
  title: { color: colors.onSurface, fontSize: 15, fontWeight: '700', lineHeight: 21 },
  subtitle: { color: colors.onSurfaceTertiary, fontSize: 12, lineHeight: 18, marginTop: 3 },
  badge: { backgroundColor: colors.goldMuted, borderRadius: 20, paddingHorizontal: 9, paddingVertical: 6, borderWidth: 1, borderColor: colors.goldSoft },
  badgeText: { fontSize: 10, fontWeight: '600', color: colors.brandSecondary },
  readyBadge: { backgroundColor: colors.successSoft, borderColor: colors.successSoft },
  readyText: { color: colors.success },
  progressWrap: { paddingLeft: 48, gap: 6 },
  step: { fontSize: 11, lineHeight: 16, color: colors.onSurfaceTertiary },
  track: { height: 5, borderRadius: 8, backgroundColor: colors.surfaceSecondary, overflow: 'hidden' },
  fill: { height: '100%', backgroundColor: colors.gold, borderRadius: 8 },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' },
  date: { fontSize: 11, lineHeight: 17, color: colors.onSurfaceTertiary, flexShrink: 1 },
  button: { minHeight: 44, paddingHorizontal: 12, borderRadius: 9, flexDirection: 'row', gap: 7, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary },
  buttonText: { fontSize: 12, fontWeight: '700', color: colors.onBrandPrimary },
  secondaryButton: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.divider },
  secondaryText: { color: colors.primary },
  pressed: { opacity: 0.7 },
});