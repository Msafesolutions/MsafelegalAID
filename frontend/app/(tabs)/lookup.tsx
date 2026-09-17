/**
 * Dhara Lookup — eCourts case search tab.
 *
 * Two search modes:
 *  1. By CNR  — 16-character Case Number Record (e.g. DLHC010001232024)
 *  2. By Party — litigant / party name (phrase search)
 *
 * All calls are proxied through /api/cases/* so the bearer token
 * never leaves the backend.
 */
import React, { useState, useCallback, useRef } from 'react';
import {
  View, Text, TextInput, ScrollView, Pressable,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';

// ─── Types ────────────────────────────────────────────────────────────────────

type CaseResult = {
  cnr: string | null;
  case_status: string | null;
  next_hearing_date: string | null;
  court_name: string | null;
  district: string | null;
  state: string | null;
  case_type: string | null;
  filing_date: string | null;
  petitioners: string[];
  respondents: string[];
};

type Mode = 'cnr' | 'party';

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Soft-format a CNR as the user types: uppercase, max 16 chars. */
const formatCNR = (raw: string) => raw.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 16);

const CNR_HINT_COLOR = '#9CA3AF';

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return null;
  const disposed = /dispos|closed|decided/i.test(status);
  return (
    <View style={[styles.badge, disposed ? styles.badgeDisposed : styles.badgePending]}>
      <Text style={[styles.badgeText, disposed ? styles.badgeTextDisposed : styles.badgeTextPending]}>
        {status}
      </Text>
    </View>
  );
}

function CaseCard({ item }: { item: CaseResult }) {
  const [expanded, setExpanded] = useState(false);
  const petitioner  = Array.isArray(item.petitioners) ? item.petitioners[0] : null;
  const respondent  = Array.isArray(item.respondents) ? item.respondents[0] : null;

  return (
    <Pressable style={styles.card} onPress={() => setExpanded((v) => !v)} testID={`case-card-${item.cnr}`}>
      {/* Row 1: CNR + status */}
      <View style={styles.cardTop}>
        <View style={styles.cnrRow}>
          <Ionicons name="document-text-outline" size={15} color={theme.colors.brand} />
          <Text style={styles.cnr} selectable>{item.cnr ?? '—'}</Text>
        </View>
        <StatusBadge status={item.case_status} />
      </View>

      {/* Row 2: court + district */}
      {(item.court_name || item.district) ? (
        <Text style={styles.court} numberOfLines={1}>
          {[item.court_name, item.district, item.state].filter(Boolean).join(' · ')}
        </Text>
      ) : null}

      {/* Row 3: next hearing */}
      {item.next_hearing_date ? (
        <View style={styles.hearingRow}>
          <Ionicons name="calendar-outline" size={13} color={theme.colors.brandSecondary} />
          <Text style={styles.hearingText}>Next hearing: {item.next_hearing_date}</Text>
        </View>
      ) : null}

      {/* Expanded: parties + filing info */}
      {expanded && (
        <View style={styles.expandedWrap}>
          {petitioner ? (
            <View style={styles.partyRow}>
              <Text style={styles.partyLabel}>Petitioner</Text>
              <Text style={styles.partyValue}>{petitioner}</Text>
            </View>
          ) : null}
          {respondent ? (
            <View style={styles.partyRow}>
              <Text style={styles.partyLabel}>Respondent</Text>
              <Text style={styles.partyValue}>{respondent}</Text>
            </View>
          ) : null}
          {item.case_type ? (
            <View style={styles.partyRow}>
              <Text style={styles.partyLabel}>Case type</Text>
              <Text style={styles.partyValue}>{item.case_type}</Text>
            </View>
          ) : null}
          {item.filing_date ? (
            <View style={styles.partyRow}>
              <Text style={styles.partyLabel}>Filed on</Text>
              <Text style={styles.partyValue}>{item.filing_date}</Text>
            </View>
          ) : null}
        </View>
      )}

      <Text style={styles.expandToggle}>
        {expanded ? 'Show less ▲' : 'Show more ▼'}
      </Text>
    </Pressable>
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function LookupScreen() {
  const { token } = useAuth();

  const [mode,     setMode]    = useState<Mode>('cnr');
  const [query,    setQuery]   = useState('');
  const [loading,  setLoading] = useState(false);
  const [error,    setError]   = useState<string | null>(null);
  const [results,  setResults] = useState<CaseResult[]>([]);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<TextInput>(null);

  const switchMode = useCallback((m: Mode) => {
    setMode(m);
    setQuery('');
    setResults([]);
    setError(null);
    setSearched(false);
    setTimeout(() => inputRef.current?.focus(), 80);
  }, []);

  const search = useCallback(async () => {
    const q = query.trim();
    if (!q || !token) return;
    setLoading(true);
    setError(null);
    setResults([]);
    setSearched(false);

    try {
      let url: string;
      if (mode === 'cnr') {
        const cnr = q.toUpperCase();
        url = `${API_BASE}/api/cases/cnr/${cnr}`;
      } else {
        url = `${API_BASE}/api/cases/search?name=${encodeURIComponent(q)}`;
      }

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Error ${res.status}`);
      }

      const data = await res.json();

      if (mode === 'cnr') {
        setResults([data as CaseResult]);
      } else {
        setResults((data?.results ?? []) as CaseResult[]);
      }
    } catch (e: any) {
      setError(e?.message ?? 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
      setSearched(true);
    }
  }, [query, mode, token]);

  const handleCNRChange = (text: string) => setQuery(formatCNR(text));

  const cnrComplete = mode === 'cnr' && query.length === 16;
  const canSearch   = mode === 'cnr' ? cnrComplete : query.trim().length >= 2;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <View style={styles.header}>
        <View style={styles.headerTitleRow}>
          <Ionicons name="search-outline" size={20} color={theme.colors.onBrandPrimary} />
          <Text style={styles.headerTitle}>Dhara Lookup</Text>
        </View>
        <Text style={styles.headerSub}>
          Search Indian court cases via eCourtsIndia
        </Text>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* ── Mode toggle ─────────────────────────────────────────────────── */}
          <View style={styles.modeRow}>
            <Pressable
              testID="mode-cnr"
              style={[styles.modeBtn, mode === 'cnr' && styles.modeBtnActive]}
              onPress={() => switchMode('cnr')}
            >
              <Ionicons
                name="barcode-outline"
                size={15}
                color={mode === 'cnr' ? theme.colors.onBrandPrimary : theme.colors.brand}
              />
              <Text style={[styles.modeBtnText, mode === 'cnr' && styles.modeBtnTextActive]}>
                By CNR
              </Text>
            </Pressable>
            <Pressable
              testID="mode-party"
              style={[styles.modeBtn, mode === 'party' && styles.modeBtnActive]}
              onPress={() => switchMode('party')}
            >
              <Ionicons
                name="person-outline"
                size={15}
                color={mode === 'party' ? theme.colors.onBrandPrimary : theme.colors.brand}
              />
              <Text style={[styles.modeBtnText, mode === 'party' && styles.modeBtnTextActive]}>
                By Party
              </Text>
            </Pressable>
          </View>

          {/* ── Input ───────────────────────────────────────────────────────── */}
          <View style={styles.inputCard}>
            <View style={styles.inputRow}>
              <TextInput
                ref={inputRef}
                testID="lookup-input"
                style={styles.input}
                value={query}
                onChangeText={mode === 'cnr' ? handleCNRChange : setQuery}
                placeholder={
                  mode === 'cnr'
                    ? 'CNR number — e.g. DLHC010001232024'
                    : 'Petitioner or respondent name'
                }
                placeholderTextColor={CNR_HINT_COLOR}
                autoCapitalize={mode === 'cnr' ? 'characters' : 'words'}
                autoCorrect={false}
                returnKeyType="search"
                onSubmitEditing={canSearch ? search : undefined}
                editable={!loading}
                maxLength={mode === 'cnr' ? 16 : 120}
              />
              {query.length > 0 && (
                <Pressable
                  onPress={() => { setQuery(''); setResults([]); setError(null); setSearched(false); }}
                  hitSlop={8}
                >
                  <Ionicons name="close-circle" size={18} color={theme.colors.onSurfaceSecondary} />
                </Pressable>
              )}
            </View>

            {/* CNR progress indicator */}
            {mode === 'cnr' && query.length > 0 && (
              <View style={styles.cnrProgress}>
                <View style={[styles.cnrBar, { width: `${(query.length / 16) * 100}%` as any }]} />
                <Text style={styles.cnrCount}>
                  {query.length}/16{cnrComplete ? ' ✓' : ''}
                </Text>
              </View>
            )}

            <Text style={styles.inputHint}>
              {mode === 'cnr'
                ? '4 letters + 12 digits — find the CNR on your case notice or eCourts portal'
                : 'Enter the full or partial name of any party listed in the case'}
            </Text>
          </View>

          {/* ── Search button ───────────────────────────────────────────────── */}
          <Pressable
            testID="lookup-search-btn"
            style={[styles.searchBtn, !canSearch && styles.searchBtnDisabled]}
            onPress={search}
            disabled={!canSearch || loading}
          >
            {loading ? (
              <ActivityIndicator color={theme.colors.onBrandPrimary} size="small" />
            ) : (
              <>
                <Ionicons name="search" size={16} color={theme.colors.onBrandPrimary} />
                <Text style={styles.searchBtnText}>Search</Text>
              </>
            )}
          </Pressable>

          {/* ── Error ───────────────────────────────────────────────────────── */}
          {error && (
            <View style={styles.errorCard}>
              <Ionicons name="alert-circle-outline" size={16} color={theme.colors.error} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* ── Results ─────────────────────────────────────────────────────── */}
          {results.length > 0 && (
            <View style={styles.resultsWrap}>
              <Text style={styles.resultsLabel}>
                {results.length === 1 ? '1 case found' : `${results.length} cases found`}
              </Text>
              {results.map((item, i) => (
                <CaseCard key={item.cnr ?? i} item={item} />
              ))}
            </View>
          )}

          {/* ── Empty state ─────────────────────────────────────────────────── */}
          {searched && results.length === 0 && !error && (
            <View style={styles.emptyWrap}>
              <Ionicons name="file-tray-outline" size={40} color={theme.colors.onSurfaceSecondary} />
              <Text style={styles.emptyTitle}>No cases found</Text>
              <Text style={styles.emptyBody}>
                {mode === 'cnr'
                  ? 'Check the CNR number and try again.'
                  : 'Try a different spelling or broader search term.'}
              </Text>
            </View>
          )}

          {/* ── First-launch hint ───────────────────────────────────────────── */}
          {!searched && !loading && (
            <View style={styles.hintWrap}>
              <View style={styles.hintCard}>
                <Ionicons name="barcode-outline" size={22} color={theme.colors.brand} style={{ marginBottom: 6 }} />
                <Text style={styles.hintTitle}>Case Number Record (CNR)</Text>
                <Text style={styles.hintBody}>
                  Your unique 16-character case ID. Find it on any court notice,
                  vakalatnama, or the National eCourts portal at{' '}
                  <Text style={styles.hintLink}>ecourts.gov.in</Text>.
                </Text>
              </View>
              <View style={styles.hintCard}>
                <Ionicons name="person-outline" size={22} color={theme.colors.brand} style={{ marginBottom: 6 }} />
                <Text style={styles.hintTitle}>Party name search</Text>
                <Text style={styles.hintBody}>
                  Search by petitioner or respondent name to find all cases
                  associated with a person or organisation across courts.
                </Text>
              </View>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  safe:   { flex: 1, backgroundColor: theme.colors.surface },

  // Header
  header: {
    backgroundColor: theme.dhara.navy,
    paddingHorizontal: theme.spacing.xl,
    paddingVertical: theme.spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(211,182,117,0.25)',
  },
  headerTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 },
  headerTitle:   { fontSize: 20, fontWeight: '700', color: theme.colors.onBrandPrimary, fontFamily: theme.fonts.display },
  headerSub:     { fontSize: 13, color: theme.dhara.gold, fontWeight: '500' },

  scroll:        { flex: 1 },
  scrollContent: { padding: theme.spacing.xl, gap: theme.spacing.lg },

  // Mode toggle
  modeRow: { flexDirection: 'row', gap: 10 },
  modeBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 10, borderRadius: theme.radius.md,
    borderWidth: 1.5, borderColor: theme.colors.brand,
    backgroundColor: theme.colors.surface,
  },
  modeBtnActive:     { backgroundColor: theme.colors.brand, borderColor: theme.colors.brand },
  modeBtnText:       { fontSize: 14, fontWeight: '700', color: theme.colors.brand },
  modeBtnTextActive: { color: theme.colors.onBrandPrimary },

  // Input card
  inputCard: {
    borderWidth: 1, borderColor: theme.colors.border,
    borderRadius: theme.radius.lg, padding: theme.spacing.lg,
    backgroundColor: theme.colors.surface, gap: 8,
  },
  inputRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    borderBottomWidth: 1, borderBottomColor: theme.colors.divider,
    paddingBottom: 8,
  },
  input: { flex: 1, fontSize: 15, color: theme.colors.onSurface, minHeight: 28 },

  // CNR progress
  cnrProgress: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  cnrBar:      { height: 3, borderRadius: 2, backgroundColor: theme.colors.brand, maxWidth: '100%' },
  cnrCount:    { fontSize: 11, color: theme.colors.brand, fontWeight: '700' },

  inputHint: { fontSize: 12, color: theme.colors.onSurfaceSecondary, lineHeight: 16 },

  // Search button
  searchBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, backgroundColor: theme.dhara.navy,
    paddingVertical: 14, borderRadius: theme.radius.md,
  },
  searchBtnDisabled: { backgroundColor: theme.colors.borderStrong },
  searchBtnText:     { color: theme.colors.onBrandPrimary, fontSize: 15, fontWeight: '700' },

  // Error
  errorCard: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    backgroundColor: '#FEF2F2', borderWidth: 1, borderColor: theme.colors.error,
    borderRadius: theme.radius.md, padding: theme.spacing.lg,
  },
  errorText: { flex: 1, color: theme.colors.error, fontSize: 13, lineHeight: 18 },

  // Results
  resultsWrap:  { gap: theme.spacing.md },
  resultsLabel: { fontSize: 13, fontWeight: '700', color: theme.colors.onSurfaceSecondary, letterSpacing: 0.3 },

  // Case card
  card: {
    borderWidth: 1, borderColor: theme.colors.border,
    borderRadius: theme.radius.lg, padding: theme.spacing.lg,
    backgroundColor: theme.colors.surface, gap: 6,
    ...Platform.select({ web: { boxShadow: '0 1px 6px rgba(20,54,90,0.07)' } as any }),
  },
  cardTop:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  cnrRow:        { flexDirection: 'row', alignItems: 'center', gap: 6 },
  cnr:           { fontSize: 14, fontWeight: '800', color: theme.dhara.navy, letterSpacing: 0.5, fontFamily: theme.fonts.mono ?? theme.fonts.body },
  court:         { fontSize: 13, color: theme.colors.onSurface, fontWeight: '500' },
  hearingRow:    { flexDirection: 'row', alignItems: 'center', gap: 5 },
  hearingText:   { fontSize: 12, color: theme.colors.brand, fontWeight: '600' },
  expandedWrap:  { borderTopWidth: 1, borderTopColor: theme.colors.divider, paddingTop: 8, gap: 5, marginTop: 4 },
  partyRow:      { flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
  partyLabel:    { width: 88, fontSize: 12, fontWeight: '700', color: theme.colors.onSurfaceSecondary },
  partyValue:    { flex: 1, fontSize: 12, color: theme.colors.onSurface, lineHeight: 17 },
  expandToggle:  { fontSize: 11, color: theme.colors.brand, textAlign: 'right', marginTop: 2 },

  // Status badge
  badge:           { paddingHorizontal: 8, paddingVertical: 3, borderRadius: theme.radius.pill },
  badgePending:    { backgroundColor: '#FEF9EC' },
  badgeDisposed:   { backgroundColor: '#ECFDF5' },
  badgeText:       { fontSize: 10, fontWeight: '700', letterSpacing: 0.3 },
  badgeTextPending:  { color: '#B45309' },
  badgeTextDisposed: { color: '#047857' },

  // Empty state
  emptyWrap:  { alignItems: 'center', paddingVertical: 40, gap: 10 },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: theme.colors.onSurface },
  emptyBody:  { fontSize: 13, color: theme.colors.onSurfaceSecondary, textAlign: 'center' },

  // Hint cards
  hintWrap: { gap: 12 },
  hintCard: {
    borderWidth: 1, borderColor: theme.colors.border,
    borderRadius: theme.radius.lg, padding: theme.spacing.lg,
    backgroundColor: theme.colors.surfaceSecondary,
  },
  hintTitle: { fontSize: 14, fontWeight: '700', color: theme.colors.onSurface, marginBottom: 4 },
  hintBody:  { fontSize: 13, color: theme.colors.onSurfaceSecondary, lineHeight: 19 },
  hintLink:  { color: theme.colors.brand, fontWeight: '600' },
});
