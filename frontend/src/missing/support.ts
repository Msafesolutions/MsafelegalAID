import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { API_BASE } from '../auth';

export type MissingLocation = { latitude: number; longitude: number; accuracy?: number; source: 'gps' | 'manual' };
export type MissingSupport = { draftId: string; location?: MissingLocation; photosAttached?: boolean };
export type MissingPhoto = { file_id: string; filename: string; size: number };
export const answersKey = (userId: string) => `missing_answers_${userId}`;
const supportKey = (userId: string) => `missing_support_${userId}`;
export const mapUrl = (location: MissingLocation) => `https://www.google.com/maps/search/?api=1&query=${location.latitude},${location.longitude}`;

export async function loadSupport(userId: string): Promise<MissingSupport> {
  const raw = await AsyncStorage.getItem(supportKey(userId));
  if (raw) return JSON.parse(raw);
  const support = { draftId: `missing-${Date.now()}-${Math.random().toString(36).slice(2, 12)}` };
  await saveSupport(userId, support);
  return support;
}
export const saveSupport = (userId: string, data: MissingSupport) => AsyncStorage.setItem(supportKey(userId), JSON.stringify(data));
export const clearSupport = (userId: string) => AsyncStorage.multiRemove([supportKey(userId), answersKey(userId)]);
export const photoUrl = (draftId: string, id?: string) => `${API_BASE}/api/missing/${draftId}/photos${id ? '/' + id : ''}`;
export async function photoRequest(draftId: string, token: string, id?: string, init?: RequestInit) {
  const response = await fetch(photoUrl(draftId, id), { ...init, headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Could not load photos. Please try again.');
  }
  return response;
}

// Temporary in-memory representation for PDF rendering, never persisted as base64.
export async function photoForPdf(draftId: string, photo: MissingPhoto, token: string): Promise<string> {
  if (Platform.OS === 'web') {
    const blob = await (await photoRequest(draftId, token, photo.file_id)).blob();
    return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = reject; reader.readAsDataURL(blob); });
  }
  const fs = await import('expo-file-system/legacy');
  const uri = `${fs.cacheDirectory}missing-${photo.file_id}.jpg`;
  try {
    const result = await fs.downloadAsync(photoUrl(draftId, photo.file_id), uri, { headers: { Authorization: `Bearer ${token}` } });
    if (result.status !== 200) throw new Error('A photo could not be loaded. Please retry.');
    return 'data:image/jpeg;base64,' + await fs.readAsStringAsync(uri, { encoding: fs.EncodingType.Base64 });
  } finally { await fs.deleteAsync(uri, { idempotent: true }).catch(() => {}); }
}