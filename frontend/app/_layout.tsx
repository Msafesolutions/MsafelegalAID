import { Stack, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { LogBox, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { KeyboardProvider } from "react-native-keyboard-controller";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { AuthProvider, useAuth } from "@/src/auth";
import { consentVersionKey, isCurrentConsent } from "@/src/consentStorage";

LogBox.ignoreAllLogs(true);
SplashScreen.preventAutoHideAsync();

/** Redirects to /consent if the user hasn't accepted the current notice version. */
function ConsentGuard() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    // Let the splash/language flow settle first. Never stack consent screens.
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
