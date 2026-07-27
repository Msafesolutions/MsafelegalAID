import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, Link } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { API_BASE, useAuth } from '@/src/auth';
import { theme } from '@/src/theme';

/**
 * Zero-cost password reset — user proves account ownership by matching the
 * email + registered phone number. On success the backend auto-logs the user
 * in with the new password.
 */
export default function ForgotPassword() {
  const router = useRouter();
  const { hydrateSession } = useAuth();
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    setError(null);
    if (!email.trim() || !phone.trim() || !newPassword) {
      setError('Please fill in all fields.');
      return;
    }
    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          phone: phone.trim(),
          new_password: newPassword,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.detail || 'Reset failed. Please try again.');
        return;
      }
      // Success — auto-login using the returned token
      if (hydrateSession) {
        await hydrateSession(data.token, data.user);
      }
      Alert.alert(
        'Password reset',
        'Your password has been updated. You are now signed in.',
        [{ text: 'OK', onPress: () => router.replace('/(tabs)') }],
      );
    } catch (e: any) {
      setError(e?.message || 'Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} testID="forgot-password-screen">
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Pressable onPress={() => router.back()} style={styles.back} testID="fp-back">
            <Ionicons name="chevron-back" size={22} color={theme.colors.onBrandPrimary} />
            <Text style={styles.backText}>Back to sign in</Text>
          </Pressable>

          <Text style={styles.brand}>Dhara</Text>
          <Text style={styles.tag}>Reset your password</Text>

          <View style={styles.card}>
            <Text style={styles.heading}>Forgot password?</Text>
            <Text style={styles.sub}>
              {'Enter your email and the phone number you registered with. We\u2019ll let you set a new password immediately \u2014 no email link needed.'}
            </Text>

            <Text style={styles.label}>Email</Text>
            <TextInput
              testID="fp-email-input"
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor={theme.colors.onSurfaceTertiary}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
            />

            <Text style={styles.label}>Registered phone number</Text>
            <TextInput
              testID="fp-phone-input"
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              placeholder="+91 98765 43210"
              placeholderTextColor={theme.colors.onSurfaceTertiary}
              keyboardType="phone-pad"
              autoCorrect={false}
            />

            <Text style={styles.label}>New password (min 6 chars)</Text>
            <TextInput
              testID="fp-new-password-input"
              style={styles.input}
              value={newPassword}
              onChangeText={setNewPassword}
              placeholder="••••••••"
              placeholderTextColor={theme.colors.onSurfaceTertiary}
              secureTextEntry
            />

            <Text style={styles.label}>Confirm new password</Text>
            <TextInput
              testID="fp-confirm-password-input"
              style={styles.input}
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              placeholder="••••••••"
              placeholderTextColor={theme.colors.onSurfaceTertiary}
              secureTextEntry
            />

            {error && (
              <Text style={styles.error} testID="fp-error">
                {error}
              </Text>
            )}

            <Pressable
              testID="fp-submit-button"
              style={[styles.btn, loading && { opacity: 0.6 }]}
              disabled={loading}
              onPress={onSubmit}
            >
              {loading ? (
                <ActivityIndicator color={theme.colors.onBrandPrimary} />
              ) : (
                <Text style={styles.btnText}>Reset password & sign in</Text>
              )}
            </Pressable>

            <View style={styles.row}>
              <Text style={styles.sub}>Remembered it? </Text>
              <Link href="/login" asChild>
                <Pressable testID="go-to-login">
                  <Text style={styles.link}>Back to sign in</Text>
                </Pressable>
              </Link>
            </View>
          </View>

          <Text style={styles.footer}>सत्य • अहिंसा • अधिकार</Text>
          <Text style={styles.copyright}>
            © {new Date().getFullYear()} Callistus Moses · An Msafe product
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.brand },
  scroll: { flexGrow: 1, padding: theme.spacing.xl, paddingTop: theme.spacing.lg },
  back: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 6 },
  backText: { color: theme.colors.onBrandPrimary, fontSize: 14, fontWeight: '600' },
  brand: {
    fontFamily: theme.fonts.display,
    fontSize: 36,
    color: theme.colors.onBrandPrimary,
    textAlign: 'center',
    fontWeight: '700',
    marginTop: theme.spacing.lg,
  },
  tag: { color: theme.colors.brandSecondary, textAlign: 'center', marginTop: 4, fontSize: 14 },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.xl,
    marginTop: theme.spacing.xl,
  },
  heading: {
    fontFamily: theme.fonts.display,
    fontSize: 22,
    color: theme.colors.onSurface,
    fontWeight: '700',
  },
  sub: { color: theme.colors.onSurfaceSecondary, marginTop: 6, lineHeight: 20 },
  label: {
    color: theme.colors.onSurfaceSecondary,
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.sm,
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    fontSize: 16,
    color: theme.colors.onSurface,
    backgroundColor: theme.colors.surfaceSecondary,
  },
  btn: {
    backgroundColor: theme.colors.brand,
    padding: theme.spacing.lg,
    borderRadius: theme.radius.md,
    alignItems: 'center',
    marginTop: theme.spacing.xl,
    minHeight: 52,
  },
  btnText: { color: theme.colors.onBrandPrimary, fontWeight: '700', fontSize: 15 },
  row: { flexDirection: 'row', justifyContent: 'center', marginTop: theme.spacing.lg },
  link: { color: theme.colors.brandSecondary, fontWeight: '700' },
  error: { color: theme.colors.error, marginTop: theme.spacing.md, fontSize: 13 },
  footer: {
    textAlign: 'center',
    color: theme.colors.brandSecondary,
    marginTop: theme.spacing.xxl,
    letterSpacing: 2,
  },
  copyright: {
    textAlign: 'center',
    color: '#8A93A6',
    marginTop: theme.spacing.md,
    fontSize: 11,
    letterSpacing: 0.5,
  },
});
