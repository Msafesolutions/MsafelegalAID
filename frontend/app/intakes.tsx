import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, Pressable, FlatList, StyleSheet, ActivityIndicator, Share, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import * as Clipboard from 'expo-clipboard';
import { Ionicons } from '@expo/vector-icons';
import { useAuth, API_BASE } from '@/src/auth';

const NAVY = '#14365A';
const GOLD = '#D3B675';

type Intake = {
  id: string;
  intake_token: string;
  intake_url: string;
  client_name: string;
  status: 'pending' | 'complete' | 'expired';
  created_at: string;
};

function StatusChip({ status }: { status: Intake['status'] }) {
  const map = {
    pending:  { bg: '#F3F4F6', text: '#6B7280', label: 'Pending' },
    complete: { bg: '#FEF9EC', text: NAVY,       label: 'Complete' },
    expired:  { bg: '#FEF2F2', text: '#DC2626',  label: 'Expired' },
  };
  const c = map[status];
  return (
    <View style={[ic.chip, { backgroundColor: c.bg }]}>
      <Text style={[ic.chipText, { color: c.text }]}>{c.label}</Text>
    </View>
  );
}

export default function Intakes() {
  const { token, user } = useAuth();
  const router = useRouter();
  const [intakes, setIntakes] = useState<Intake[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const loadIntakes = useCallback(async () => {
    if (!user?.id || !token) return;
    setLoading(true);
    const r = await fetch(`${API_BASE}/api/advocate/intakes/${user.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => null);
    if (r?.ok) setIntakes(await r.json());
    setLoading(false);
  }, [user?.id, token]);

  useEffect(() => { loadIntakes(); }, [loadIntakes]);

  const createIntake = async () => {
    if (!user?.id || !token) return;
    setCreating(true);
    try {
      const r = await fetch(`${API_BASE}/api/advocate/intake/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ advocate_id: user.id }),
      });
      if (!r.ok) throw new Error('Failed');
      const { intake_url } = await r.json();
      await loadIntakes();
      // Show share sheet
      if (Platform.OS !== 'web') {
        await Share.share({ message: `Use this link to share your situation with me securely:\n${intake_url}`, url: intake_url });
      } else {
        await Clipboard.setStringAsync(intake_url);
        alert(`Link copied!\n${intake_url}`);
      }
    } catch { /* silently handled */ }
    setCreating(false);
  };

  return (
    <SafeAreaView style={s.safe}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={{ marginRight: 12 }}>
          <Ionicons name="arrow-back" size={22} color="#fff" />
        </Pressable>
        <Text style={s.headerTitle}>Client Intakes</Text>
      </View>

      {loading ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator color={NAVY} />
        </View>
      ) : (
        <FlatList
          data={intakes}
          keyExtractor={item => item.id}
          contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
          ListEmptyComponent={
            <View style={s.empty}>
              <Ionicons name="people-outline" size={40} color="#D1D5DB" />
              <Text style={s.emptyTitle}>No intakes yet</Text>
              <Text style={s.emptySub}>Tap + to create a shareable intake link for a client.</Text>
            </View>
          }
          renderItem={({ item }) => (
            <Pressable
              style={s.row}
              onPress={() => item.status === 'complete' ? router.push(`/intake-view/${item.intake_token}` as any) : null}
            >
              <View style={{ flex: 1 }}>
                <Text style={s.rowName}>
                  {item.client_name || 'Awaiting client'}
                </Text>
                <Text style={s.rowDate}>{new Date(item.created_at).toLocaleDateString('en-IN')}</Text>
              </View>
              <StatusChip status={item.status} />
              {item.status === 'complete' && <Ionicons name="chevron-forward" size={16} color="#9CA3AF" style={{ marginLeft: 8 }} />}
            </Pressable>
          )}
        />
      )}

      {/* FAB */}
      <Pressable style={s.fab} onPress={createIntake} disabled={creating}>
        {creating ? <ActivityIndicator color="#fff" size="small" /> : <Ionicons name="add" size={28} color="#fff" />}
      </Pressable>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F9FAFB' },
  header: { backgroundColor: NAVY, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#fff', flex: 1 },
  row: { backgroundColor: '#fff', borderRadius: 12, padding: 14, marginBottom: 10, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#E5E7EB' },
  rowName: { fontSize: 15, fontWeight: '600', color: '#1F2937', marginBottom: 3 },
  rowDate: { fontSize: 12, color: '#9CA3AF' },
  empty: { alignItems: 'center', paddingTop: 60, gap: 8 },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: '#374151' },
  emptySub:   { fontSize: 13, color: '#9CA3AF', textAlign: 'center', maxWidth: 260 },
  fab: { position: 'absolute', bottom: 28, right: 20, width: 56, height: 56, borderRadius: 28, backgroundColor: GOLD, alignItems: 'center', justifyContent: 'center', elevation: 6, shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 6, shadowOffset: { width: 0, height: 3 } },
});

const ic = StyleSheet.create({
  chip: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  chipText: { fontSize: 12, fontWeight: '700' },
});
