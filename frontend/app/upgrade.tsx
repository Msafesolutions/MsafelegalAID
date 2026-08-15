import { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  Platform,
  Modal,
  TextInput,
} from 'react-native';
// NOTE: must be the keyboard-controller KeyboardAvoidingView, not React Native's.
// This modal renders inside an RN <Modal>, and keyboard-controller forces
// SOFT_INPUT_ADJUST_NOTHING on every modal window it attaches to, so RN's
// KeyboardAvoidingView (which relies on the window resizing) can never work here.
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import * as Clipboard from 'expo-clipboard';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';

type Pricing = {
  pro_price_inr_paise: number;
  pro_price_label: string;
  pro_price_usd_cents: number;
  pro_price_usd_label: string;
  billing_type: string;
  features: string[];
  providers: {
    stripe: { enabled: boolean; currency: string; amount_label: string; regions: string[] };
    razorpay: {
      enabled: boolean;
      currency: string;
      amount_label: string;
      regions: string[];
      link_url: string;
      handle: string;
    };
  };
};

export default function Upgrade() {
  const { token, user, refreshUser } = useAuth();
  const router = useRouter();
  const params = useLocalSearchParams<{ status?: string; session_id?: string }>();
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [loadingStripe, setLoadingStripe] = useState(false);
  const [loadingRazor, setLoadingRazor] = useState(false);
  const [checkingReturn, setCheckingReturn] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [razorModal, setRazorModal] = useState(false);
  const [razorPaymentId, setRazorPaymentId] = useState('');
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/billing/pricing`)
      .then((r) => r.json())
      .then(setPricing)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (params.status === 'success' && params.session_id && token) {
      setCheckingReturn(true);
      fetch(`${API_BASE}/api/billing/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ session_id: params.session_id }),
      })
        .then((r) => r.json())
        .then(async (d) => {
          if (d.is_pro) await refreshUser();
        })
        .finally(() => setCheckingReturn(false));
    }
  }, [params.status, params.session_id, token, refreshUser]);

  const payStripe = useCallback(async () => {
    if (!token) return;
    setErrorMsg(null);
    setLoadingStripe(true);
    try {
      const returnUrl = Linking.createURL('/upgrade');
      const r = await fetch(`${API_BASE}/api/billing/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ return_url: returnUrl }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `Checkout failed (HTTP ${r.status})`);
      if (data.already_pro) {
        await refreshUser();
        setErrorMsg('You already have Pro access.');
        return;
      }
      if (!data.url) throw new Error('Failed to create checkout session');

      const result = await WebBrowser.openAuthSessionAsync(data.url, returnUrl);
      if (result.type === 'success' && result.url && data.session_id) {
        const v = await fetch(`${API_BASE}/api/billing/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ session_id: data.session_id }),
        }).then((x) => x.json());
        if (v.is_pro) {
          await refreshUser();
          Alert.alert('Welcome to Pro', 'Your account is now Pro.');
        }
      }
    } catch (e: any) {
      const msg = e?.message || 'Please try again';
      setErrorMsg(msg);
      if (Platform.OS !== 'web') Alert.alert('Stripe checkout failed', msg);
    } finally {
      setLoadingStripe(false);
    }
  }, [token, refreshUser]);

  const payRazorpay = useCallback(async () => {
    if (!pricing?.providers?.razorpay?.link_url) return;
    setErrorMsg(null);
    setLoadingRazor(true);
    try {
      await WebBrowser.openBrowserAsync(pricing.providers.razorpay.link_url, {
        dismissButtonStyle: 'done',
      });
      setRazorModal(true);
    } catch (e: any) {
      setErrorMsg(e?.message || 'Unable to open payment page');
    } finally {
      setLoadingRazor(false);
    }
  }, [pricing]);

  const submitRazorPaymentId = useCallback(async () => {
    if (!token) return;
    const pid = razorPaymentId.trim();
    if (!pid.startsWith('pay_')) {
      Alert.alert('Invalid Payment ID', 'The Payment ID from Razorpay must start with "pay_".');
      return;
    }
    setVerifying(true);
    try {
      const r = await fetch(`${API_BASE}/api/billing/razorpay/submit-payment-id`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ payment_id: pid }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Verification failed');
      if (data.is_pro) {
        await refreshUser();
        setRazorModal(false);
        setRazorPaymentId('');
        Alert.alert(
          'Welcome to Dhara Pro',
          data.trust_based
            ? 'Your Pro access has been activated. We will confirm your payment shortly.'
            : 'Payment verified. Your account is now Pro.'
        );
      }
    } catch (e: any) {
      Alert.alert('Could not verify', e?.message || 'Please double-check the Payment ID and try again.');
    } finally {
      setVerifying(false);
    }
  }, [token, razorPaymentId, refreshUser]);

  const pasteFromClipboard = useCallback(async () => {
    try {
      const txt = await Clipboard.getStringAsync();
      if (txt) setRazorPaymentId(txt.trim());
    } catch {}
  }, []);

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
          <View style={styles.crown}>
            <Ionicons name="star" size={32} color={theme.colors.brandSecondary} />
          </View>
          <Text style={styles.heroTitle}>Lawyer-consultation depth</Text>
          <Text style={styles.heroSub}>Structured, actionable, drafts included.</Text>
          {pricing && (
            <View style={styles.priceRow}>
              <Text testID="pro-price" style={styles.price}>
                {pricing.pro_price_label}
              </Text>
              <Text style={styles.priceMeta}>
                {pricing.billing_type === 'one_time' ? 'one-time' : 'per month'} · India
              </Text>
              <Text style={styles.priceAlt}>
                or {pricing.pro_price_usd_label} USD (Canada / International)
              </Text>
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
            Pro provides more detailed AI answers. It is NOT legal advice and does NOT create an
            advocate-client relationship. For actual legal matters consult a Bar Council-registered
            advocate. © Callistus Moses · Msafe.
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

            {/* Razorpay — India */}
            {pricing?.providers?.razorpay?.enabled && (
              <Pressable
                testID="upgrade-razorpay-button"
                style={[styles.cta, styles.ctaRazor, (loadingRazor || checkingReturn) && { opacity: 0.6 }]}
                disabled={loadingRazor || checkingReturn}
                onPress={payRazorpay}
              >
                {loadingRazor ? (
                  <ActivityIndicator color={theme.colors.onBrandPrimary} />
                ) : (
                  <>
                    <Ionicons name="flash" size={18} color={theme.colors.onBrandPrimary} />
                    <View style={{ alignItems: 'flex-start' }}>
                      <Text style={styles.ctaText}>
                        Pay {pricing.providers.razorpay.amount_label} via Razorpay
                      </Text>
                      <Text style={styles.ctaSub}>UPI · Cards · NetBanking · India</Text>
                    </View>
                  </>
                )}
              </Pressable>
            )}

            {/* Already paid Razorpay? */}
            {pricing?.providers?.razorpay?.enabled && (
              <Pressable
                testID="already-paid-razorpay"
                onPress={() => setRazorModal(true)}
                style={styles.alreadyPaidLink}
              >
                <Text style={styles.alreadyPaidText}>
                  Already paid on Razorpay? Enter Payment ID →
                </Text>
              </Pressable>
            )}

            {/* Stripe — International */}
            {pricing?.providers?.stripe?.enabled && (
              <Pressable
                testID="upgrade-stripe-button"
                style={[styles.cta, styles.ctaStripe, (loadingStripe || checkingReturn) && { opacity: 0.6 }]}
                disabled={loadingStripe || checkingReturn}
                onPress={payStripe}
              >
                {loadingStripe || checkingReturn ? (
                  <ActivityIndicator color={theme.colors.onBrandPrimary} />
                ) : (
                  <>
                    <Ionicons name="card" size={18} color={theme.colors.onBrandPrimary} />
                    <View style={{ alignItems: 'flex-start' }}>
                      <Text style={styles.ctaText}>
                        Pay {pricing.providers.stripe.amount_label} USD via Stripe
                      </Text>
                      <Text style={styles.ctaSub}>Cards · Canada · International</Text>
                    </View>
                  </>
                )}
              </Pressable>
            )}
          </>
        )}

        <Text style={styles.footer}>
          Powered by Razorpay (India) & Stripe (Intl) · Secured payments · Refunds at sole discretion of
          Msafe.
        </Text>
      </ScrollView>

      {/* Razorpay Payment ID Modal */}
      <Modal
        visible={razorModal}
        transparent
        animationType="slide"
        onRequestClose={() => setRazorModal(false)}
      >
        <KeyboardAvoidingView behavior="padding" style={styles.modalOverlay}>
          <View style={styles.modalCard} testID="razorpay-verify-modal">
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Confirm your Razorpay payment</Text>
              <Pressable onPress={() => setRazorModal(false)} hitSlop={10}>
                <Ionicons name="close" size={24} color={theme.colors.onSurface} />
              </Pressable>
            </View>
            <Text style={styles.modalBody}>
              After paying on the Razorpay page, you will receive a Payment ID (starts with{' '}
              <Text style={styles.mono}>pay_</Text>) via SMS or email. Paste it below to activate Pro.
            </Text>
            <View style={styles.inputRow}>
              <TextInput
                testID="razorpay-payment-id-input"
                value={razorPaymentId}
                onChangeText={setRazorPaymentId}
                placeholder="pay_xxxxxxxxxxxxxx"
                placeholderTextColor={theme.colors.onSurfaceTertiary}
                autoCapitalize="none"
                autoCorrect={false}
                style={styles.input}
              />
              <Pressable onPress={pasteFromClipboard} style={styles.pasteBtn} testID="paste-btn">
                <Ionicons name="clipboard-outline" size={18} color={theme.colors.brand} />
                <Text style={styles.pasteBtnText}>Paste</Text>
              </Pressable>
            </View>
            <Pressable
              testID="verify-razorpay-btn"
              style={[styles.cta, styles.ctaRazor, (verifying || !razorPaymentId.trim()) && { opacity: 0.6 }]}
              disabled={verifying || !razorPaymentId.trim()}
              onPress={submitRazorPaymentId}
            >
              {verifying ? (
                <ActivityIndicator color={theme.colors.onBrandPrimary} />
              ) : (
                <>
                  <Ionicons name="shield-checkmark" size={18} color={theme.colors.onBrandPrimary} />
                  <Text style={styles.ctaText}>Activate Pro</Text>
                </>
              )}
            </Pressable>
            <Pressable
              onPress={async () => {
                if (pricing?.providers?.razorpay?.link_url) {
                  await WebBrowser.openBrowserAsync(pricing.providers.razorpay.link_url);
                }
              }}
              style={{ marginTop: 12 }}
            >
              <Text style={styles.reopenLink}>Reopen Razorpay page →</Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

function CompareRow({ label, free, pro }: { label: string; free?: boolean; pro?: boolean }) {
  return (
    <View style={styles.compareRow}>
      <Text style={styles.compareLabel}>{label}</Text>
      <View style={{ flexDirection: 'row', gap: 24 }}>
        <Ionicons
          name={free ? 'checkmark-circle' : 'remove-circle-outline'}
          size={20}
          color={free ? theme.colors.success : theme.colors.borderStrong}
        />
        <Ionicons
          name={pro ? 'checkmark-circle' : 'remove-circle-outline'}
          size={20}
          color={pro ? theme.colors.brandSecondary : theme.colors.borderStrong}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.brand },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.brand,
  },
  headerTitle: {
    color: theme.colors.onBrandPrimary,
    fontFamily: theme.fonts.display,
    fontSize: 20,
    fontWeight: '700',
  },
  scroll: {
    padding: theme.spacing.lg,
    paddingBottom: theme.spacing.xxxl,
    backgroundColor: theme.colors.surface,
  },
  hero: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
    backgroundColor: theme.colors.brand,
    marginHorizontal: -theme.spacing.lg,
    marginTop: -theme.spacing.lg,
    paddingHorizontal: theme.spacing.lg,
  },
  crown: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
  },
  heroTitle: {
    color: theme.colors.onBrandPrimary,
    fontFamily: theme.fonts.display,
    fontSize: 24,
    fontWeight: '700',
  },
  heroSub: { color: theme.colors.brandSecondary, marginTop: 4 },
  priceRow: { alignItems: 'center', marginTop: theme.spacing.md },
  price: {
    color: theme.colors.onBrandPrimary,
    fontFamily: theme.fonts.display,
    fontSize: 40,
    fontWeight: '700',
  },
  priceMeta: { color: '#D1D5DB', fontSize: 13, marginTop: 2 },
  priceAlt: { color: theme.colors.brandSecondary, fontSize: 12, marginTop: 6 },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.lg,
    marginTop: theme.spacing.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  section: {
    fontFamily: theme.fonts.display,
    fontSize: 17,
    color: theme.colors.brand,
    marginBottom: theme.spacing.md,
    fontWeight: '700',
  },
  feature: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.sm,
  },
  featureText: { flex: 1, color: theme.colors.onSurface, lineHeight: 20 },
  compareRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.colors.divider,
  },
  compareLabel: { flex: 1, color: theme.colors.onSurface, fontSize: 13 },
  disclaimerBox: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    padding: theme.spacing.md,
    backgroundColor: '#FFF6E5',
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: '#F0D68A',
    marginTop: theme.spacing.lg,
  },
  disclaimerText: { flex: 1, color: '#7A4C00', fontSize: 12, lineHeight: 17 },
  cta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderRadius: theme.radius.md,
    padding: theme.spacing.lg,
    marginTop: theme.spacing.lg,
    minHeight: 62,
  },
  ctaRazor: { backgroundColor: theme.colors.brandSecondary },
  ctaStripe: { backgroundColor: '#635BFF' },
  ctaText: { color: theme.colors.onBrandPrimary, fontWeight: '800', fontSize: 15 },
  ctaSub: { color: theme.colors.onBrandPrimary, fontSize: 11, opacity: 0.85, marginTop: 2 },
  alreadyPaidLink: { alignItems: 'center', marginTop: 8 },
  alreadyPaidText: { color: theme.colors.brand, fontSize: 13, fontWeight: '600', textDecorationLine: 'underline' },
  alreadyPro: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.sm,
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.surfaceSecondary,
    borderRadius: theme.radius.md,
    marginTop: theme.spacing.xl,
    borderWidth: 1,
    borderColor: theme.colors.brandSecondary,
  },
  alreadyProText: { color: theme.colors.brand, fontWeight: '700' },
  footer: {
    textAlign: 'center',
    color: theme.colors.onSurfaceTertiary,
    marginTop: theme.spacing.lg,
    fontSize: 11,
  },
  errorBox: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
    padding: theme.spacing.md,
    backgroundColor: '#FEE2E2',
    borderColor: theme.colors.error,
    borderWidth: 1,
    borderRadius: theme.radius.md,
    marginTop: theme.spacing.lg,
  },
  errorText: { flex: 1, color: theme.colors.error, fontSize: 13, fontWeight: '600' },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: theme.colors.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: theme.spacing.lg,
    paddingBottom: theme.spacing.xl,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  modalTitle: { fontSize: 18, fontWeight: '800', color: theme.colors.brand, fontFamily: theme.fonts.display },
  modalBody: { color: theme.colors.onSurface, fontSize: 13, lineHeight: 19, marginBottom: theme.spacing.md },
  mono: { fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' }), fontWeight: '700' },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    fontSize: 14,
    color: theme.colors.onSurface,
    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' }),
    backgroundColor: theme.colors.surfaceSecondary,
  },
  pasteBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.md,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  pasteBtnText: { color: theme.colors.brand, fontWeight: '700', fontSize: 13 },
  reopenLink: { textAlign: 'center', color: theme.colors.brand, textDecorationLine: 'underline', fontSize: 13 },
});
