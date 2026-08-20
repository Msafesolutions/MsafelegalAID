/**
 * Draft history — every notice a user creates is kept on the device so it can
 * be reopened, copied and re-sent later without spending another draft from the
 * quota (regenerating from history never calls /api/drafts/consume).
 *
 * Device-only by design: a legal notice contains names, addresses and amounts,
 * and there is no product reason to keep that on the server.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'dhara_draft_history_v1';
const MAX = 25;

export type DraftHistoryItem = {
  id: string;
  type: string;
  title: string;
  text: string;
  lang: 'en' | 'hi';
  created_at: string;
};

export async function loadHistory(): Promise<DraftHistoryItem[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function addToHistory(
  item: Omit<DraftHistoryItem, 'id' | 'created_at'>,
): Promise<DraftHistoryItem[]> {
  const items = await loadHistory();
  const next = [
    { ...item, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, created_at: new Date().toISOString() },
    ...items,
  ].slice(0, MAX);
  await AsyncStorage.setItem(KEY, JSON.stringify(next));
  return next;
}

export async function removeFromHistory(id: string): Promise<DraftHistoryItem[]> {
  const items = (await loadHistory()).filter((i) => i.id !== id);
  await AsyncStorage.setItem(KEY, JSON.stringify(items));
  return items;
}

export async function findInHistory(id: string): Promise<DraftHistoryItem | undefined> {
  return (await loadHistory()).find((i) => i.id === id);
}
