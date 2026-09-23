import { ActivityIndicator, Pressable, Text, View, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { ComplaintCard } from './ComplaintCard';
import { isDraftReady, useComplaints } from './complaints';
import { theme } from '../theme';

const colors = theme.colors;
export function ComplaintsList({ all = false }: { all?: boolean }) {
  const { items, loading, error, retry } = useComplaints();
  const router = useRouter();
  const scope = all ? 'complaints' : 'home';
  const active = items.find(item => !isDraftReady(item));
  const completed = items.find(isDraftReady);
  const preview = [active, completed].filter(item => item !== undefined);
  if (preview.length < 2) preview.push(...items.filter(item => !preview.includes(item)).slice(0, 2 - preview.length));
  return <View testID={`${scope}-complaints-list`} style={styles.list}>
    {loading ? <ActivityIndicator testID={`${scope}-complaints-loading`} color={colors.primary} />
      : error ? <View style={styles.empty}>
        <Text testID={`${scope}-complaints-error`} style={styles.body}>We couldn’t load your complaints. Please check your connection.</Text>
        <Pressable testID={`${scope}-complaints-retry`} accessibilityRole="button" onPress={retry} style={styles.button}><Text style={styles.buttonText}>Try again</Text></Pressable>
      </View> : items.length ? (all ? items : preview).map(item => <ComplaintCard key={item.session_id} item={item} scope={scope} />)
        : <View style={styles.empty}>
          <Text testID={`${scope}-complaints-empty-title`} style={styles.title}>Your first step towards help</Text>
          <Text testID={`${scope}-complaints-empty`} style={styles.body}>You haven’t started a complaint yet. We’ll guide you, one step at a time.</Text>
          <Pressable testID={`${scope}-first-complaint`} accessibilityRole="button" onPress={() => router.push('/fir-draft')} style={styles.button}><Text style={styles.buttonText}>Start a complaint</Text></Pressable>
        </View>}
  </View>;
}
const styles = StyleSheet.create({
  list: { gap: 12 },
  empty: { backgroundColor: colors.surface, borderRadius: 18, padding: 20, gap: 12, borderWidth: 1, borderColor: colors.divider },
  title: { fontSize: 17, fontWeight: '700', color: colors.primary },
  body: { fontSize: 14, lineHeight: 22, color: colors.onSurfaceSecondary },
  button: { minHeight: 44, padding: 12, alignItems: 'center', borderRadius: 10, backgroundColor: colors.primary },
  buttonText: { color: colors.onBrandPrimary, fontWeight: '700' },
});