import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

const API = process.env.EXPO_PUBLIC_BACKEND_URL;
const TOKEN_KEY = 'gk_token';
const USER_KEY = 'gk_user';
const LANG_KEY = 'gk_lang';
const MODEL_KEY = 'gk_model';
const AUTO_SPEAK_KEY = 'dhara_auto_speak';
const TTS_VOLUME_KEY = 'dhara_tts_volume';

export type User = { id: string; email: string; name: string; phone?: string; language: string; state?: string | null; state_name?: string; is_grandfathered?: boolean; is_pro?: boolean; pro_since?: string | null; pro_samples_used?: number; pro_samples_limit?: number; pro_samples_remaining?: number; drafts_used?: number; drafts_free_limit?: number; drafts_remaining?: number; daily_questions_cap?: number; daily_questions_left?: number; daily_voice_cap?: number; daily_voice_left?: number; terms_accepted?: boolean; terms_version?: string; terms_accepted_at?: string };
export type Language = { code: string; name: string; native: string; tts: string };
export type ModelChoice = { provider: string; name: string; label: string; recommended?: boolean };

type AuthCtx = {
  token: string | null;
  user: User | null;
  loading: boolean;
  language: Language;
  setLanguage: (l: Language) => Promise<void>;
  model: ModelChoice;
  setModel: (m: ModelChoice) => Promise<void>;
  autoSpeak: boolean;
  setAutoSpeak: (v: boolean) => Promise<void>;
  /** Playback loudness for spoken answers, 0.0–1.0. Persisted across sessions. */
  ttsVolume: number;
  setTtsVolume: (v: number) => Promise<void>;
  setUserState: (code: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string, phone: string, terms_accepted: boolean, terms_version: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hydrateSession: (token: string, user: User) => Promise<void>;
};

const DEFAULT_LANG: Language = { code: 'en', name: 'English', native: 'English', tts: 'en-IN' };
const DEFAULT_MODEL: ModelChoice = { provider: 'anthropic', name: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5', recommended: true };

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANG);
  const [model, setModelState] = useState<ModelChoice>(DEFAULT_MODEL);
  const [autoSpeak, setAutoSpeakState] = useState<boolean>(true);
  const [ttsVolume, setTtsVolumeState] = useState<number>(1.0);

  useEffect(() => {
    (async () => {
      const [t, u, l, m, a, v] = await Promise.all([
        AsyncStorage.getItem(TOKEN_KEY),
        AsyncStorage.getItem(USER_KEY),
        AsyncStorage.getItem(LANG_KEY),
        AsyncStorage.getItem(MODEL_KEY),
        AsyncStorage.getItem(AUTO_SPEAK_KEY),
        AsyncStorage.getItem(TTS_VOLUME_KEY),
      ]);
      if (t) setToken(t);
      if (u) setUser(JSON.parse(u));
      if (l) setLanguageState(JSON.parse(l));
      if (m) setModelState(JSON.parse(m));
      if (a !== null) setAutoSpeakState(a === '1');
      if (v !== null) {
        const n = parseFloat(v);
        if (!Number.isNaN(n)) setTtsVolumeState(Math.min(1, Math.max(0, n)));
      }
      setLoading(false);
    })();
  }, []);

  const persist = async (t: string, u: User) => {
    await AsyncStorage.setItem(TOKEN_KEY, t);
    await AsyncStorage.setItem(USER_KEY, JSON.stringify(u));
    setToken(t);
    setUser(u);
  };

  const login = async (email: string, password: string) => {
    const r = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || 'Login failed');
    const data = await r.json();
    await persist(data.token, data.user);
  };

  const register = async (email: string, password: string, name: string, phone: string, terms_accepted: boolean, terms_version: string) => {
    const r = await fetch(`${API}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name, phone, terms_accepted, terms_version }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || 'Register failed');
    const data = await r.json();
    await persist(data.token, data.user);
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const r = await fetch(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) {
        const u = await r.json();
        await AsyncStorage.setItem(USER_KEY, JSON.stringify(u));
        setUser(u);
      }
    } catch {}
  };

  const logout = async () => {
    await AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY]);
    setToken(null);
    setUser(null);
  };

  const setLanguage = useCallback(async (l: Language) => {
    setLanguageState(l);
    await AsyncStorage.setItem(LANG_KEY, JSON.stringify(l));
  }, []);

  const setModel = useCallback(async (m: ModelChoice) => {
    setModelState(m);
    await AsyncStorage.setItem(MODEL_KEY, JSON.stringify(m));
  }, []);

  const setAutoSpeak = useCallback(async (v: boolean) => {
    setAutoSpeakState(v);
    await AsyncStorage.setItem(AUTO_SPEAK_KEY, v ? '1' : '0');
  }, []);

  const setTtsVolume = useCallback(async (v: number) => {
    const clamped = Math.min(1, Math.max(0, v));
    setTtsVolumeState(clamped);
    await AsyncStorage.setItem(TTS_VOLUME_KEY, String(clamped));
  }, []);

  // Jurisdiction — state / UT decides rent, liquor, stamp duty and traffic fine
  // amounts, so the server needs it to serve the local rule with the answer.
  const setUserState = useCallback(async (code: string) => {
    if (!token) return;
    const r = await fetch(`${API}/api/auth/state`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ state: code }),
    });
    if (!r.ok) throw new Error('Could not save your state');
    const data = await r.json();
    setUser((prev) => {
      const next = prev ? { ...prev, state: data.state, state_name: data.state_name } : prev;
      if (next) AsyncStorage.setItem(USER_KEY, JSON.stringify(next));
      return next;
    });
  }, [token]);

  return (
    <Ctx.Provider value={{ token, user, loading, language, setLanguage, model, setModel, autoSpeak, setAutoSpeak, ttsVolume, setTtsVolume, setUserState, login, register, logout, refreshUser, hydrateSession: persist }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error('AuthProvider missing');
  return c;
}

export const API_BASE = API;
