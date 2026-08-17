import { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, ActivityIndicator, KeyboardAvoidingView, ScrollView, Platform, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, Link } from 'expo-router';
import { useAuth } from '@/src/auth';
import { theme } from '@/src/theme';

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/(tabs)');
    } catch (e: any) {
      setError(e?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} testID="login-screen">
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
        <Image source={require('../assets/images/icon.png')} style={styles.logo} resizeMode="contain" />
        <Text style={styles.brand}>Dhara</Text>
          <Text style={styles.tag}>Know your rights. Speak them.</Text>

          <View style={styles.card}>
            <Text style={styles.heading}>Welcome back</Text>
            <Text style={styles.sub}>Sign in to continue</Text>

            <Text style={styles.label}>Email</Text>
            <TextInput
              testID="login-email-input"
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor={theme.colors.onSurfaceTertiary}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
            />

            <Text style={styles.label}>Password</Text>
            <TextInput
              testID="login-password-input"
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              placeholderTextColor={theme.colors.onSurfaceTertiary}
              secureTextEntry
            />

            {error && <Text style={styles.error} testID="login-error">{error}</Text>}

            <Pressable testID="login-submit-button" style={[styles.btn, loading && { opacity: 0.6 }]} disabled={loading} onPress={onSubmit}>
              {loading ? <ActivityIndicator color={theme.colors.onBrandPrimary} /> : <Text style={styles.btnText}>Sign In</Text>}
            </Pressable>

            <Link href="/forgot-password" asChild>
              <Pressable testID="go-to-forgot-password" style={styles.forgotWrap}>
                <Text style={styles.forgotLink}>Forgot password?</Text>
              </Pressable>
            </Link>

            <View style={styles.row}>
              <Text style={styles.sub}>New here? </Text>
              <Link href="/signup" asChild>
                <Pressable testID="go-to-signup"><Text style={styles.link}>Create an account</Text></Pressable>
              </Link>
            </View>
          </View>

          <Text style={styles.footer}>सत्य • अहिंसा • अधिकार</Text>
          <Text testID="login-copyright" style={styles.copyright}>© {new Date().getFullYear()} Callistus Moses · An Msafe product</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.brand },
  scroll: { flexGrow: 1, padding: theme.spacing.xl, justifyContent: 'center' },
  // Fixed square dimensions + resizeMode="contain" — the logo can never stretch.
  logo: { width: 84, height: 84, alignSelf: 'center', borderRadius: 20, marginBottom: 12 },
  brand: { fontFamily: theme.fonts.display, fontSize: 44, color: theme.colors.onBrandPrimary, textAlign: 'center', fontWeight: '700' },
  tag: { color: theme.colors.brandSecondary, textAlign: 'center', marginTop: 8, fontSize: 15 },
  card: { backgroundColor: theme.colors.surface, borderRadius: theme.radius.lg, padding: theme.spacing.xl, marginTop: theme.spacing.xxl },
  heading: { fontFamily: theme.fonts.display, fontSize: 24, color: theme.colors.onSurface, fontWeight: '700' },
  sub: { color: theme.colors.onSurfaceSecondary, marginTop: 4 },
  label: { color: theme.colors.onSurfaceSecondary, marginTop: theme.spacing.lg, marginBottom: theme.spacing.sm, fontWeight: '600' },
  input: { borderWidth: 1, borderColor: theme.colors.border, borderRadius: theme.radius.md, padding: theme.spacing.md, fontSize: 16, color: theme.colors.onSurface, backgroundColor: theme.colors.surfaceSecondary },
  btn: { backgroundColor: theme.colors.brand, padding: theme.spacing.lg, borderRadius: theme.radius.md, alignItems: 'center', marginTop: theme.spacing.xl, minHeight: 52 },
  btnText: { color: theme.colors.onBrandPrimary, fontWeight: '700', fontSize: 16 },
  row: { flexDirection: 'row', justifyContent: 'center', marginTop: theme.spacing.lg },
  link: { color: theme.colors.brandSecondary, fontWeight: '700' },
  forgotWrap: { alignItems: 'center', marginTop: theme.spacing.md, padding: 6 },
  forgotLink: { color: theme.colors.brand, fontWeight: '600', fontSize: 14, textDecorationLine: 'underline' },
  error: { color: theme.colors.error, marginTop: theme.spacing.md },
  footer: { textAlign: 'center', color: theme.colors.brandSecondary, marginTop: theme.spacing.xxl, letterSpacing: 2 },
  copyright: { textAlign: 'center', color: '#8A93A6', marginTop: theme.spacing.md, fontSize: 11, letterSpacing: 0.5 },
});
