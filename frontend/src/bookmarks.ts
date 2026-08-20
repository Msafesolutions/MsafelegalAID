/**
 * Saved answers ("bookmarks").
 *
 * Design rule: the DEVICE is the source of truth for reading. Everything is
 * written to AsyncStorage first so a saved answer opens instantly with no
 * network — the "standing in a police station with one bar of signal" case.
 * The server copy is only a sync target so the collection survives a reinstall
 * or a new phone.
 *
 * Each item carries a `client_id` generated on the device; the API is
 * idempotent on (user, client_id) so re-pushing a queue after being offline
 * never creates duplicates.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'dhara_bookmarks_v1';

export type SavedCitation = {
  key: string;
  citation: string;
  short_label: string;
  act: string;
  official_text: string;
  source_url: string;
  verified_at: string;
};

export type Bookmark = {
  client_id: string;
  question: string;
  answer: string;
  language: string;
  citations: SavedCitation[];
  created_at: string;
  /** false while the item still has to be pushed to the server */
  synced: boolean;
  /** local tombstone — removed from the list once the server confirms */
  pending_delete?: boolean;
};

async function write(items: Bookmark[]) {
  await AsyncStorage.setItem(KEY, JSON.stringify(items));
}

export async function loadLocal(): Promise<Bookmark[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const items: Bookmark[] = raw ? JSON.parse(raw) : [];
    return items.filter((i) => !i.pending_delete);
  } catch {
    return [];
  }
}

async function loadRaw(): Promise<Bookmark[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function isSaved(question: string, answer: string): Promise<boolean> {
  const items = await loadLocal();
  return items.some((i) => i.question === question && i.answer === answer);
}

export async function addBookmark(
  apiBase: string,
  token: string | null,
  b: Omit<Bookmark, 'client_id' | 'created_at' | 'synced'>,
): Promise<Bookmark[]> {
  const items = await loadRaw();
  const item: Bookmark = {
    ...b,
    client_id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    created_at: new Date().toISOString(),
    synced: false,
  };
  const next = [item, ...items];
  await write(next);
  // Fire-and-forget push; if it fails the item stays unsynced and the next
  // sync() attempt picks it up.
  if (token) {
    push(apiBase, token, item).catch(() => {});
  }
  return next.filter((i) => !i.pending_delete);
}

export async function removeBookmark(
  apiBase: string,
  token: string | null,
  clientId: string,
): Promise<Bookmark[]> {
  const items = await loadRaw();
  let next = items.map((i) =>
    i.client_id === clientId ? { ...i, pending_delete: true } : i,
  );
  if (token) {
    try {
      await fetch(`${apiBase}/api/bookmarks/${clientId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      next = next.filter((i) => i.client_id !== clientId);
    } catch {
      // stays as a local tombstone; sync() retries the delete
    }
  } else {
    next = next.filter((i) => i.client_id !== clientId);
  }
  await write(next);
  return next.filter((i) => !i.pending_delete);
}

async function push(apiBase: string, token: string, item: Bookmark) {
  const res = await fetch(`${apiBase}/api/bookmarks`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      client_id: item.client_id,
      question: item.question,
      answer: item.answer,
      language: item.language,
      citations: item.citations,
      created_at: item.created_at,
    }),
  });
  if (!res.ok) throw new Error('push failed');
  const items = await loadRaw();
  await write(items.map((i) => (i.client_id === item.client_id ? { ...i, synced: true } : i)));
}

/**
 * Two-way sync. Pushes local additions and deletions, then merges anything the
 * server has that this device does not (reinstall / second device). Silently
 * returns the local list if the network is unavailable — never throws.
 */
export async function syncBookmarks(apiBase: string, token: string | null): Promise<Bookmark[]> {
  if (!token) return loadLocal();
  let items = await loadRaw();
  // 1. deletions first so a tombstoned item is not resurrected by the pull
  for (const t of items.filter((i) => i.pending_delete)) {
    try {
      await fetch(`${apiBase}/api/bookmarks/${t.client_id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      items = items.filter((i) => i.client_id !== t.client_id);
    } catch {
      return items.filter((i) => !i.pending_delete);
    }
  }
  await write(items);
  // 2. push unsynced additions
  for (const u of items.filter((i) => !i.synced)) {
    try {
      await push(apiBase, token, u);
    } catch {
      return (await loadRaw()).filter((i) => !i.pending_delete);
    }
  }
  // 3. pull and merge
  try {
    const res = await fetch(`${apiBase}/api/bookmarks`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('pull failed');
    const remote: any[] = await res.json();
    const local = await loadRaw();
    const known = new Set(local.map((i) => i.client_id));
    const added: Bookmark[] = remote
      .filter((r) => r.client_id && !known.has(r.client_id))
      .map((r) => ({
        client_id: r.client_id,
        question: r.question || '',
        answer: r.answer || '',
        language: r.language || 'en',
        citations: r.citations || [],
        created_at: r.created_at || new Date().toISOString(),
        synced: true,
      }));
    const merged = [...local, ...added]
      .filter((i) => !i.pending_delete)
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
    await write(merged);
    return merged;
  } catch {
    return (await loadRaw()).filter((i) => !i.pending_delete);
  }
}
