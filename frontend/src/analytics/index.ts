/**
 * DHARA Three-Layer Analytics
 *
 * Sinks:
 *   1. PostHog EU  — cross-platform (native + web)
 *   2. GA4 gtag.js — web-only (injected in +html.tsx)
 *   3. Cloudflare  — web-only (script tag in +html.tsx; fires automatically)
 *
 * DPDP Act 2023 compliance:
 *   - No raw PII (name / phone / email / Aadhaar) in any event
 *   - User IDs SHA-256 hashed before identify() calls
 *   - maskAllInputs enforced in PostHog session replay config
 *   - Only behavioural properties sent (screen, tap type, lengths)
 */

import { Platform } from 'react-native';
import * as Crypto from 'expo-crypto';
import type PostHogType from 'posthog-react-native';

// ── PostHog constants ─────────────────────────────────────────────────────
export const POSTHOG_API_KEY = 'phc_sRQRpeBn6TEPHJmZ7DfDxLVP68yExZv3UUMQckBcxAGD';
export const POSTHOG_OPTIONS = {
  host: 'https://eu.i.posthog.com',
  // Disable auto-pageview here; we fire screen_view manually via the
  // AnalyticsNavigationTracker hook so we can attach the language prop.
  capturePageview: false,
  // Session replay masking — ensures no form field values are recorded.
  sessionReplay: {
    maskAllInputs: true,
    maskAllTextInputs: true,
  },
} as const;

// ── Lazy singleton ─────────────────────────────────────────────────────────
// Using a lazy singleton avoids import-time initialisation and ensures the
// PostHogProvider (which calls new PostHog()) is always in charge on native.
let _posthog: PostHogType | null = null;

export function setPostHogInstance(instance: PostHogType): void {
  _posthog = instance;
}

function ph(): PostHogType | null {
  return _posthog;
}

// ── DPDP helper: SHA-256 hash ────────────────────────────────────────────
/**
 * Returns a lowercase hex SHA-256 digest of the input string.
 * Used to pseudonymise user IDs before they reach any analytics sink.
 * Falls back to a simple FNV-1a hash if Crypto is unavailable.
 */
export async function hashId(raw: string): Promise<string> {
  try {
    return await Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA256,
      raw,
      { encoding: Crypto.CryptoEncoding.HEX },
    );
  } catch {
    // Fallback: deterministic but NOT cryptographically strong — only used
    // if expo-crypto fails (e.g. extreme OEM restriction).
    let h = 0x811c9dc5;
    for (let i = 0; i < raw.length; i++) {
      h ^= raw.charCodeAt(i);
      h = (h * 0x01000193) >>> 0;
    }
    return h.toString(16).padStart(8, '0');
  }
}

// ── GA4 helper (web only) ─────────────────────────────────────────────────
function ga4(eventName: string, params?: Record<string, unknown>): void {
  if (Platform.OS !== 'web') return;
  try {
    const gtag = (globalThis as any).gtag;
    if (typeof gtag === 'function') {
      gtag('event', eventName, params ?? {});
    }
  } catch {}
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Fire a named event to PostHog (all platforms) + GA4 (web only).
 * Properties must NEVER contain raw PII. Pass lengths, booleans, and codes.
 */
export function trackEvent(
  eventName: string,
  properties?: Record<string, unknown>,
): void {
  // PostHog
  try {
    ph()?.capture(eventName, properties);
  } catch {}
  // GA4 web
  ga4(eventName, properties);
}

/**
 * Associate the current device with a pseudonymous user ID.
 * The raw userId is SHA-256 hashed before it leaves the device.
 */
export async function identifyUser(
  userId: string,
  traits?: Record<string, unknown>,
): Promise<void> {
  const hashedId = await hashId(userId);
  try {
    ph()?.identify(hashedId, traits);
  } catch {}
  // GA4: set hashed user_id
  if (Platform.OS === 'web') {
    try {
      const gtag = (globalThis as any).gtag;
      if (typeof gtag === 'function') {
        gtag('set', { user_id: hashedId });
      }
    } catch {}
  }
}

/**
 * Reset analytics identity on logout.
 * Clears the PostHog distinct ID so future events are anonymous again.
 */
export function resetAnalyticsIdentity(): void {
  try {
    ph()?.reset();
  } catch {}
  // GA4: clear user_id
  if (Platform.OS === 'web') {
    try {
      const gtag = (globalThis as any).gtag;
      if (typeof gtag === 'function') {
        gtag('set', { user_id: undefined });
      }
    } catch {}
  }
}
