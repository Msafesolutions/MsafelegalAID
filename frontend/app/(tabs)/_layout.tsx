import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { View, Platform, StyleSheet, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { PlatformPressable } from '@react-navigation/elements';
import { useEffect } from 'react';
import { theme } from '@/src/theme';
import { AppTabBar } from '@/src/components/AppTabBar';
import { useAuth } from '@/src/auth';
import { addNotificationTapListener } from '@/src/push';
import { t } from '@/src/i18n';

/**
 * Tab layout with a non-dismissible global legal disclaimer banner
 * below the tab bar. The outer safe area protects both on ALL tabs.
 *
 * Also owns the auth guard: whenever `token` becomes null (e.g. user tapped
 * Sign Out on Settings), we force-redirect to /login. Without this guard the
 * tabs stay mounted after logout and the user appears stuck on the settings
 * page — which was the root cause of the reported "Sign out doesn't work" bug.
 */
export default function TabsLayout() {
  const { token, loading, language } = useAuth();
  const router = useRouter();
  const { fontScale } = useWindowDimensions();

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
    <SafeAreaView style={styles.root} edges={['bottom']} testID="tabs-layout">
      <View style={styles.content}>
        <Tabs
          initialRouteName="home"
          tabBar={props => <AppTabBar {...props} />}
          safeAreaInsets={{ bottom: 0 }}
          screenOptions={{
            headerShown: false,
            tabBarActiveTintColor: theme.colors.primaryMid,
            tabBarInactiveTintColor: theme.colors.onSurfaceTertiary,
            // Icon (28), label (16+), item padding (10), bar padding (16).
            // The old 64pt bar left just 47pt and clipped the label's baseline.
            tabBarStyle: [styles.tabBar, { height: 60 + Math.ceil(16 * Math.max(1, fontScale)) }],
            tabBarLabelPosition: 'below-icon',
            tabBarLabelStyle: styles.tabLabel,
            tabBarIconStyle: styles.tabIcon,
            tabBarItemStyle: styles.tabItem,
            tabBarButton: props => <PlatformPressable {...props} style={[props.style, styles.tabButton]} />,
          }}
        >
          <Tabs.Screen name="home" options={{ title: 'Home' }} />
          <Tabs.Screen name="complaints" options={{ title: 'Complaints' }} />
          <Tabs.Screen name="discover" options={{ title: 'Lookup' }} />
          <Tabs.Screen
            name="index"
            options={{
              title: t('tab.ask', language.code),
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="chatbubbles-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-chat',
            }}
          />
          <Tabs.Screen
            name="rights"
            options={{
              title: t('tab.rights', language.code),
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="shield-checkmark-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-rights',
            }}
          />
          <Tabs.Screen
            name="voter-roll"
            options={{
              title: t('tab.vote', language.code),
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="checkbox-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-vote',
            }}
          />
          <Tabs.Screen
            name="saved"
            options={{
              title: t('tab.saved', language.code),
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
              href: null, // No empty seventh slot; still reachable via header icon.
            }}
          />
          <Tabs.Screen
            name="lookup"
            options={{
              title: t('tab.lookup', language.code),
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="search-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-lookup',
            }}
          />
          <Tabs.Screen
            name="advocate"
            options={{
              title: t('tab.advocate', language.code),
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="briefcase-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-advocate',
            }}
          />
          <Tabs.Screen
            name="settings"
            options={{
              title: t('tab.settings', language.code),
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="settings-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-settings',
            }}
          />
        </Tabs>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.colors.surface },
  content: { flex: 1, minHeight: 0 },
  tabBar: {
    backgroundColor: theme.colors.surface,
    borderTopColor: theme.colors.divider,
    paddingTop: 8,
    paddingBottom: 8,
    flexShrink: 0,
  },
  tabItem: { minHeight: 52, minWidth: 0 },
  tabButton: { paddingHorizontal: 1 },
  tabIcon: { width: 32, height: 28, flexShrink: 0 },
  tabLabel: { fontWeight: '600', fontSize: 11, lineHeight: 16, flexShrink: 0 },
  // ── Ask AI FAB ─────────────────────────────────────────────────────────────
  fabContainer: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 100,
  },
  fab: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: theme.colors.gold,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 1,
    borderWidth: 3,
    borderColor: theme.colors.surface,
    ...Platform.select({
      ios: {
        shadowColor: theme.colors.shadow,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.45,
        shadowRadius: 8,
      },
      android: { elevation: 10 },
    }),
  },
  fabPressed: {
    backgroundColor: theme.colors.accentDark,
  },
  fabLabel: {
    fontSize: 9,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: 0.4,
  },
});
