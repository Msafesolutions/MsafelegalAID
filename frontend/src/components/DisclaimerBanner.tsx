import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '@/src/theme';

/**
 * Non-dismissible legal disclaimer banner.
 * Rendered globally above the tab bar via (tabs)/_layout.tsx.
 * Wording is FIXED — do not change without legal review.
 */
export const DISCLAIMER_TEXT =
  'DHARA provides legal information, not legal advice. This does not create an advocate-client relationship. Verify with a qualified advocate before acting. © Callistus Moses · MSafe Solutions.';

export function DisclaimerBanner({ testID = 'global-disclaimer' }: { testID?: string }) {
  return (
    <View style={styles.wrap} testID={testID}>
      <Ionicons name="shield-half" size={14} color={theme.colors.brand} style={{ marginTop: 1 }} />
      <Text style={styles.text} numberOfLines={4}>
        {DISCLAIMER_TEXT}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 6,
    backgroundColor: '#FFF6E5',
    borderTopWidth: 1,
    borderTopColor: '#F0D68A',
    borderBottomWidth: 1,
    borderBottomColor: '#F0D68A',
  },
  text: {
    flex: 1,
    color: '#5A3A00',
    fontSize: 10,
    lineHeight: 13,
    fontWeight: '500',
  },
});
