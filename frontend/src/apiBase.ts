import Constants from 'expo-constants';
import { Platform } from 'react-native';

export function resolveApiBase(platform: string, currentHost: string, backend: string, _preview: string) {
  const base = backend.replace(/\/+$/, '');
  // On web, THIS app's own domain — preview sandbox OR any production/custom
  // domain (e.g. app.dhara.msafesolutions.com) — always routes /api/* to this
  // same backend via the platform's ingress rule. The same-origin relative
  // path is therefore always correct and must be used.
  // Bug this replaces: the old logic only recognised two specific hardcoded
  // hosts and fell back to the PREVIEW backend's absolute URL for any other
  // host (e.g. the production custom domain), so signup/login on production
  // silently hit the stale preview backend and got back HTML, which the
  // client then failed to JSON.parse.
  if (platform === 'web' && currentHost) return '';
  return base;
}
const extra = Constants.expoConfig?.extra;
export const API_BASE = resolveApiBase(
  Platform.OS,
  // On native, `window` exists but `window.location` is undefined — reading .host crashed the APK at launch.
  Platform.OS === 'web' && typeof window !== 'undefined' && window.location ? window.location.host : '',
  extra?.backendUrl ?? process.env.EXPO_PUBLIC_BACKEND_URL ?? '',
  extra?.packagerHostname ?? '',
);