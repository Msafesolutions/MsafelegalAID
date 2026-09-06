/**
 * Emergent-managed push notifications (SuprSend relay) — client side.
 *
 * Registration is USER-INITIATED ONLY (Settings -> "Push notifications"
 * toggle). We never request the OS permission on cold start - see
 * <handle_permissions_contract>: ask contextually, after clear intent, and
 * never dead-end the user if they decline.
 *
 * Uses the NATIVE device push token (getDevicePushTokenAsync), not Expo's
 * own push-token abstraction - the SuprSend relay talks to FCM/APNs
 * directly, which is exactly why an Android build needs a real
 * google-services.json before this can work on a device.
 */
import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { API_BASE } from '@/src/auth';

export type PushPermissionState = 'granted' | 'denied' | 'undetermined' | 'unsupported';

// Foreground behaviour: show banners even while the app is open.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function getPushPermissionState(): Promise<PushPermissionState> {
  if (Platform.OS === 'web') return 'unsupported';
  const { status } = await Notifications.getPermissionsAsync();
  return status as PushPermissionState;
}

/**
 * Call this ONLY from a direct user action (e.g. tapping the Settings
 * toggle). Requests the OS permission if needed, then registers the native
 * device token with our backend for this user. Returns the resulting
 * permission info so the caller can render every state correctly
 * (granted / denied-but-askable / permanently-blocked).
 */
export async function enablePushNotifications(
  token: string,
  userId: string,
): Promise<{ granted: boolean; canAskAgain: boolean }> {
  if (Platform.OS === 'web') return { granted: false, canAskAgain: false };

  let perm = await Notifications.getPermissionsAsync();
  if (perm.status !== 'granted') {
    if (perm.status === 'denied' && !perm.canAskAgain) {
      return { granted: false, canAskAgain: false };
    }
    perm = await Notifications.requestPermissionsAsync();
  }
  if (perm.status !== 'granted') {
    return { granted: false, canAskAgain: !!perm.canAskAgain };
  }

  try {
    const devicePushToken = await Notifications.getDevicePushTokenAsync();
    await fetch(`${API_BASE}/api/register-push`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        user_id: userId,
        platform: Platform.OS,
        device_token: devicePushToken.data,
      }),
    });
  } catch {
    // Registration hiccup shouldn't block the rest of the app - the OS
    // permission is still granted; the user can just try the toggle again.
  }
  return { granted: true, canAskAgain: true };
}

/** Fires when the user taps a notification (foreground, background, or cold
 * start via getLastNotificationResponseAsync - call sites handle that). */
export function addNotificationTapListener(onTap: (actionUrl: string | null) => void) {
  return Notifications.addNotificationResponseReceivedListener((response) => {
    const url = (response.notification.request.content.data as any)?.action_url ?? null;
    onTap(url);
  });
}
