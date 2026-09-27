import { Stack } from 'expo-router';
import { theme } from '@/src/theme';

export default function VisitorLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: theme.colors.primary },
        headerTintColor: '#fff',
        headerTitleStyle: { fontWeight: '700' },
        headerBackTitle: 'Back',
      }}
    >
      <Stack.Screen name="index"        options={{ title: 'Visitor Mode' }} />
      <Stack.Screen name="intent"       options={{ title: 'How Can We Help?' }} />
      <Stack.Screen name="emergency"    options={{ title: 'Emergency Help' }} />
      <Stack.Screen name="lost-passport" options={{ title: 'Lost Passport' }} />
    </Stack>
  );
}
