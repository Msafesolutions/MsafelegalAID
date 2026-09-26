import { Stack, useRouter, useSegments, usePathname } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect, useRef } from "react";
import { LogBox, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { KeyboardProvider } from "react-native-keyboard-controller";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { PostHogProvider, usePostHog } from "posthog-react-native";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { AuthProvider, useAuth } from "@/src/auth";
import { consentVersionKey, isCurrentConsent } from "@/src/consentStorage";
import { theme } from "@/src/theme";
import {
  POSTHOG_API_KEY,
  POSTHOG_OPTIONS,
  setPostHogInstance,
  identifyUser,
  resetAnalyticsIdentity,
  trackEvent,
} from "@/src/analytics";

LogBox.ignoreAllLogs(true);
SplashScreen.preventAutoHideAsync();

/** Redirects to /consent if the user hasn't accepted the current notice version. */
function ConsentGuard() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    if (loading || !segments.length || segments[0] === 'language' || segments[0] === 'consent') return;
    let active = true;
    void (async () => {
      const stored = await AsyncStorage.getItem(consentVersionKey(user?.id)).catch(() => null);
      if (active && !isCurrentConsent(stored, user?.terms_version)) {
        router.replace(user?.id ? { pathname: '/consent', params: { mode: 'update' } } : '/consent');
      }
    })();
    return () => { active = false; };
  }, [loading, user?.id, user?.terms_version, segments, router]);

  return null;
}

/**
 * Wires the PostHog client instance (created by PostHogProvider) into our
 * central analytics module so every trackEvent() call everywhere in the app
 * reaches the same initialised client.
 */
function PostHogBridge() {
  const posthog = usePostHog();
  const wiredRef = useRef(false);
  useEffect(() => {
    if (posthog && !wiredRef.current) {
      wiredRef.current = true;
      setPostHogInstance(posthog as any);
    }
  }, [posthog]);
  return null;
}

/**
 * Fires screen_view to PostHog + GA4 whenever the active route changes.
 * Language code is attached as a property for regional engagement reporting.
 * DPDP: no path parameters that could contain PII are forwarded — only the
 * static route template (e.g. "/(tabs)/home", "/fir-draft") is sent.
 */
function AnalyticsScreenTracker() {
  const pathname = usePathname();
  const { language } = useAuth();
  const prevRef = useRef<string>('');

  useEffect(() => {
    // Strip dynamic segments that might carry IDs (e.g. /session/abc123 → /session)
    const screen = pathname.replace(/\/[0-9a-f-]{8,}$/i, '').replace(/\/[0-9]+$/i, '') || '/';
    if (screen === prevRef.current) return;
    prevRef.current = screen;
    trackEvent('screen_view', { screen_name: screen, language: language.code });
  }, [pathname, language.code]);

  return null;
}

/**
 * Identifies the signed-in user in PostHog and GA4 using a SHA-256 hashed
 * user ID (DPDP Act 2023 compliance — no raw PII leaves the device).
 * Calls reset() when the user signs out so subsequent events are anonymous.
 */
function AnalyticsIdentitySync() {
  const { user } = useAuth();
  const prevIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (user?.id && user.id !== prevIdRef.current) {
      prevIdRef.current = user.id;
      // Fire-and-forget; hash is async but the user session is already set.
      identifyUser(user.id, { is_pro: user.is_pro ?? false }).catch(() => {});
    } else if (!user && prevIdRef.current) {
      prevIdRef.current = null;
      resetAnalyticsIdentity();
    }
  }, [user?.id, user?.is_pro]);

  return null;
}

export default function RootLayout() {
  const [loaded, error] = useIconFonts();

  useEffect(() => {
    if (loaded || error) SplashScreen.hideAsync();
  }, [loaded, error]);

  if (!loaded && !error) return null;

  return (
    <SafeAreaProvider>
      <KeyboardProvider preserveEdgeToEdge>
        {/* PostHogProvider must wrap AuthProvider so PostHogBridge can reach
            the client while AuthProvider still owns the user state. */}
        <PostHogProvider
          apiKey={POSTHOG_API_KEY}
          options={POSTHOG_OPTIONS as any}
        >
          <AuthProvider>
            <PostHogBridge />
            <AnalyticsIdentitySync />
            <AnalyticsScreenTracker />
            <ConsentGuard />
            <StatusBar style="dark" />
            <View style={{ flex: 1 }}>
              <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: theme.colors.surface } }} />
            </View>
          </AuthProvider>
        </PostHogProvider>
      </KeyboardProvider>
    </SafeAreaProvider>
  );
}
