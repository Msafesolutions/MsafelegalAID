import { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, Modal, Alert, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth, API_BASE, Language, ModelChoice } from '@/src/auth';
import { theme } from '@/src/theme';

export default function Settings() {
  const { user, logout, language, setLanguage, model, setModel } = useAuth();
  const [langs, setLangs] = useState<Language[]>([]);
  const [models, setModels] = useState<ModelChoice[]>([]);
  const [showLang, setShowLang] = useState(false);
  const [showModel, setShowModel] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/reference/languages`).then(r => r.json()).then(setLangs);
    fetch(`${API_BASE}/api/reference/models`).then(r => r.json()).then(setModels);
  }, []);

  const confirmLogout = () => {
    if (Platform.OS === 'web') {
      // eslint-disable-next-line no-alert
      if (typeof window !== 'undefined' && window.confirm('Sign out of Gandhikar?')) {
        logout();
      }
      return;
    }
    Alert.alert('Sign out?', '', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign out', style: 'destructive', onPress: () => logout() },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="settings-screen">
      <View style={styles.header}>
        <Text style={styles.h1}>Settings</Text>
        <Text style={styles.h2}>Personalize your Gandhikar</Text>
      </View>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.profile}>
          <View style={styles.avatar}><Text style={styles.avatarTxt}>{user?.name?.[0]?.toUpperCase() || 'G'}</Text></View>
          <View style={{ marginLeft: theme.spacing.md, flex: 1 }}>
            <Text style={styles.name}>{user?.name}</Text>
            <Text style={styles.email}>{user?.email}</Text>
          </View>
        </View>

        <Text style={styles.section}>Preferences</Text>

        <Pressable testID="pick-language" style={styles.row} onPress={() => setShowLang(true)}>
          <Ionicons name="language" size={22} color={theme.colors.brand} />
          <View style={{ flex: 1, marginLeft: theme.spacing.md }}>
            <Text style={styles.rowTitle}>Language</Text>
            <Text style={styles.rowValue}>{language.native} · {language.name}</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={theme.colors.onSurfaceTertiary} />
        </Pressable>

        <Pressable testID="pick-model" style={styles.row} onPress={() => setShowModel(true)}>
          <Ionicons name="sparkles-outline" size={22} color={theme.colors.brand} />
          <View style={{ flex: 1, marginLeft: theme.spacing.md }}>
            <Text style={styles.rowTitle}>AI Model</Text>
            <Text style={styles.rowValue}>{model.label}</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={theme.colors.onSurfaceTertiary} />
        </Pressable>

        <Text style={styles.section}>Emergency Helplines</Text>
        <View style={styles.helpCard}>
          <HelpRow label="Police" number="112" />
          <HelpRow label="Women's Helpline" number="181" />
          <HelpRow label="Legal Aid (NALSA)" number="15100" />
          <HelpRow label="Child Helpline" number="1098" />
          <HelpRow label="Human Rights Commission" number="14433" />
        </View>

        <Text style={styles.section}>About</Text>
        <View style={styles.aboutCard}>
          <Text style={styles.aboutText}>
            Gandhikar is a free civic empowerment tool. Named after Mahatma Gandhi, it exists to make every Indian citizen aware of their rights under the Bharatiya Nyaya Sanhita (BNS), the Constitution of India, and other laws.
            {'\n\n'}सत्य • अहिंसा • अधिकार{'\n\n'}
            Note: Gandhikar provides legal information — not legal advice. For serious matters, consult a lawyer or contact NALSA (15100) for free legal aid.
          </Text>
        </View>

        <View testID="copyright-block" style={styles.copyBlock}>
          <Text style={styles.copyLine}>© {new Date().getFullYear()} Callistus Moses</Text>
          <Text style={styles.copySub}>An Msafe product · All rights reserved</Text>
        </View>

        <Pressable testID="logout-button" style={styles.logoutBtn} onPress={confirmLogout}>
          <Ionicons name="log-out-outline" size={20} color={theme.colors.error} />
          <Text style={styles.logoutText}>Sign out</Text>
        </Pressable>
      </ScrollView>

      <PickerModal
        testID="lang-modal"
        visible={showLang}
        title="Choose language"
        onClose={() => setShowLang(false)}
        items={langs.map(l => ({ id: l.code, label: `${l.native} · ${l.name}`, data: l }))}
        selectedId={language.code}
        onSelect={(item) => { setLanguage(item.data); setShowLang(false); }}
      />
      <PickerModal
        testID="model-modal"
        visible={showModel}
        title="Choose AI model"
        onClose={() => setShowModel(false)}
        items={models.map(m => ({ id: `${m.provider}-${m.name}`, label: m.recommended ? `${m.label} · Recommended` : m.label, data: m }))}
        selectedId={`${model.provider}-${model.name}`}
        onSelect={(item) => { setModel(item.data); setShowModel(false); }}
      />
    </SafeAreaView>
  );
}

function HelpRow({ label, number }: { label: string; number: string }) {
  return (
    <View style={styles.helpRow} testID={`help-${number}`}>
      <Text style={styles.helpLabel}>{label}</Text>
      <View style={styles.helpNumBadge}><Text style={styles.helpNum}>{number}</Text></View>
    </View>
  );
}

function PickerModal({ visible, title, onClose, items, selectedId, onSelect, testID }: any) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose} testID={testID}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <View style={styles.sheetHandle} />
          <Text style={styles.sheetTitle}>{title}</Text>
          <ScrollView style={{ maxHeight: 500 }}>
            {items.map((it: any) => (
              <Pressable
                key={it.id}
                testID={`opt-${it.id}`}
                style={[styles.opt, selectedId === it.id && styles.optSel]}
                onPress={() => onSelect(it)}
              >
                <Text style={[styles.optText, selectedId === it.id && styles.optTextSel]}>{it.label}</Text>
                {selectedId === it.id && <Ionicons name="checkmark-circle" size={22} color={theme.colors.brand} />}
              </Pressable>
            ))}
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.surface },
  header: { padding: theme.spacing.xl, paddingBottom: theme.spacing.md, borderBottomWidth: 1, borderBottomColor: theme.colors.divider },
  h1: { fontFamily: theme.fonts.display, fontSize: 28, color: theme.colors.brand, fontWeight: '700' },
  h2: { color: theme.colors.onSurfaceSecondary, marginTop: 4 },
  scroll: { padding: theme.spacing.lg, paddingBottom: theme.spacing.xxxl },
  profile: { flexDirection: 'row', alignItems: 'center', padding: theme.spacing.lg, backgroundColor: theme.colors.brand, borderRadius: theme.radius.lg },
  avatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: theme.colors.brandSecondary, alignItems: 'center', justifyContent: 'center' },
  avatarTxt: { color: theme.colors.onBrandSecondary, fontWeight: '700', fontSize: 22 },
  name: { color: theme.colors.onBrandPrimary, fontSize: 17, fontWeight: '700' },
  email: { color: '#D1D5DB', marginTop: 2, fontSize: 13 },
  section: { fontFamily: theme.fonts.display, fontSize: 16, color: theme.colors.brand, marginTop: theme.spacing.xl, marginBottom: theme.spacing.sm, fontWeight: '700' },
  row: { flexDirection: 'row', alignItems: 'center', padding: theme.spacing.lg, backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.md, marginBottom: theme.spacing.sm, borderWidth: 1, borderColor: theme.colors.border },
  rowTitle: { color: theme.colors.onSurface, fontWeight: '600' },
  rowValue: { color: theme.colors.onSurfaceSecondary, fontSize: 13, marginTop: 2 },
  helpCard: { backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.md, padding: theme.spacing.md, borderWidth: 1, borderColor: theme.colors.border },
  helpRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: theme.spacing.md, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: theme.colors.divider },
  helpLabel: { color: theme.colors.onSurface, fontSize: 15 },
  helpNumBadge: { backgroundColor: theme.colors.brandSecondary, paddingHorizontal: theme.spacing.md, paddingVertical: theme.spacing.xs, borderRadius: theme.radius.pill },
  helpNum: { color: theme.colors.onBrandSecondary, fontWeight: '700' },
  aboutCard: { backgroundColor: theme.colors.surfaceSecondary, borderRadius: theme.radius.md, padding: theme.spacing.lg, borderWidth: 1, borderColor: theme.colors.border },
  aboutText: { color: theme.colors.onSurfaceSecondary, lineHeight: 22, fontSize: 13 },
  logoutBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, padding: theme.spacing.lg, marginTop: theme.spacing.xl, borderWidth: 1, borderColor: theme.colors.error, borderRadius: theme.radius.md },
  logoutText: { color: theme.colors.error, fontWeight: '700' },
  copyBlock: { alignItems: 'center', marginTop: theme.spacing.xl, paddingVertical: theme.spacing.lg },
  copyLine: { color: theme.colors.onSurfaceSecondary, fontSize: 12, fontWeight: '700' },
  copySub: { color: theme.colors.onSurfaceTertiary, fontSize: 11, marginTop: 2, letterSpacing: 0.5 },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: theme.colors.surface, borderTopLeftRadius: theme.radius.lg, borderTopRightRadius: theme.radius.lg, padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl },
  sheetHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: theme.colors.border, alignSelf: 'center', marginBottom: theme.spacing.md },
  sheetTitle: { fontFamily: theme.fonts.display, fontSize: 20, color: theme.colors.brand, marginBottom: theme.spacing.md, fontWeight: '700' },
  opt: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: theme.spacing.md, paddingHorizontal: theme.spacing.md, borderRadius: theme.radius.md, marginBottom: 4 },
  optSel: { backgroundColor: theme.colors.surfaceSecondary },
  optText: { color: theme.colors.onSurface, fontSize: 15 },
  optTextSel: { color: theme.colors.brand, fontWeight: '700' },
});
