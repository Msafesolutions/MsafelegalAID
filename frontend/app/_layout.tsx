import { Stack, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect, useCallback } from "react";
import { LogBox, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { KeyboardProvider } from "react-native-keyboard-controller";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { AuthProvider, useAuth } from "@/src/auth";
import { CONSENT_NOTICE_VERSION, CONSENT_VERSION_KEY } from "@/src/consentStrings";

LogBox.ignoreAllLogs(true);
SplashScreen.preventAutoHideAsync();

/** Redirects to /consent if the user hasn't accepted the current notice version. */
function ConsentGuard() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  const checkConsent = useCallback(async () => {
    if (loading) return;
    // Never redirect from the consent screen itself
    if (segments.includes('consent' as never)) return;

    // Check stored local version first (covers pre-login visit)
    const stored = await AsyncStorage.getItem(CONSENT_VERSION_KEY).catch(() => null);
    const userVersion = (user as any)?.terms_version || null;
    const effective = userVersion || stored;

    if (!effective || effective < CONSENT_NOTICE_VERSION) {
      const mode = user ? 'update' : undefined;
      // Use router.push so user can come back if needed
      router.push(mode
        ? ({ pathname: '/consent', params: { mode } } as any)
        : ('/consent' as any),
      );
    }
  }, [loading, user, segments, router]);

  useEffect(() => { checkConsent(); }, [checkConsent]);

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
        <AuthProvider>
          <ConsentGuard />
          <StatusBar style="dark" />
          <View style={{ flex: 1 }}>
            <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#FDFBF7' } }} />
          </View>
        </AuthProvider>
      </KeyboardProvider>
    </SafeAreaProvider>
  );
}
