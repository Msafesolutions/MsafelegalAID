import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import { theme } from '@/src/theme';
import { DRAFTS } from '@/src/drafts';

export default function DraftsList() {
  const router = useRouter();
  const { user } = useAuth();
  const isPro = !!user?.is_pro;
  const remaining = user?.drafts_remaining ?? 1;

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="drafts-screen">
      <View style={styles.header}>
        <Pressable testID="drafts-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={theme.colors.onBrandPrimary} />
        </Pressable>
        <Text style={styles.h1}>Ready notices</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.intro}>
          Fill a short form and Dhara writes the full legal notice for you — with the correct
          deadlines. Copy it, send it by registered post, and keep the receipt.
        </Text>

        <View style={styles.quotaCard} testID="drafts-quota">
          <Ionicons name={isPro ? 'star' : 'information-circle-outline'} size={18} color={theme.colors.brand} />
          <Text style={styles.quotaText}>
            {isPro
              ? 'Dhara Pro · unlimited notices'
              : remaining > 0
                ? `${remaining} free notice left · unlimited with Pro`
                : 'Free notice used · upgrade to Pro for unlimited notices'}
          </Text>
        </View>

        {DRAFTS.map((d) => (
          <Pressable
            key={d.type}
            testID={`draft-${d.type}`}
            style={styles.card}
            onPress={() => router.push(`/drafts/${d.type}`)}
          >
            <View style={styles.iconWrap}>
              <Ionicons name={d.icon} size={22} color={theme.colors.brand} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.cardTitle}>{d.title}</Text>
              <Text style={styles.cardSub}>{d.subtitle}</Text>
              <View style={styles.deadline}>
                <Ionicons name="time-outline" size={14} color={theme.colors.error} />
                <Text style={styles.deadlineText}>{d.deadline}</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={20} color={theme.colors.onSurfaceTertiary} />
          </Pressable>
        ))}
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
  h1: { fontFamily: theme.fonts.display, fontSize: 20, color: theme.colors.onBrandPrimary, fontWeight: '700' },
  scroll: { padding: theme.spacing.lg, gap: theme.spacing.md, paddingBottom: theme.spacing.xxxl },
  intro: { color: theme.colors.onSurfaceSecondary, fontSize: 14, lineHeight: 21 },
  quotaCard: {
    flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm,
    backgroundColor: theme.colors.goldSoft, borderRadius: theme.radius.md,
    borderWidth: 1, borderColor: theme.colors.gold, padding: theme.spacing.md,
  },
  quotaText: { flex: 1, color: theme.colors.brand, fontWeight: '700', fontSize: 13 },
  card: {
    flexDirection: 'row', alignItems: 'flex-start', gap: theme.spacing.md,
    backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.md,
    borderWidth: 1, borderColor: theme.colors.border, padding: theme.spacing.lg,
  },
  iconWrap: {
    width: 40, height: 40, borderRadius: 20, backgroundColor: theme.colors.surface,
    alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: theme.colors.border,
  },
  cardTitle: { color: theme.colors.brand, fontWeight: '800', fontSize: 15 },
  cardSub: { color: theme.colors.onSurfaceSecondary, fontSize: 13, marginTop: 2, lineHeight: 18 },
  deadline: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: theme.spacing.sm },
  deadlineText: { flex: 1, color: theme.colors.error, fontSize: 12, lineHeight: 17, fontWeight: '600' },
});
