import { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet, Text, Image } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { useAuth } from '@/src/auth';
import { theme } from '@/src/theme';

export default function Index() {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    (async () => {
      if (token) {
        router.replace('/(tabs)/home');
        return;
      }
      // First launch → user picks a language before login
      const savedLang = await AsyncStorage.getItem('gk_lang');
      router.replace(savedLang ? '/login' : '/language');
    })();
  }, [token, loading, router]);

  return (
    <View style={styles.c} testID="splash-screen">
      <Image source={require('../assets/images/icon.png')} style={styles.logo} resizeMode="contain" />
      <Text style={styles.brand}>Dhara</Text>
      <Text style={styles.tag}>आपके अधिकार, आपकी शक्ति</Text>
      <ActivityIndicator color={theme.colors.brandSecondary} style={{ marginTop: 24 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  c: { flex: 1, backgroundColor: theme.colors.brand, alignItems: 'center', justifyContent: 'center' },
  // Strict 1:1 square + contain → zero distortion on every viewport
  logo: { width: 88, height: 88, aspectRatio: 1, borderRadius: 22, marginBottom: 16 },
  brand: { fontFamily: theme.fonts.display, fontSize: 40, color: theme.colors.onBrandPrimary, fontWeight: '700' },
  tag: { fontFamily: theme.fonts.body, color: theme.colors.brandSecondary, marginTop: 12, fontSize: 16 },
});
