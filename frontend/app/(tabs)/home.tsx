import { useCallback, useEffect, useRef, useState } from 'react';
import { Animated, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { setStatusBarStyle } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/auth';
import { theme } from '@/src/theme';
import { ComplaintsList } from '@/src/home/ComplaintsList';
import { DisclaimerBanner } from '@/src/components/DisclaimerBanner';
import { ConsentPublicHelp } from '@/src/components/ConsentPublicHelp';
import { consentCopy } from '@/src/consentCopy';

const colors = theme.colors;
export default function Home() {
  const { user, language } = useAuth();
  const router = useRouter();
  const [emergency, setEmergency] = useState(false);
  const entrance = useRef(new Animated.Value(0)).current;
  useEffect(() => { Animated.timing(entrance, { toValue: 1, duration: 280, useNativeDriver: true }).start(); }, [entrance]);
  useFocusEffect(useCallback(() => { setStatusBarStyle('light'); return () => setStatusBarStyle('dark'); }, []));
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const firstName = user?.name?.trim().split(/\s+/)[0] || 'there';
  const help = [
    { id: 'rights', label: 'Know Your\nRights', icon: 'shield-checkmark-outline' as const, action: () => router.push('/(tabs)/rights') },
    { id: 'advocate', label: 'Find an\nAdvocate', icon: 'call-outline' as const, action: () => router.push('/(tabs)/advocate') },
    { id: 'emergency', label: 'Emergency\nHelplines', icon: 'shield-outline' as const, action: () => setEmergency(true) },
  ];
  return <SafeAreaView style={styles.safe} edges={['top']} testID="home-screen">
    <View testID="home-header" style={styles.header}>
      <View style={styles.logo}><Text style={styles.logoText}>ध</Text></View>
      <View style={styles.brandWrap}><Text testID="home-brand" style={styles.brand}>Dhara</Text><Text testID="home-tagline" style={styles.tagline}>YOUR LEGAL RIGHTS</Text></View>
      <Pressable testID="home-language" accessibilityRole="button" accessibilityLabel="Change language" style={styles.language} onPress={() => router.push({ pathname: '/language', params: { from: 'home' } })}>
        <Ionicons name="globe-outline" size={15} color={colors.onBrandPrimary} /><Text style={styles.languageText} numberOfLines={1}>{language.native}</Text><Ionicons name="chevron-down" size={12} color={colors.onBrandPrimary} />
      </Pressable>
      <Pressable testID="home-profile" accessibilityRole="button" accessibilityLabel="Your profile" style={styles.profile} onPress={() => router.push('/(tabs)/settings')}><Ionicons name="person-outline" size={20} color={colors.onBrandPrimary} /></Pressable>
    </View>
    <ScrollView testID="home-scroll" style={styles.scroll} contentContainerStyle={styles.content}>
      <Animated.View testID="home-content" style={{ opacity: entrance, transform: [{ translateY: entrance.interpolate({ inputRange: [0, 1], outputRange: [8, 0] }) }] }}>
        <View testID="home-greeting-panel" style={styles.greeting}><Text testID="home-greeting" style={styles.greetingText}>{greeting}, {firstName}</Text></View>
        <Text testID="home-quick-help-heading" style={styles.sectionTitle}>QUICK HELP</Text>
        <View style={styles.helpRow}>{help.map((item, i) => <Pressable key={item.id} testID={`home-help-${item.id}`} accessibilityRole="button" onPress={item.action} style={({ pressed }) => [styles.helpCard, pressed && styles.pressed]}>
          <View style={[styles.helpIcon, i === 1 ? styles.goldIcon : i === 2 ? styles.greenIcon : null]}><Ionicons name={item.icon} size={22} color={i === 1 ? colors.brandSecondary : i === 2 ? colors.success : colors.primary} /></View>
          <Text style={styles.helpLabel}>{item.label}</Text>
        </Pressable>)}</View>
        <View style={styles.sectionRow}><Text testID="home-complaints-heading" style={styles.sectionTitle}>YOUR COMPLAINTS</Text>
          <View style={styles.complaintActions}><Pressable testID="home-new-complaint" accessibilityRole="button" accessibilityLabel="Start a new complaint" style={styles.seeAll} onPress={() => router.push('/fir-draft')}><Ionicons name="add-circle-outline" size={22} color={colors.primary} /></Pressable><Pressable testID="home-see-all" accessibilityRole="button" style={styles.seeAll} onPress={() => router.push('/complaints')}><Text style={styles.link}>See all</Text></Pressable></View>
        </View>
        <ComplaintsList />
        <Pressable testID="home-pro-card" accessibilityRole="button" style={({ pressed }) => [styles.pro, pressed && styles.pressed]} onPress={() => router.push('/upgrade')}>
          <View style={styles.proTextWrap}><Text testID="home-pro-title" style={styles.proTitle}>{user?.is_pro ? 'Your Dhara Pro' : 'Unlock Dhara Pro'}</Text><Text testID="home-pro-description" style={styles.proSub}>Detailed legal information{ '\n' }Drafts & action plans</Text></View>
          <View style={styles.proBadge}><Ionicons name="star" size={18} color={colors.onGold} /><Text style={styles.proBadgeTitle}>Pro</Text><Text style={styles.proBadgeCaption}>{user?.is_pro ? 'Manage' : 'View plans'}</Text></View>
        </Pressable>
        <View style={styles.disclaimer}><DisclaimerBanner testID="home-legal-disclaimer" /></View>
      </Animated.View>
    </ScrollView>
    <ConsentPublicHelp mode={emergency ? 'emergency' : null} onClose={() => setEmergency(false)} copy={{ ...consentCopy.en, back: 'Back to Home' }} />
  </SafeAreaView>;
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.primary },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 20, paddingVertical: 18 },
  logo: { width: 38, height: 38, borderRadius: 11, backgroundColor: colors.gold, alignItems: 'center', justifyContent: 'center' },
  logoText: { fontSize: 22, color: colors.onGold, fontWeight: '800' },
  brandWrap: { flex: 1, minWidth: 62 },
  brand: { color: colors.onBrandPrimary, fontWeight: '800', fontSize: 22, letterSpacing: 0.2 },
  tagline: { color: colors.onNavyMuted, fontSize: 8, lineHeight: 14, letterSpacing: 0.9 },
  language: { flexDirection: 'row', gap: 5, alignItems: 'center', backgroundColor: colors.navyOverlay, paddingHorizontal: 10, minHeight: 44, borderRadius: 24, maxWidth: 118 },
  languageText: { color: colors.onBrandPrimary, fontSize: 12, fontWeight: '600', flexShrink: 1 },
  profile: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.navyOverlay, borderRadius: 22 },
  scroll: { flex: 1, backgroundColor: colors.background },
  content: { padding: 18, paddingBottom: 28, width: '100%', maxWidth: 640, alignSelf: 'center' },
  greeting: { backgroundColor: colors.primaryMid, borderRadius: 22, paddingHorizontal: 22, paddingVertical: 15, marginBottom: 18 },
  greetingText: { color: colors.onBrandPrimary, fontSize: 12, fontWeight: '700', letterSpacing: 0.6, textTransform: 'uppercase' },
  sectionTitle: { fontSize: 11, lineHeight: 16, fontWeight: '600', letterSpacing: 1, color: colors.onSurfaceTertiary },
  helpRow: { flexDirection: 'row', gap: 10, marginTop: 10, marginBottom: 10 },
  helpCard: { flex: 1, alignItems: 'center', backgroundColor: colors.surface, paddingVertical: 16, paddingHorizontal: 5, gap: 9, minHeight: 106, borderRadius: 16, borderWidth: 1, borderColor: colors.divider },
  helpIcon: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.navySoft, alignItems: 'center', justifyContent: 'center' },
  goldIcon: { backgroundColor: colors.goldMuted },
  greenIcon: { backgroundColor: colors.successSoft },
  helpLabel: { color: colors.onSurface, fontSize: 11, lineHeight: 16, fontWeight: '600', textAlign: 'center' },
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
  disclaimer: { marginTop: 16, borderRadius: 10, overflow: 'hidden' },
});