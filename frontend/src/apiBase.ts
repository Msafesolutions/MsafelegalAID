import Constants from 'expo-constants';
import { Platform } from 'react-native';

export function resolveApiBase(platform: string, currentHost: string, backend: string, preview: string) {
  const base = backend.replace(/\/+$/, '');
  if (platform !== 'web' || !currentHost) return base;
  const host = (value: string) => {
    try { return value ? new URL(value.includes('://') ? value : `https://${value}`).host.toLowerCase() : ''; }
    catch { return ''; }
  };
  return currentHost.toLowerCase() === host(base) || (host(preview) && currentHost.toLowerCase() === host(preview)) ? '' : base;
}
const extra = Constants.expoConfig?.extra;
export const API_BASE = resolveApiBase(
  Platform.OS,
  // On native, `window` exists but `window.location` is undefined — reading .host crashed the APK at launch.
  Platform.OS === 'web' && typeof window !== 'undefined' && window.location ? window.location.host : '',
  extra?.backendUrl ?? process.env.EXPO_PUBLIC_BACKEND_URL ?? '',
  extra?.packagerHostname ?? '',
);