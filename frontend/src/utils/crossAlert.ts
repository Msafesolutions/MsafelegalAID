import { Alert, Platform } from 'react-native';

export type CrossAlertButton = {
  text: string;
  onPress?: () => void;
  style?: 'default' | 'cancel' | 'destructive';
};

/**
 * Cross-platform replacement for `Alert.alert()`.
 *
 * react-native-web's `Alert.alert` only reliably renders a plain
 * `window.alert()` — multi-button confirm/cancel flows (delete
 * confirmations, "see Pro" prompts, etc.) silently show nothing or lose
 * their buttons/callbacks on web. This gives every call site identical
 * behaviour on native (real `Alert.alert`) and web (`window.confirm` /
 * `window.alert`), so a confirm-before-delete flow that works on Android
 * also works when the same code runs in a browser.
 *
 * Same call signature as `Alert.alert(title, message?, buttons?)` — a
 * drop-in replacement, not a new API to learn.
 */
export function crossAlert(title: string, message?: string, buttons?: CrossAlertButton[]) {
  if (Platform.OS !== 'web') {
    Alert.alert(title, message, buttons as any);
    return;
  }
  const text = [title, message].filter(Boolean).join('\n\n');
  if (!buttons || buttons.length <= 1) {
    if (typeof window !== 'undefined') window.alert(text);
    buttons?.[0]?.onPress?.();
    return;
  }
  const cancelBtn = buttons.find((b) => b.style === 'cancel');
  const primaryBtn = buttons.find((b) => b.style !== 'cancel') || buttons[buttons.length - 1];
  const confirmed = typeof window !== 'undefined' ? window.confirm(text) : false;
  if (confirmed) {
    primaryBtn?.onPress?.();
  } else {
    cancelBtn?.onPress?.();
  }
}
