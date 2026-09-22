import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '@/src/theme';
import { useAuth } from '@/src/auth';
import { t } from '@/src/i18n';

/**
 * Non-dismissible legal disclaimer banner — localized.
 * Rendered globally above the tab bar via (tabs)/_layout.tsx.
 */
export const DISCLAIMER_TEXT =
  'DHARA provides legal information, not legal advice. This does not create an advocate-client relationship. Verify with a qualified advocate before acting. © Callistus Moses · MSafe Solutions.';

export function DisclaimerBanner({ testID = 'global-disclaimer' }: { testID?: string }) {
  const { language } = useAuth();
  const text = t('disclaimer', language.code);
  return (
    <View style={styles.wrap} testID={testID}>
      <Ionicons name="shield-half" size={14} color={theme.colors.brand} style={{ marginTop: 1 }} />
      <Text style={styles.text} numberOfLines={4}>
        {text}
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
    // dhara.textSecondary (#4A5A6E) on amber bg (#FFF6E5) = 6.60:1 ✅ WCAG AA
    // Legal text: 12px minimum — not fine-print size — this copy has legal function.
    color: theme.dhara.textSecondary,
    fontSize: 12,
    lineHeight: 17,
    fontWeight: '500',
  },
});
