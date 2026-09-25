import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { theme } from '../theme';
import { DisclaimerBanner } from './DisclaimerBanner';

const colors = theme.colors;
const TABS = [
  { name: 'home',        label: 'Home',     icon: 'home-outline',         activeIcon: 'home',          testID: 'tab-home' },
  { name: 'rights',      label: 'Rights',   icon: 'shield-outline',       activeIcon: 'shield',        testID: 'tab-rights' },
  { name: 'voter-roll',  label: 'Vote',     icon: 'checkbox-outline',     activeIcon: 'checkbox',      testID: 'tab-vote' },
  { name: 'index',       label: 'Ask AI',   icon: 'chatbubble-outline',   activeIcon: 'chatbubble-outline', testID: 'tab-chat' },
  { name: 'advocate',    label: 'Advocate', icon: 'briefcase-outline',    activeIcon: 'briefcase',     testID: 'tab-advocate' },
  { name: 'settings',    label: 'Profile',  icon: 'person-outline',       activeIcon: 'person',        testID: 'tab-settings' },
] as const;

export function AppTabBar({ state, navigation }: BottomTabBarProps) {
  return <View testID="app-bottom-navigation" style={styles.wrap}>
    {state.routes[state.index].name !== 'home' && <DisclaimerBanner />}
    <View style={styles.tabs}>
      {TABS.map(tab => {
        const route = state.routes.find(r => r.name === tab.name);
        if (!route) return null;
        const focused = state.routes[state.index].key === route.key;
        const ask = tab.name === 'index';
        return <Pressable key={tab.name} testID={tab.testID} accessibilityRole="tab" aria-selected={focused} accessibilityState={{ selected: focused }} accessibilityLabel={tab.label}
          style={({ pressed }) => [styles.tab, pressed && styles.pressed]}
          onPress={() => {
            const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
            if (!focused && !event.defaultPrevented) navigation.navigate(route.name, route.params);
          }} onLongPress={() => navigation.emit({ type: 'tabLongPress', target: route.key })}>
          <View testID={ask ? 'ask-ai-fab' : undefined} style={ask ? styles.askCircle : styles.icon}>
            <Ionicons name={focused ? tab.activeIcon : tab.icon} size={ask ? 26 : 22} color={ask ? colors.onGold : focused ? colors.primary : colors.onSurfaceTertiary} />
          </View>
          <Text style={[styles.label, focused && styles.activeLabel]}>{tab.label}</Text>
        </Pressable>;
      })}
    </View>
  </View>;
}
const styles = StyleSheet.create({
  wrap: { backgroundColor: colors.surface, flexShrink: 0 },
  tabs: { flexDirection: 'row', alignItems: 'flex-end', paddingHorizontal: 4, paddingTop: 6, paddingBottom: 10, borderTopWidth: 1, borderColor: colors.divider },
  tab: { flex: 1, minHeight: 58, justifyContent: 'flex-end', alignItems: 'center', gap: 5, paddingHorizontal: 2 },
  icon: { minHeight: 30, alignItems: 'center', justifyContent: 'center' },
  askCircle: { width: 54, height: 54, borderRadius: 27, backgroundColor: colors.gold, borderWidth: 3, borderColor: colors.surface, alignItems: 'center', justifyContent: 'center', marginTop: -16 },
  label: { color: colors.onSurfaceTertiary, fontSize: 10, lineHeight: 15, fontWeight: '500', textAlign: 'center' },
  activeLabel: { color: colors.primary, fontWeight: '800' },
  pressed: { opacity: 0.65 },
});