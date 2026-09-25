/**
 * Missing Person — Entry Screen (First Screen)
 * Shows urgent notice + 112 / 1098 tap-to-call buttons.
 * "Prepare Written Complaint" navigates to the interview.
 *
 * DATA POLICY: No answers leave the device. PDF generated on-device only.
 * Route: /missing
 */
import {
  View, Text, Pressable, ScrollView, StyleSheet, Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import interviewData from '@/src/content/missing_interview.json';

type Lang = 'en' | 'hi' | 'mr';

const NAVY  = '#1B2B5B';
const RED   = '#CC0000';
const GOLD  = '#C9973A';
const BG    = '#FAFAF8';

function t(obj: Record<string, string> | undefined, lang: Lang): string {
  if (!obj) return '';
  return obj[lang] || obj['en'] || '';
}

export default function MissingEntryScreen() {
  const { language: rawLang } = useAuth();
  const lang: Lang = (['en', 'hi', 'mr'].includes(rawLang) ? rawLang : 'en') as Lang;
  const router = useRouter();

  const first = interviewData.entry_screens.first_screen;

  const makeCall = (number: string) => {
    Linking.openURL(`tel:${number}`).catch(() => {
      Linking.openURL(`https://en.wikipedia.org/wiki/Emergency_telephone_number`);
    });
  };

  return (
    <SafeAreaView style={s.safe} edges={['top']}>
      <ScrollView contentContainerStyle={s.scroll}>
        {/* Header */}
        <View style={s.header}>
          <Text style={s.title}>{t(first.title, lang)}</Text>
          <View style={s.urgentBadge}>
            <Text style={s.urgentText}>🚨 {t(first.urgent_note, lang)}</Text>
          </View>
        </View>

        {/* Body text */}
        <Text style={s.body}>{t(first.body, lang)}</Text>

        {/* Emergency call buttons */}
        <View style={s.callSection}>
          {first.emergency_numbers.map(num => (
            <Pressable
              key={num.number}
              style={[s.callBtn, num.number === '1098' && s.callBtnSecondary]}
              onPress={() => makeCall(num.number)}
            >
              <Text style={s.callIcon}>📞</Text>
              <View style={s.callInfo}>
                <Text style={s.callNumber}>{num.number}</Text>
                <Text style={s.callLabel}>{t(num.label, lang)}</Text>
              </View>
            </Pressable>
          ))}
        </View>

        {/* Divider */}
        <View style={s.divider} />

        {/* Continue to interview */}
        <Pressable
          style={s.continueBtn}
          onPress={() => router.push('/missing/interview')}
        >
          <Text style={s.continueBtnText}>{t(first.continue_label, lang)}</Text>
        </Pressable>

        <Text style={s.note}>
          {lang === 'hi'
            ? 'आपके उत्तर केवल इस डिवाइस पर सुरक्षित रहेंगे।'
            : lang === 'mr'
            ? 'तुमची उत्तरे फक्त या डिव्हाइसवर सुरक्षित राहतील.'
            : 'Your answers are stored on this device only — never uploaded.'}
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:          { flex: 1, backgroundColor: BG },
  scroll:        { paddingHorizontal: 20, paddingTop: 20, paddingBottom: 40 },

  header:        { marginBottom: 16 },
  title:         { fontSize: 28, fontWeight: '800', color: NAVY, letterSpacing: -0.5, marginBottom: 12 },

  urgentBadge:   {
    backgroundColor: '#FFF0F0', borderRadius: 10, padding: 12,
    borderLeftWidth: 4, borderLeftColor: RED,
  },
  urgentText:    { fontSize: 13, color: RED, lineHeight: 19, fontWeight: '600' },

  body:          { fontSize: 15, color: '#444', lineHeight: 23, marginBottom: 24 },

  callSection:   { gap: 12, marginBottom: 24 },
  callBtn:       {
    backgroundColor: RED, borderRadius: 16, padding: 18,
    flexDirection: 'row', alignItems: 'center', gap: 14,
    shadowColor: RED, shadowOpacity: 0.3, shadowRadius: 8, shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  callBtnSecondary: { backgroundColor: '#E65C00' },
  callIcon:      { fontSize: 28 },
  callInfo:      { flex: 1 },
  callNumber:    { fontSize: 28, fontWeight: '800', color: '#FFF', letterSpacing: 1 },
  callLabel:     { fontSize: 13, color: 'rgba(255,255,255,0.85)', marginTop: 2 },

  divider:       { height: 1, backgroundColor: '#E5E7EB', marginBottom: 24 },

  continueBtn:   {
    backgroundColor: NAVY, borderRadius: 14, paddingVertical: 18,
    alignItems: 'center', marginBottom: 14,
    shadowColor: NAVY, shadowOpacity: 0.25, shadowRadius: 8, shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  continueBtnText: { fontSize: 17, fontWeight: '700', color: '#FFF' },

  note:          { fontSize: 12, color: '#888', textAlign: 'center', lineHeight: 17 },
});
