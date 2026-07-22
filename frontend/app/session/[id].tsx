import { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as Speech from 'expo-speech';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';

type Msg = { id: string; role: string; content: string };
type Session = { id: string; title: string; language: string };

export default function SessionView() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { token, language } = useAuth();
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(true);
  const [speakingId, setSpeakingId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      if (!token || !id) return;
      try {
        const r = await fetch(`${API_BASE}/api/chat/sessions/${id}/messages`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await r.json();
        setSession(data.session);
        setMessages(data.messages);
      } catch {}
      finally { setLoading(false); }
    })();
    return () => { Speech.stop(); };
  }, [id, token]);

  const speak = useCallback((mid: string, text: string) => {
    if (speakingId === mid) { Speech.stop(); setSpeakingId(null); return; }
    Speech.stop();
    setSpeakingId(mid);
    Speech.speak(text, {
      language: language.tts,
      onDone: () => setSpeakingId(null),
      onStopped: () => setSpeakingId(null),
      onError: () => setSpeakingId(null),
    });
  }, [speakingId, language]);

  return (
    <SafeAreaView style={styles.safe} edges={['top']} testID="session-view">
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} testID="back-btn" hitSlop={10}>
          <Ionicons name="arrow-back" size={26} color={theme.colors.brand} />
        </Pressable>
        <Text style={styles.title} numberOfLines={1}>{session?.title || 'Conversation'}</Text>
        <View style={{ width: 26 }} />
      </View>
      {loading ? (
        <View style={styles.center}><ActivityIndicator color={theme.colors.brand} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {messages.map(m => (
            <View key={m.id} style={[styles.msg, m.role === 'user' ? styles.userMsg : styles.aiMsg]}>
              <View style={styles.msgHeader}>
                <Text style={[styles.msgRole, m.role === 'user' ? styles.userRole : styles.aiRole]}>
                  {m.role === 'user' ? 'You' : 'Dhara'}
                </Text>
                {m.role === 'assistant' && (
                  <Pressable onPress={() => speak(m.id, m.content)} hitSlop={10} testID={`speak-${m.id}`}>
                    <Ionicons name={speakingId === m.id ? 'stop-circle' : 'volume-high-outline'} size={22} color={theme.colors.brand} />
                  </Pressable>
                )}
              </View>
              <Text style={[styles.msgText, m.role === 'user' ? styles.userText : styles.aiText]}>{m.content}</Text>
            </View>
          ))}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.surface },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: theme.spacing.lg, borderBottomWidth: 1, borderBottomColor: theme.colors.divider },
  title: { flex: 1, textAlign: 'center', fontFamily: theme.fonts.display, fontSize: 17, color: theme.colors.brand, fontWeight: '700', marginHorizontal: theme.spacing.md },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { padding: theme.spacing.lg, paddingBottom: theme.spacing.xxl },
  msg: { marginBottom: theme.spacing.lg, borderRadius: theme.radius.lg, padding: theme.spacing.lg },
  userMsg: { backgroundColor: theme.colors.brand, alignSelf: 'flex-end', maxWidth: '90%', borderBottomRightRadius: 4 },
  aiMsg: { backgroundColor: theme.colors.surfaceSecondary, alignSelf: 'flex-start', maxWidth: '100%', borderBottomLeftRadius: 4, borderWidth: 1, borderColor: theme.colors.border },
  msgHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: theme.spacing.xs, alignItems: 'center' },
  msgRole: { fontSize: 12, fontWeight: '700' },
  userRole: { color: theme.colors.brandSecondary },
  aiRole: { color: theme.colors.brand },
  msgText: { fontSize: 15, lineHeight: 22 },
  userText: { color: theme.colors.onBrandPrimary },
  aiText: { color: theme.colors.onSurface },
});
