import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { LogBox, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { AuthProvider } from "@/src/auth";

LogBox.ignoreAllLogs(true);

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [loaded, error] = useIconFonts();

  useEffect(() => {
    if (loaded || error) {
      SplashScreen.hideAsync();
    }
  }, [loaded, error]);

  if (!loaded && !error) return null;

  return (
    <SafeAreaProvider>
      {/*
        preserveEdgeToEdge is REQUIRED here: this app enables edge-to-edge via
        Expo's own app.json `android.edgeToEdgeEnabled` config plugin, not via
        the `react-native-edge-to-edge` package. The library only
        auto-detects and preserves an externally-enabled edge-to-edge mode
        when it sees THAT package installed — otherwise it may independently
        toggle edge-to-edge off/on itself, which corrupts its own keyboard-
        height/inset math on Android 15+ (targetSdk 35 enforces edge-to-edge
        at the OS level, so the two can end up disagreeing about window
        insets). Without this prop, the composer/TextInput can render mostly
        hidden behind the keyboard on affected devices.
      */}
      <KeyboardProvider preserveEdgeToEdge>
        <AuthProvider>
          <StatusBar style="dark" />
          <View style={{ flex: 1 }}>
            <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#FDFBF7' } }} />
          </View>
        </AuthProvider>
      </KeyboardProvider>
    </SafeAreaProvider>
  );
}
