import { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet, Image } from 'react-native';
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
      <Image
        source={require('../assets/images/dhara_logo_full.png')}
        style={styles.logo}
        resizeMode="contain"
      />
      <ActivityIndicator color={theme.colors.gold} style={{ marginTop: 32 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  c: { flex: 1, backgroundColor: theme.colors.brand, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 40 },
  logo: { width: 260, height: 260, resizeMode: 'contain' },
});
