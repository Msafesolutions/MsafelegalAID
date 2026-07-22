import { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet, Text } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import { theme } from '@/src/theme';

export default function Index() {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (token) router.replace('/(tabs)');
    else router.replace('/login');
  }, [token, loading, router]);

  return (
    <View style={styles.c} testID="splash-screen">
      <Text style={styles.brand}>Gandhikar</Text>
      <Text style={styles.tag}>आपके अधिकार, आपकी शक्ति</Text>
      <ActivityIndicator color={theme.colors.brandSecondary} style={{ marginTop: 24 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  c: { flex: 1, backgroundColor: theme.colors.brand, alignItems: 'center', justifyContent: 'center' },
  brand: { fontFamily: theme.fonts.display, fontSize: 40, color: theme.colors.onBrandPrimary, fontWeight: '700' },
  tag: { fontFamily: theme.fonts.body, color: theme.colors.brandSecondary, marginTop: 12, fontSize: 16 },
});
