// Icon font loader for Expo apps. Fonts are loaded from a CDN only under
// Expo Go (StoreClient) — that's where @expo/vector-icons' .ttf files come
// back as 0 bytes from Metro's asset resolver on Android. Native dev/prod
// builds and web pass an empty map, so useFonts resolves to [true, null]
// immediately via react-native-vector-icons autolinking / web stubs.
// ICON_VECTOR_VERSION must match @expo/vector-icons in package.json.
// Usage: const [loaded, error] = useIconFonts();

import Constants, { ExecutionEnvironment } from "expo-constants";
import { useFonts } from "expo-font";

const ICON_VECTOR_VERSION = "15.1.1";

// short internal fontName (what the library queries) -> CDN .ttf file name
const ICON_FAMILIES: Record<string, string> = {
  anticon: "AntDesign",
  entypo: "Entypo",
  evilicons: "EvilIcons",
  feather: "Feather",
  FontAwesome: "FontAwesome",
  Fontisto: "Fontisto",
  foundation: "Foundation",
  ionicons: "Ionicons",
  "material-community": "MaterialCommunityIcons",
  material: "MaterialIcons",
  octicons: "Octicons",
  "simple-line-icons": "SimpleLineIcons",
  zocial: "Zocial",
  // FontAwesome5 style variants (key = `FontAwesome5Free-<style>`)
  "FontAwesome5Free-Regular": "FontAwesome5_Regular",
  "FontAwesome5Free-Solid": "FontAwesome5_Solid",
  "FontAwesome5Free-Brand": "FontAwesome5_Brands",
  // FontAwesome6 style variants (key = `FontAwesome6Free-<style>`)
  "FontAwesome6Free-Regular": "FontAwesome6_Regular",
  "FontAwesome6Free-Solid": "FontAwesome6_Solid",
  "FontAwesome6Free-Brand": "FontAwesome6_Brands",
};

const cdnUrl = (file: string): string =>
  `https://cdn.jsdelivr.net/npm/@expo/vector-icons@${ICON_VECTOR_VERSION}/build/vendor/react-native-vector-icons/Fonts/${file}.ttf`;

const iconFontMap = (): Record<string, string> =>
  Object.fromEntries(
    Object.entries(ICON_FAMILIES).map(([key, file]) => [key, cdnUrl(file)]),
  );

// On web: only load the Ionicons font (most used icon family) to prevent
// the "icon flash" on first render while keeping load time minimal.
// Loaded from the LOCAL node_modules copy (bundled by Metro), not the CDN —
// app boot must never depend on an external network fetch succeeding.
// If cdn.jsdelivr.net is slow/unreachable (sandboxed/offline preview,
// corporate proxy, flaky network), useFonts() would hang and the whole app
// would stay on a blank splash screen until the browser's own connection
// timeout, since RootLayout returns null until loaded/error resolves.
// Full CDN map is only needed in Expo Go (StoreClient) on Android, where the
// local Metro-bundled .ttf is served as 0 bytes by the asset resolver.
const webFontMap = (): Record<string, any> => ({
  ionicons: require("../../node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/Fonts/Ionicons.ttf"),
});

export const useIconFonts = (): readonly [boolean, Error | null] =>
  useFonts(
    Constants.executionEnvironment === ExecutionEnvironment.StoreClient
      ? iconFontMap()        // Expo Go Android: all families from CDN
      : typeof document !== "undefined"
        ? webFontMap()       // Web: Ionicons only, bundled locally
        : {},                // Native dev/prod build: autolinking handles it
  );
