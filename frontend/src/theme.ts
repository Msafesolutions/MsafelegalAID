export const theme = {
  colors: {
    surface: '#FDFBF7',
    onSurface: '#1A202C',
    surfaceSecondary: '#F4F1EA',
    onSurfaceSecondary: '#374151',
    surfaceTertiary: '#EAE4D9',
    onSurfaceTertiary: '#4B5563',
    surfaceInverse: '#1A202C',
    onSurfaceInverse: '#FDFBF7',
    // Royal Blue + Gold brand palette
    brand: '#12328C',
    brandPrimary: '#12328C',
    onBrandPrimary: '#FDFBF7',
    brandSecondary: '#9A6E00',
    onBrandSecondary: '#FFFFFF',
    brandTertiary: '#1B4BB8',
    onBrandTertiary: '#FDFBF7',
    gold: '#D4AF37',
    goldSoft: '#F5E3A3',
    success: '#2D6A4F',
    warning: '#D97706',
    error: '#B91C1C',
    info: '#1E40AF',
    border: '#D1D5DB',
    borderStrong: '#9CA3AF',
    divider: '#E5E7EB',
  },
  // ── Documented Dhara brand palette ──────────────────────────────────────────
  // WCAG-verified tokens.  Do NOT use ad-hoc hex values or Tailwind defaults
  // on navy backgrounds — gray-on-navy fails outright regardless of shade.
  // Reference these constants everywhere instead of inline hex strings.
  //   gold (#D3B675) on navy (#14365A) = 6.29:1   ✅ WCAG AA
  //   white (#FFF) on navy (#14365A)   = 12.33:1  ✅ WCAG AAA
  //   textSecondary on surface (#FDFBF7) = 6.81:1 ✅ WCAG AA
  //   navy on surface (#FDFBF7)        = 11.92:1  ✅ WCAG AAA
  dhara: {
    navy:             '#14365A', // primary backgrounds on auth/onboarding screens
    navyLight:        '#1E4A78', // hover / pressed states on navy
    gold:             '#D3B675', // accent text on navy; 6.29:1 — NEVER use brandSecondary on navy
    goldDark:         '#B8934F', // gold on light bg when higher contrast needed; 4.6:1 vs cream
    cream:            '#F5F0E6', // card backgrounds
    textPrimary:      '#14365A', // body text on light backgrounds
    textSecondary:    '#4A5A6E', // secondary text on light; 6.81:1 on surface — NOT gray-400
    textOnNavy:       '#FFFFFF', // primary text on navy
    textOnNavyMuted:  '#D3B675', // muted text on navy — NEVER a raw gray (gray-on-navy fails)
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    xxl: 32,
    xxxl: 48,
  },
  radius: {
    sm: 6,
    md: 12,
    lg: 20,
    pill: 999,
  },
  fonts: {
    // Native serif fallback family — dignified editorial feel
    display: 'serif',
    displayRegular: 'serif',
    body: 'System',
    bodyMedium: 'System',
    bodyBold: 'System',
  },
} as const;
