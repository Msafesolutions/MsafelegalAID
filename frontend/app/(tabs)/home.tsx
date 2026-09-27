import { useCallback, useEffect, useRef, useState } from 'react';
import { Animated, Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { setStatusBarStyle } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/auth';
import { theme } from '@/src/theme';
import { trackEvent } from '@/src/analytics';
import { ComplaintsList } from '@/src/home/ComplaintsList';
import { DisclaimerBanner } from '@/src/components/DisclaimerBanner';
import { MarqueeBanner } from '@/src/components/MarqueeBanner';
import { ConsentPublicHelp } from '@/src/components/ConsentPublicHelp';
import { consentCopy } from '@/src/consentCopy';

const colors = theme.colors;
export default function Home() {
  const { user, language } = useAuth();
  const router = useRouter();
  const [emergency, setEmergency] = useState(false);
  const [question, setQuestion] = useState('');
  const openChat = (voice = false) => {
    router.push({ pathname: '/(tabs)', params: { draft: question, entry: String(Date.now()), voiceHint: voice ? '1' : '' } });
    setQuestion('');
  };
  const entrance = useRef(new Animated.Value(0)).current;
  useEffect(() => { Animated.timing(entrance, { toValue: 1, duration: 280, useNativeDriver: true }).start(); }, [entrance]);
  useFocusEffect(useCallback(() => { setStatusBarStyle('light'); return () => setStatusBarStyle('dark'); }, []));
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const firstName = user?.name?.trim().split(/\s+/)[0] || 'there';
  const help = [
    { id: 'rights', label: 'Know Your\nRights', icon: 'shield-checkmark-outline' as const, action: () => { trackEvent('quick_help_tap', { card_type: 'rights', language: language.code }); router.push('/(tabs)/rights'); } },
    { id: 'advocate', label: 'Find an\nAdvocate', icon: 'call-outline' as const, action: () => { trackEvent('quick_help_tap', { card_type: 'advocate', language: language.code }); router.push('/(tabs)/advocate'); } },
    { id: 'emergency', label: 'Emergency\nHelplines', icon: 'shield-outline' as const, action: () => { trackEvent('quick_help_tap', { card_type: 'emergency', language: language.code }); setEmergency(true); } },
  ];
  return <SafeAreaView style={styles.safe} edges={['top']} testID="home-screen">
    <View testID="home-header" style={styles.header}>
      <Image source={require('../../assets/images/dhara_icon.png')} style={styles.logo} resizeMode="contain" />
      <View testID="home-brand-wrap" style={styles.brandWrap}><Text testID="home-brand" style={styles.brand} numberOfLines={1} adjustsFontSizeToFit>Dhara</Text><Text testID="home-tagline" style={styles.tagline}>YOUR LEGAL RIGHTS</Text></View>
      <Pressable testID="home-pro-chip" accessibilityRole="button" accessibilityLabel={user?.is_pro ? 'Manage Dhara Pro' : 'View Dhara Pro'} style={styles.proChip} onPress={() => router.push('/upgrade')}><View style={styles.proChipBadge}><Ionicons name="star" size={12} color={colors.onGold} /><Text testID="home-pro-label" style={styles.proChipText}>Pro</Text></View></Pressable>
      <Pressable testID="home-language" accessibilityRole="button" accessibilityLabel="Change language" style={styles.language} onPress={() => router.push({ pathname: '/language', params: { from: 'home' } })}>
        <Ionicons name="globe-outline" size={15} color={colors.onBrandPrimary} /><Text testID="home-language-label" style={styles.languageText} numberOfLines={1}>{language.code.toUpperCase()}</Text>
      </Pressable>
      <Pressable testID="home-profile" accessibilityRole="button" accessibilityLabel="Your profile" style={styles.profile} onPress={() => router.push('/(tabs)/settings')}><Ionicons name="person-outline" size={20} color={colors.onBrandPrimary} /></Pressable>
    </View>
    <MarqueeBanner variant="dark" />
    <KeyboardAvoidingView style={styles.scroll} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <ScrollView testID="home-scroll" style={styles.scroll} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Animated.View testID="home-content" style={{ opacity: entrance, transform: [{ translateY: entrance.interpolate({ inputRange: [0, 1], outputRange: [8, 0] }) }] }}>
        <View testID="home-greeting-panel" style={styles.greeting}><Text testID="home-greeting" style={styles.greetingText}>{greeting}, {firstName}</Text></View>
        <Text testID="home-quick-help-heading" style={styles.sectionTitle}>QUICK HELP</Text>
        <View style={styles.helpRow}>{help.map((item, i) => <Pressable key={item.id} testID={`home-help-${item.id}`} accessibilityRole="button" onPress={item.action} style={({ pressed }) => [styles.helpCard, pressed && styles.pressed]}>
          <View style={[styles.helpIcon, i === 1 ? styles.goldIcon : i === 2 ? styles.greenIcon : null]}><Ionicons name={item.icon} size={24} color={i === 1 ? colors.brandSecondary : i === 2 ? colors.success : colors.primary} /></View>
          <Text style={styles.helpLabel}>{item.label}</Text>
        </Pressable>)}</View>

        {/* ── Someone is Missing — Emergency Card ───────────────────────── */}
        <Pressable
          testID="home-missing-person"
          accessibilityRole="button"
          style={({ pressed }) => [styles.missingCard, pressed && styles.pressed]}
          onPress={() => router.push('/missing')}
        >
          <View style={styles.missingLeft}>
            <Ionicons name="alert-circle" size={23} color={colors.error} />
            <View>
              <Text style={styles.missingTitle}>
                {language.code === 'hi'
                  ? 'कोई लापता है'
                  : language.code === 'mr'
                  ? 'कोणी बेपत्ता आहे'
                  : 'Someone is missing'}
              </Text>
              <Text style={styles.missingSub}>
                {language.code === 'hi'
                  ? 'शिकायत तैयार करें'
                  : language.code === 'mr'
                  ? 'तक्रार तयार करा'
                  : 'Prepare written complaint'}
              </Text>
            </View>
          </View>
          <Ionicons name="chevron-forward" size={18} color={colors.error} />
        </Pressable>

        {/* ── International Visitor entry ───────────────────────────────── */}
        <Pressable
          testID="home-visitor-mode"
          accessibilityRole="button"
          style={({ pressed }) => [styles.visitorCard, pressed && styles.pressed]}
          onPress={() => router.push('/visitor')}
        >
          <View style={styles.missingLeft}>
            <Text style={styles.visitorFlag}>🌍</Text>
            <View>
              <Text style={styles.visitorTitle}>International Visitor?</Text>
              <Text style={styles.missingSub}>Lost passport · Emergency help · Speak For Me</Text>
            </View>
          </View>
          <Ionicons name="chevron-forward" size={18} color={colors.primary} />
        </Pressable>
        <View style={styles.sectionRow}><Text testID="home-complaints-heading" style={styles.sectionTitle}>YOUR COMPLAINTS</Text>
          <Pressable testID="home-see-all" accessibilityRole="button" style={styles.seeAll} onPress={() => router.push('/(tabs)/complaints')}><Text style={styles.link}>See all →</Text></Pressable>
        </View>
        <ComplaintsList />
        <Text testID="home-ask-heading" style={[styles.sectionTitle, styles.askHeading]}>ASK YOUR LEGAL QUESTION</Text>
        <View testID="home-ask-row" style={styles.askRow}>
          <TextInput testID="home-question-input" accessibilityLabel={`Ask in ${language.native}`} style={styles.askInput} placeholder={`Ask in ${language.native}…`} placeholderTextColor={colors.onSurfaceTertiary} value={question} onChangeText={setQuestion} returnKeyType="go" onSubmitEditing={() => openChat()} />
          <Pressable testID="home-ask-action" accessibilityRole="button" accessibilityLabel={question.trim() ? 'Open question in Ask AI' : 'Open voice chat'} style={styles.askButton} onPress={() => openChat(!question.trim())}><Ionicons name={question.trim() ? 'arrow-forward' : 'mic'} size={22} color={colors.onGold} /></Pressable>
        </View>
        <View style={styles.disclaimer}><DisclaimerBanner testID="home-legal-disclaimer" /></View>
      </Animated.View>
    </ScrollView>
    </KeyboardAvoidingView>
    <ConsentPublicHelp mode={emergency ? 'emergency' : null} onClose={() => setEmergency(false)} copy={{ ...consentCopy.en, back: 'Back to Home' }} />
  </SafeAreaView>;
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primary },
  header: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 12 },
  logo: { width: 34, height: 34 },
  brandWrap: { flex: 1, minWidth: 0, flexShrink: 1 },
  brand: { color: colors.onBrandPrimary, fontWeight: '800', fontSize: 22, letterSpacing: 0.2 },
  tagline: { color: colors.onNavyMuted, fontSize: 7, lineHeight: 12, letterSpacing: 0.3 },
  proChip: { minWidth: 48, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  proChipBadge: { flexDirection: 'row', gap: 3, alignItems: 'center', backgroundColor: colors.gold, borderRadius: 16, paddingHorizontal: 9, paddingVertical: 6 },
  proChipText: { fontSize: 12, color: colors.onGold, fontWeight: '800' },
  language: { flexDirection: 'row', gap: 5, alignItems: 'center', backgroundColor: colors.navyOverlay, paddingHorizontal: 10, minHeight: 44, borderRadius: 24, maxWidth: 118 },
  languageText: { color: colors.onBrandPrimary, fontSize: 12, fontWeight: '600', flexShrink: 1 },
  profile: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.navyOverlay, borderRadius: 22 },
  scroll: { flex: 1, backgroundColor: colors.background },
  content: { padding: 18, paddingBottom: 28, width: '100%', maxWidth: 640, alignSelf: 'center' },
  greeting: { backgroundColor: colors.primaryMid, borderRadius: 14, paddingHorizontal: 18, paddingVertical: 14, marginBottom: 14 },
  greetingText: { color: colors.onBrandPrimary, fontSize: 12, fontWeight: '700', letterSpacing: 0.6, textTransform: 'uppercase' },
  sectionTitle: { fontSize: 11, lineHeight: 16, fontWeight: '600', letterSpacing: 1, color: colors.onSurfaceTertiary },
  helpRow: { flexDirection: 'row', gap: 10, marginTop: 10, marginBottom: 10 },
  helpCard: { flex: 1, alignItems: 'center', backgroundColor: colors.surface, paddingVertical: 10, paddingHorizontal: 4, gap: 5, minHeight: 84, borderRadius: 12, borderWidth: 1, borderColor: colors.divider },
  helpIcon: { width: 40, height: 40, borderRadius: 11, backgroundColor: colors.navySoft, alignItems: 'center', justifyContent: 'center' },
  goldIcon: { backgroundColor: colors.goldSoft },
  greenIcon: { backgroundColor: colors.successSoft },
  helpLabel: { color: colors.onSurface, fontSize: 11, lineHeight: 16, fontWeight: '600', textAlign: 'center' },
  missingCard: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: colors.surface, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10,
    marginBottom: 4, borderWidth: 1, borderColor: colors.divider,
  },
  visitorCard: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: colors.navySoft, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10,
    marginBottom: 4, borderWidth: 1.5, borderColor: colors.primary + '33',
  },
  visitorFlag:  { fontSize: 22, marginRight: 2 },
  visitorTitle: { fontSize: 14, fontWeight: '700', color: colors.primary },
  missingLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  missingTitle: { fontSize: 14, fontWeight: '700', color: colors.error },
  missingSub:   { fontSize: 11, color: colors.onSurfaceTertiary, marginTop: 2 },
  sectionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 2, marginBottom: 4 },
  seeAll: { minHeight: 44, minWidth: 44, alignItems: 'flex-end', justifyContent: 'center' },
  link: { color: colors.primary, fontSize: 12, fontWeight: '700' },
  complaintActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  newComplaint: { minHeight: 44, flexDirection: 'row', gap: 7, justifyContent: 'center', alignItems: 'center', marginVertical: 8 },
  pro: { backgroundColor: colors.primary, borderRadius: 18, padding: 18, flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 24 },
  proTextWrap: { flex: 1 },
  proTitle: { fontSize: 16, fontWeight: '700', color: colors.onBrandPrimary },
  proSub: { fontSize: 12, lineHeight: 18, color: colors.onNavyMuted, marginTop: 4 },
  proBadge: { padding: 8, minWidth: 76, borderRadius: 12, backgroundColor: colors.gold, alignItems: 'center' },
  proBadgeTitle: { color: colors.onGold, fontWeight: '800', fontSize: 13 },
  proBadgeCaption: { color: colors.onGold, fontSize: 10, marginTop: 2 },
  pressed: { opacity: 0.75 },
  askHeading: { marginTop: 18, marginBottom: 10 },
  askRow: { backgroundColor: colors.surface, borderRadius: 14, padding: 10, paddingLeft: 14, flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderColor: colors.divider },
  askInput: { flex: 1, minWidth: 0, minHeight: 44, fontSize: 15, color: colors.onSurface },
  askButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.gold, alignItems: 'center', justifyContent: 'center' },
  disclaimer: { marginTop: 16, borderRadius: 10, overflow: 'hidden' },
});