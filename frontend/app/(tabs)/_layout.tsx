import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { View, Platform } from 'react-native';
import { useEffect } from 'react';
import { theme } from '@/src/theme';
import { DisclaimerBanner } from '@/src/components/DisclaimerBanner';
import { useAuth } from '@/src/auth';
import { addNotificationTapListener } from '@/src/push';

/**
 * Tab layout with a non-dismissible global legal disclaimer banner
 * pinned just above the tab bar. It appears on ALL tabs.
 *
 * Also owns the auth guard: whenever `token` becomes null (e.g. user tapped
 * Sign Out on Settings), we force-redirect to /login. Without this guard the
 * tabs stay mounted after logout and the user appears stuck on the settings
 * page — which was the root cause of the reported "Sign out doesn't work" bug.
 */
export default function TabsLayout() {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!token) {
      router.replace('/login');
    }
  }, [token, loading, router]);

  // Tapping a push notification (e.g. the daily nudge, or a dead-law
  // bookmark alert) routes straight to the relevant screen. Native only —
  // expo-notifications' tap events aren't applicable on web.
  useEffect(() => {
    if (Platform.OS === 'web' || !token) return undefined;
    const sub = addNotificationTapListener((actionUrl) => {
      if (actionUrl) router.push(actionUrl as any);
    });
    return () => sub.remove();
  }, [token, router]);

  // Don't render tabs at all while unauthenticated — prevents a flash of the
  // settings screen after logout while the redirect is in flight.
  if (!token) return null;

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.surface }}>
      <View style={{ flex: 1 }}>
        <Tabs
          screenOptions={{
            headerShown: false,
            tabBarActiveTintColor: theme.colors.brand,
            tabBarInactiveTintColor: theme.colors.onSurfaceTertiary,
            tabBarStyle: {
              backgroundColor: theme.colors.surface,
              borderTopColor: theme.colors.divider,
              height: 64,
              paddingBottom: 8,
              paddingTop: 8,
            },
            tabBarLabelStyle: { fontWeight: '600', fontSize: 11 },
          }}
        >
          <Tabs.Screen
            name="index"
            options={{
              title: 'Ask',
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="chatbubbles-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-chat',
            }}
          />
          <Tabs.Screen
            name="rights"
            options={{
              title: 'Rights',
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="shield-checkmark-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-rights',
            }}
          />
          <Tabs.Screen
            name="saved"
            options={{
              title: 'Saved',
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="bookmark-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-saved',
            }}
          />
          <Tabs.Screen
            name="history"
            options={{
              title: 'History',
              tabBarButton: () => null, // hidden from tab bar; accessible via header icon
            }}
          />
          <Tabs.Screen
            name="lookup"
            options={{
              title: 'Lookup',
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="search-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-lookup',
            }}
          />
          <Tabs.Screen
            name="settings"
            options={{
              title: 'Settings',
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="settings-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-settings',
            }}
          />
        </Tabs>
      </View>
      {/* Non-dismissible legal disclaimer — appears on every tab, above tab bar. */}
      <DisclaimerBanner />
    </View>
  );
}
