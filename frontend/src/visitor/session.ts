/**
 * Visitor Mode — Session & Feature Flags
 * Stored locally; no server account required.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'dhara_visitor_session';

export type VisitorLang = {
  code: string;
  label: string;      // in English
  native: string;     // in the language itself
};

export type VisitorSession = {
  touristLang: VisitorLang;  // the tourist's own language
  indianState: string;        // e.g. "MH" — the state they are in
  indianStateName: string;
  createdAt: string;
};

export const TOURIST_LANGUAGES: VisitorLang[] = [
  { code: 'en',  label: 'English',    native: 'English' },
  { code: 'fr',  label: 'French',     native: 'Français' },
  { code: 'de',  label: 'German',     native: 'Deutsch' },
  { code: 'es',  label: 'Spanish',    native: 'Español' },
  { code: 'pt',  label: 'Portuguese', native: 'Português' },
  { code: 'it',  label: 'Italian',    native: 'Italiano' },
  { code: 'ja',  label: 'Japanese',   native: '日本語' },
  { code: 'ko',  label: 'Korean',     native: '한국어' },
  { code: 'zh',  label: 'Chinese',    native: '中文' },
  { code: 'ar',  label: 'Arabic',     native: 'العربية' },
  { code: 'ru',  label: 'Russian',    native: 'Русский' },
  { code: 'hi',  label: 'Hindi',      native: 'हिन्दी' },
];

export const INDIAN_STATES: { code: string; name: string }[] = [
  { code: 'MH', name: 'Maharashtra' },
  { code: 'DL', name: 'Delhi' },
  { code: 'GJ', name: 'Gujarat' },
  { code: 'RJ', name: 'Rajasthan' },
  { code: 'KA', name: 'Karnataka' },
  { code: 'TN', name: 'Tamil Nadu' },
  { code: 'KL', name: 'Kerala' },
  { code: 'WB', name: 'West Bengal' },
  { code: 'UP', name: 'Uttar Pradesh' },
  { code: 'MP', name: 'Madhya Pradesh' },
  { code: 'BR', name: 'Bihar' },
  { code: 'HP', name: 'Himachal Pradesh' },
  { code: 'UK', name: 'Uttarakhand' },
  { code: 'GA', name: 'Goa' },
  { code: 'PB', name: 'Punjab' },
  { code: 'HR', name: 'Haryana' },
  { code: 'AP', name: 'Andhra Pradesh' },
  { code: 'TS', name: 'Telangana' },
  { code: 'JK', name: 'Jammu & Kashmir' },
  { code: 'AS', name: 'Assam' },
  { code: 'OD', name: 'Odisha' },
  { code: 'CH', name: 'Chandigarh (UT)' },
];

export async function saveVisitorSession(s: VisitorSession): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(s));
}

export async function loadVisitorSession(): Promise<VisitorSession | null> {
  const raw = await AsyncStorage.getItem(KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export async function clearVisitorSession(): Promise<void> {
  await AsyncStorage.removeItem(KEY);
}
