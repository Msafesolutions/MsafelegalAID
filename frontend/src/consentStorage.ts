import AsyncStorage from '@react-native-async-storage/async-storage';
import { CONSENT_NOTICE_VERSION } from './consentStrings';

export const CONSENT_VERSION_KEY = 'gk_consent_version';
export const CONSENT_ANON_KEY = 'gk_consent_anon_id';
export const CONSENT_PREFS_KEY = 'gk_consent_prefs';

// A different signed-in account must never inherit another account's acceptance.
export function consentVersionKey(userId?: string) {
  return userId ? `${CONSENT_VERSION_KEY}:${userId}` : CONSENT_VERSION_KEY;
}

export function isCurrentConsent(local: string | null, server?: string) {
  // The legacy server stores a notice date in terms_version. Legal version
  // "2.0" is NOT comparable to a notice date. Compare exact notice versions.
  return local === CONSENT_NOTICE_VERSION || server === CONSENT_NOTICE_VERSION;
}

export async function saveConsentLocally(
  purposes: { core: boolean; analytics: boolean; updates: boolean }, userId?: string,
) {
  const prefsKey = userId ? `${CONSENT_PREFS_KEY}:${userId}` : CONSENT_PREFS_KEY;
  // Write the version last: it is the completion marker read by the guard.
  await AsyncStorage.setItem(prefsKey, JSON.stringify(purposes));
  await AsyncStorage.setItem(consentVersionKey(userId), CONSENT_NOTICE_VERSION);
}