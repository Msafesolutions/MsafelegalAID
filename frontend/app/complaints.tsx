import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { ComplaintsList } from '@/src/home/ComplaintsList';
import { theme } from '@/src/theme';

const colors = theme.colors;
export default function Complaints() {
  const router = useRouter();
  return <SafeAreaView style={styles.safe} testID="complaints-screen">
    <View style={styles.header}>
      <Pressable testID="complaints-back" accessibilityRole="button" accessibilityLabel="Back to Home" style={styles.icon} onPress={() => router.canGoBack() ? router.back() : router.replace('/(tabs)/home')}><Ionicons name="arrow-back" size={24} color={colors.primary} /></Pressable>
      <Text testID="complaints-title" style={styles.title}>Your complaints</Text>
      <Pressable testID="complaints-create" accessibilityRole="button" accessibilityLabel="Start a complaint" style={styles.icon} onPress={() => router.push('/fir-draft')}><Ionicons name="add" size={26} color={colors.primary} /></Pressable>
    </View>
    <ScrollView contentContainerStyle={styles.content}><ComplaintsList all /></ScrollView>
  </SafeAreaView>;
}
const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: 'row', alignItems: 'center', padding: 12, gap: 8, backgroundColor: colors.surface },
  icon: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  title: { flex: 1, fontSize: 22, fontWeight: '700', color: colors.primary },
  content: { padding: 18, paddingBottom: 32 },
});