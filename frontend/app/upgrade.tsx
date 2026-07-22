import { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator, Alert, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';

type Pricing = {
  pro_price_inr_paise: number;
  pro_price_label: string;
  billing_type: string;
  features: string[];
};

export default function Upgrade() {
  const { token, user, refreshUser } = useAuth();
  const router = useRouter();
  const params = useLocalSearchParams<{ status?: string; session_id?: string }>();
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkingReturn, setCheckingReturn] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/billing/pricing`).then(r => r.json()).then(setPricing).catch(() => {});
  }, []);

  useEffect(() => {
    // On return from checkout (web) verify with backend
    if (params.status === 'success' && params.session_id && token) {
      setCheckingReturn(true);
      fetch(`${API_BASE}/api/billing/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ session_id: params.session_id }),
      }).then(r => r.json()).then(async (d) => {
        if (d.is_pro) { await refreshUser(); }
      }).finally(() => setCheckingReturn(false));
    }
  }, [params.status, params.session_id, token, refreshUser]);

  const upgrade = useCallback(async () => {
    if (!token) return;
    setErrorMsg(null);
    setLoading(true);
    try {
      const returnUrl = Linking.createURL('/upgrade');
      const r = await fetch(`${API_BASE}/api/billing/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ return_url: returnUrl }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `Checkout failed (HTTP ${r.status})`);
      if (data.already_pro) { await refreshUser(); setErrorMsg('You already have Pro access.'); return; }
      if (!data.url) throw new Error('Failed to create checkout session');

      const result = await WebBrowser.openAuthSessionAsync(data.url, returnUrl);
      if (result.type === 'success' && result.url && data.session_id) {
        const v = await fetch(`${API_BASE}/api/billing/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ session_id: data.session_id }),
        }).then(x => x.json());
        if (v.is_pro) { await refreshUser(); Alert.alert('Welcome to Pro', 'Your account is now Pro.'); }
      }
    } catch (e: any) {
      const msg = e?.message || 'Please try again';
      setErrorMsg(msg);
      if (Platform.OS !== 'web') Alert.alert('Upgrade failed', msg);
    } finally {
      setLoading(false);
    }
  }, [token, refreshUser]);

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="upgrade-screen">
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} testID="upgrade-back" hitSlop={10}>
          <Ionicons name="arrow-back" size={26} color={theme.colors.onBrandPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>Dhara Pro</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.hero}>
          <View style={styles.crown}><Ionicons name="star" size={32} color={theme.colors.brandSecondary} /></View>
          <Text style={styles.heroTitle}>Lawyer-consultation depth</Text>
          <Text style={styles.heroSub}>Structured, actionable, drafts included.</Text>
          {pricing && (
            <View style={styles.priceRow}>
              <Text testID="pro-price" style={styles.price}>{pricing.pro_price_label}</Text>
              <Text style={styles.priceMeta}>{pricing.billing_type === 'one_time' ? 'one-time' : 'per month'}</Text>
            </View>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.section}>What you get</Text>
          {(pricing?.features || []).map((f, i) => (
            <View key={i} style={styles.feature} testID={`feature-${i}`}>
              <Ionicons name="checkmark-circle" size={20} color={theme.colors.success} />
              <Text style={styles.featureText}>{f}</Text>
            </View>
          ))}
        </View>

        <View style={styles.card}>
          <Text style={styles.section}>Free vs Pro</Text>
          <CompareRow label="Exact BNS/Constitution citations" free pro />
          <CompareRow label="22 Indian languages + voice" free pro />
          <CompareRow label="Draft complaint / RTI / notice paragraphs" pro />
          <CompareRow label="Step-by-step action plans with jurisdiction" pro />
          <CompareRow label="Counter-arguments & escalation paths" pro />
          <CompareRow label="Priority Claude Sonnet 4.5 responses" pro />
        </View>

        <View style={styles.disclaimerBox}>
          <Ionicons name="information-circle" size={18} color={theme.colors.warning} />
          <Text style={styles.disclaimerText}>
            Pro provides more detailed AI answers. It is NOT legal advice and does NOT create an advocate-client relationship. For actual legal matters consult a Bar Council-registered advocate. © Callistus Moses · Msafe.
          </Text>
        </View>

        {user?.is_pro ? (
          <View style={styles.alreadyPro} testID="already-pro">
            <Ionicons name="star" size={22} color={theme.colors.brandSecondary} />
            <Text style={styles.alreadyProText}>You are already a Pro member</Text>
          </View>
        ) : (
          <>
            {errorMsg && (
              <View testID="upgrade-error" style={styles.errorBox}>
                <Ionicons name="alert-circle" size={18} color={theme.colors.error} />
                <Text style={styles.errorText}>{errorMsg}</Text>
              </View>
            )}
            <Pressable
              testID="upgrade-cta-button"
              style={[styles.cta, (loading || checkingReturn) && { opacity: 0.6 }]}
              disabled={loading || checkingReturn}
              onPress={upgrade}
            >
              {loading || checkingReturn ? (
                <ActivityIndicator color={theme.colors.onBrandPrimary} />
              ) : (
                <>
                  <Ionicons name="star" size={18} color={theme.colors.onBrandPrimary} />
                  <Text style={styles.ctaText}>Upgrade to Pro {pricing ? `— ${pricing.pro_price_label}` : ''}</Text>
                </>
              )}
            </Pressable>
          </>
        )}

        <Text style={styles.footer}>Powered by Stripe · Secured payments · Refunds at sole discretion of Msafe.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function CompareRow({ label, free, pro }: { label: string; free?: boolean; pro?: boolean }) {
  return (
    <View style={styles.compareRow}>
      <Text style={styles.compareLabel}>{label}</Text>
      <View style={{ flexDirection: 'row', gap: 24 }}>
        <Ionicons name={free ? 'checkmark-circle' : 'remove-circle-outline'} size={20} color={free ? theme.colors.success : theme.colors.borderStrong} />
        <Ionicons name={pro ? 'checkmark-circle' : 'remove-circle-outline'} size={20} color={pro ? theme.colors.brandSecondary : theme.colors.borderStrong} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.brand },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: theme.spacing.lg, backgroundColor: theme.colors.brand },
  headerTitle: { color: theme.colors.onBrandPrimary, fontFamily: theme.fonts.display, fontSize: 20, fontWeight: '700' },
  scroll: { padding: theme.spacing.lg, paddingBottom: theme.spacing.xxxl, backgroundColor: theme.colors.surface },
  hero: { alignItems: 'center', paddingVertical: theme.spacing.xl, backgroundColor: theme.colors.brand, marginHorizontal: -theme.spacing.lg, marginTop: -theme.spacing.lg, paddingHorizontal: theme.spacing.lg },
  crown: { width: 72, height: 72, borderRadius: 36, backgroundColor: theme.colors.surface, alignItems: 'center', justifyContent: 'center', marginBottom: theme.spacing.md },
  heroTitle: { color: theme.colors.onBrandPrimary, fontFamily: theme.fonts.display, fontSize: 24, fontWeight: '700' },
  heroSub: { color: theme.colors.brandSecondary, marginTop: 4 },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', marginTop: theme.spacing.md, gap: 8 },
  price: { color: theme.colors.onBrandPrimary, fontFamily: theme.fonts.display, fontSize: 40, fontWeight: '700' },
  priceMeta: { color: '#D1D5DB', fontSize: 13 },
  card: { backgroundColor: theme.colors.surface, borderRadius: theme.radius.lg, padding: theme.spacing.lg, marginTop: theme.spacing.lg, borderWidth: 1, borderColor: theme.colors.border },
  section: { fontFamily: theme.fonts.display, fontSize: 17, color: theme.colors.brand, marginBottom: theme.spacing.md, fontWeight: '700' },
  feature: { flexDirection: 'row', alignItems: 'flex-start', gap: theme.spacing.sm, marginBottom: theme.spacing.sm },
  featureText: { flex: 1, color: theme.colors.onSurface, lineHeight: 20 },
  compareRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: theme.spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: theme.colors.divider },
  compareLabel: { flex: 1, color: theme.colors.onSurface, fontSize: 13 },
  disclaimerBox: { flexDirection: 'row', gap: theme.spacing.sm, padding: theme.spacing.md, backgroundColor: '#FFF6E5', borderRadius: theme.radius.md, borderWidth: 1, borderColor: '#F0D68A', marginTop: theme.spacing.lg },
  disclaimerText: { flex: 1, color: '#7A4C00', fontSize: 12, lineHeight: 17 },
  cta: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: theme.colors.brandSecondary, borderRadius: theme.radius.md, padding: theme.spacing.lg, marginTop: theme.spacing.xl, minHeight: 56 },
  ctaText: { color: theme.colors.onBrandPrimary, fontWeight: '800', fontSize: 16 },
  alreadyPro: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: theme.spacing.sm, padding: theme.spacing.lg, backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.md, marginTop: theme.spacing.xl, borderWidth: 1, borderColor: theme.colors.brandSecondary },
  alreadyProText: { color: theme.colors.brand, fontWeight: '700' },
  footer: { textAlign: 'center', color: theme.colors.onSurfaceTertiary, marginTop: theme.spacing.lg, fontSize: 11 },
  errorBox: { flexDirection: 'row', gap: 8, alignItems: 'center', padding: theme.spacing.md, backgroundColor: '#FEE2E2', borderColor: theme.colors.error, borderWidth: 1, borderRadius: theme.radius.md, marginTop: theme.spacing.lg },
  errorText: { flex: 1, color: theme.colors.error, fontSize: 13, fontWeight: '600' },
});
