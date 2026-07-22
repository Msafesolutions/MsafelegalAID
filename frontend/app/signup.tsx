import { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, Link } from 'expo-router';
import { useAuth } from '@/src/auth';
import { theme } from '@/src/theme';

export default function Signup() {
  const { register } = useAuth();
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    setError(null);
    if (password.length < 6) { setError('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      await register(email.trim(), password, name.trim());
      router.replace('/(tabs)');
    } catch (e: any) {
      setError(e?.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} testID="signup-screen">
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.brand}>Gandhikar</Text>
          <Text style={styles.tag}>Empowerment through knowledge</Text>

          <View style={styles.card}>
            <Text style={styles.heading}>Create your account</Text>
            <Text style={styles.sub}>Free forever. No fear, just facts.</Text>

            <Text style={styles.label}>Name</Text>
            <TextInput testID="signup-name-input" style={styles.input} value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor={theme.colors.onSurfaceTertiary} />

            <Text style={styles.label}>Email</Text>
            <TextInput testID="signup-email-input" style={styles.input} value={email} onChangeText={setEmail} placeholder="you@example.com" placeholderTextColor={theme.colors.onSurfaceTertiary} autoCapitalize="none" autoCorrect={false} keyboardType="email-address" />

            <Text style={styles.label}>Password</Text>
            <TextInput testID="signup-password-input" style={styles.input} value={password} onChangeText={setPassword} placeholder="At least 6 characters" placeholderTextColor={theme.colors.onSurfaceTertiary} secureTextEntry />

            {error && <Text style={styles.error} testID="signup-error">{error}</Text>}

            <Pressable testID="signup-submit-button" style={[styles.btn, loading && { opacity: 0.6 }]} disabled={loading} onPress={onSubmit}>
              {loading ? <ActivityIndicator color={theme.colors.onBrandPrimary} /> : <Text style={styles.btnText}>Create account</Text>}
            </Pressable>

            <View style={styles.row}>
              <Text style={styles.sub}>Already registered? </Text>
              <Link href="/login" asChild>
                <Pressable testID="go-to-login"><Text style={styles.link}>Sign in</Text></Pressable>
              </Link>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.brand },
  scroll: { flexGrow: 1, padding: theme.spacing.xl, justifyContent: 'center' },
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
  error: { color: theme.colors.error, marginTop: theme.spacing.md },
});
