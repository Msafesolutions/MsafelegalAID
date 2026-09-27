/**
 * Visitor Mode — V2: Intent Router
 * Selects between Emergency and Lost Passport workflows.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet, ActivityIndicator, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '@/src/theme';
import { loadVisitorSession, VisitorSession } from '@/src/visitor/session';

const C = theme.colors;

const WORKFLOWS = [
  {
    id: 'emergency',
    icon: 'alert-circle' as const,
    color: C.error,
    bg: '#FEF2F2',
    border: '#FECACA',
    titles: {
      en: 'Emergency Help',
      fr: 'Aide d\'urgence',
      de: 'Notfallhilfe',
      es: 'Ayuda de emergencia',
      hi: 'आपातकालीन सहायता',
    } as Record<string, string>,
    subs: {
      en: 'Accident, assault, theft, medical emergency',
      fr: 'Accident, agression, vol, urgence médicale',
      de: 'Unfall, Überfall, Diebstahl, medizinischer Notfall',
      es: 'Accidente, asalto, robo, emergencia médica',
      hi: 'दुर्घटना, हमला, चोरी, चिकित्सा आपातकाल',
    } as Record<string, string>,
    route: '/visitor/emergency',
  },
  {
    id: 'lost-passport',
    icon: 'document-outline' as const,
    color: C.primary,
    bg: C.navySoft,
    border: '#BFDBFE',
    titles: {
      en: 'Lost Passport',
      fr: 'Passeport perdu',
      de: 'Reisepass verloren',
      es: 'Pasaporte perdido',
      hi: 'पासपोर्ट खो गया',
    } as Record<string, string>,
    subs: {
      en: 'Report loss, contact embassy, FRRO process',
      fr: 'Signaler la perte, contacter l\'ambassade',
      de: 'Verlust melden, Botschaft kontaktieren',
      es: 'Reportar pérdida, contactar embajada',
      hi: 'FIR दर्ज करें, दूतावास से संपर्क करें, FRRO',
    } as Record<string, string>,
    route: '/visitor/lost-passport',
  },
];

export default function VisitorIntent() {
  const router = useRouter();
  const [session, setSession] = useState<VisitorSession | null>(null);

  useEffect(() => {
    loadVisitorSession().then(s => setSession(s));
  }, []);

  const lc = session?.touristLang.code || 'en';
  const t = (map: Record<string, string>) => map[lc] || map['en'] || '';

  if (!session) {
    return (
      <SafeAreaView style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={C.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.safe} edges={['bottom']}>
      <View style={s.content}>
        <View style={s.topBadge}>
          <Ionicons name="location-outline" size={14} color={C.primary} />
          <Text style={s.topBadgeText}>{session.indianStateName} · {session.touristLang.native}</Text>
        </View>

        <Text style={s.heading}>How can we help you?</Text>
        <Text style={s.sub}>Choose the situation that best describes your need.</Text>

        <View style={s.workflows}>
          {WORKFLOWS.map(w => (
            <Pressable
              key={w.id}
              style={({ pressed }) => [s.card, { backgroundColor: w.bg, borderColor: w.border }, pressed && { opacity: 0.8 }]}
              onPress={() => router.push(w.route as any)}
            >
              <View style={[s.iconWrap, { backgroundColor: w.color + '22' }]}>
                <Ionicons name={w.icon} size={32} color={w.color} />
              </View>
              <View style={s.cardText}>
                <Text style={[s.cardTitle, { color: w.color }]}>{t(w.titles)}</Text>
                <Text style={s.cardSub}>{t(w.subs)}</Text>
              </View>
              <Ionicons name="chevron-forward" size={22} color={w.color} />
            </Pressable>
          ))}
        </View>

        <Text style={s.alwaysNote}>
          ℹ️ In any emergency, call <Text style={{ fontWeight: '800' }}>112</Text> immediately.
        </Text>

        <Pressable style={s.callBtn} onPress={() => {
          Linking.openURL('tel:112');
        }}>
          <Ionicons name="call" size={20} color="#fff" />
          <Text style={s.callBtnText}>Call 112 — Emergency</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:    { flex: 1, backgroundColor: C.background },
  content: { flex: 1, padding: 20 },

  topBadge:     {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: C.navySoft, borderRadius: 20, alignSelf: 'flex-start',
    paddingHorizontal: 12, paddingVertical: 6, marginBottom: 20,
  },
  topBadgeText: { fontSize: 12, color: C.primary, fontWeight: '600' },

  heading: { fontSize: 24, fontWeight: '800', color: C.primary, marginBottom: 6 },
  sub:     { fontSize: 14, color: C.onSurfaceTertiary, marginBottom: 24, lineHeight: 20 },

  workflows: { gap: 14 },
  card:      {
    flexDirection: 'row', alignItems: 'center', gap: 14,
    borderRadius: 16, padding: 18, borderWidth: 1.5,
  },
  iconWrap:  { width: 56, height: 56, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  cardText:  { flex: 1 },
  cardTitle: { fontSize: 17, fontWeight: '800', marginBottom: 4 },
  cardSub:   { fontSize: 12, color: C.onSurfaceTertiary, lineHeight: 17 },

  alwaysNote: {
    fontSize: 13, color: C.onSurfaceTertiary, textAlign: 'center',
    marginTop: 24, marginBottom: 12, lineHeight: 19,
  },
  callBtn:     {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 10, backgroundColor: C.error, borderRadius: 14, paddingVertical: 16,
  },
  callBtnText: { fontSize: 16, fontWeight: '800', color: '#fff' },
});
