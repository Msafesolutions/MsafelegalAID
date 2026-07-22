import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';

type Topic = { id: string; icon: string; title: string; summary: string; law: string; points: string[] };

const ICON_MAP: Record<string, keyof typeof Ionicons.glyphMap> = {
  shield: 'shield-checkmark',
  handcuffs: 'lock-closed',
  'file-text': 'document-text',
  heart: 'heart',
  car: 'car',
  info: 'information-circle',
  'shopping-bag': 'bag-handle',
  home: 'home',
};

export default function Rights() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetch(`${API_BASE}/api/reference/topics`)
      .then(r => r.json())
      .then(setTopics)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="rights-screen">
      <View style={styles.header}>
        <Text style={styles.h1}>Know Your Rights</Text>
        <Text style={styles.h2}>Rights that no one can take from you.</Text>
      </View>
      <ScrollView contentContainerStyle={styles.scroll}>
        {loading && <ActivityIndicator color={theme.colors.brand} />}
        {topics.map(t => {
          const open = expanded === t.id;
          return (
            <Pressable
              key={t.id}
              testID={`topic-${t.id}`}
              onPress={() => setExpanded(open ? null : t.id)}
              style={styles.card}
            >
              <View style={styles.cardHead}>
                <View style={styles.iconWrap}>
                  <Ionicons name={ICON_MAP[t.icon] || 'library'} size={24} color={theme.colors.brand} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardTitle}>{t.title}</Text>
                  <Text style={styles.cardSummary}>{t.summary}</Text>
                </View>
                <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={20} color={theme.colors.onSurfaceSecondary} />
              </View>
              {open && (
                <View style={styles.body}>
                  <View style={styles.lawPill}>
                    <Ionicons name="book" size={14} color={theme.colors.brandSecondary} />
                    <Text style={styles.lawText}>{t.law}</Text>
                  </View>
                  {t.points.map((p, i) => (
                    <View key={i} style={styles.point}>
                      <Text style={styles.bullet}>•</Text>
                      <Text style={styles.pointText}>{p}</Text>
                    </View>
                  ))}
                  <Pressable
                    testID={`ask-more-${t.id}`}
                    style={styles.askBtn}
                    onPress={() => router.push('/(tabs)')}
                  >
                    <Ionicons name="chatbubbles" size={16} color={theme.colors.onBrandPrimary} />
                    <Text style={styles.askText}>Ask Gandhikar more</Text>
                  </Pressable>
                </View>
              )}
            </Pressable>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.surface },
  header: { padding: theme.spacing.xl, paddingBottom: theme.spacing.md, borderBottomWidth: 1, borderBottomColor: theme.colors.divider },
  h1: { fontFamily: theme.fonts.display, fontSize: 28, color: theme.colors.brand, fontWeight: '700' },
  h2: { color: theme.colors.onSurfaceSecondary, marginTop: 4 },
  scroll: { padding: theme.spacing.lg, gap: theme.spacing.md, paddingBottom: theme.spacing.xxl },
  card: { backgroundColor: theme.colors.surface, borderRadius: theme.radius.lg, borderWidth: 1, borderColor: theme.colors.border, padding: theme.spacing.lg, marginBottom: theme.spacing.md },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  iconWrap: { width: 44, height: 44, borderRadius: 22, backgroundColor: theme.colors.surfaceSecondary, alignItems: 'center', justifyContent: 'center' },
  cardTitle: { fontFamily: theme.fonts.display, fontSize: 17, fontWeight: '700', color: theme.colors.onSurface },
  cardSummary: { color: theme.colors.onSurfaceSecondary, marginTop: 2, fontSize: 13 },
  body: { marginTop: theme.spacing.lg, paddingTop: theme.spacing.lg, borderTopWidth: 1, borderTopColor: theme.colors.divider },
  lawPill: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', backgroundColor: theme.colors.surfaceSecondary, paddingHorizontal: theme.spacing.md, paddingVertical: theme.spacing.sm, borderRadius: theme.radius.pill, marginBottom: theme.spacing.md },
  lawText: { color: theme.colors.brandSecondary, fontSize: 12, fontWeight: '600' },
  point: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.sm },
  bullet: { color: theme.colors.brandSecondary, fontSize: 18, lineHeight: 22 },
  pointText: { flex: 1, color: theme.colors.onSurface, lineHeight: 22, fontSize: 14 },
  askBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: theme.colors.brand, borderRadius: theme.radius.md, padding: theme.spacing.md, marginTop: theme.spacing.md },
  askText: { color: theme.colors.onBrandPrimary, fontWeight: '700' },
});
