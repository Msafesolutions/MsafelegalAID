import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { View } from 'react-native';
import { theme } from '@/src/theme';
import { DisclaimerBanner } from '@/src/components/DisclaimerBanner';

/**
 * Tab layout with a non-dismissible global legal disclaimer banner
 * pinned just above the tab bar. It appears on ALL tabs.
 */
export default function TabsLayout() {
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
            name="history"
            options={{
              title: 'History',
              tabBarIcon: ({ color, size }) => (
                <Ionicons name="time-outline" size={size} color={color} />
              ),
              tabBarButtonTestID: 'tab-history',
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
