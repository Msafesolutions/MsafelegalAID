import React, { useState, useCallback, useRef } from 'react';
import {
  View, Text, TextInput, ScrollView, Pressable,
  StyleSheet, ActivityIndicator, Modal, FlatList,
  KeyboardAvoidingView, Platform, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Linking from 'expo-linking';
import { Ionicons } from '@expo/vector-icons';
import { useAuth, API_BASE } from '@/src/auth';
import { theme } from '@/src/theme';
import {
  STATES_UTS, CASE_TYPES,
  getDistricts, getComplexes,
  CNR_STATE_CODES, CNR_COURT_CODES,
  type StateUT, type District, type Complex,
} from '@/src/courtData';

const NAVY = '#14365A';
const GOLD = '#D3B675';
const HINT = '#9CA3AF';

type Mode = 'cnr' | 'party';
type CaseResult = {
  cnr: string | null; case_status: string | null; next_hearing_date: string | null;
  court_name: string | null; district: string | null; state: string | null;
  case_type: string | null; filing_date: string | null;
  petitioners: string[]; respondents: string[];
};

const formatCNR = (raw: string) => raw.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 16);

// ── Generic sheet picker ──────────────────────────────────────────────────────
function SheetPicker<T extends { code: string; name: string }>({
  visible, title, items, selected, onSelect, onClose,
}: {
  visible: boolean; title: string; items: T[];
  selected: string; onSelect: (item: T) => void; onClose: () => void;
}) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={ps.overlay} onPress={onClose}>
        <View style={ps.sheet}>
          <View style={ps.handle} />
          <Text style={ps.title}>{title}</Text>
          <FlatList
            data={items}
            keyExtractor={i => i.code}
            renderItem={({ item }) => (
              <Pressable style={ps.item} onPress={() => { onSelect(item); onClose(); }}>
                <Text style={[ps.itemText, item.code === selected && ps.itemActive]}>{item.name}</Text>
                {item.code === selected && <Ionicons name="checkmark" size={16} color={NAVY} />}
              </Pressable>
            )}
          />
        </View>
      </Pressable>
    </Modal>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string | null }) {
  if (!status) return null;
  const disposed = /dispos|closed|decided/i.test(status);
  return (
    <View style={[styles.badge, disposed ? styles.badgeDisposed : styles.badgePending]}>
      <Text style={[styles.badgeText, disposed ? styles.badgeTextDisposed : styles.badgeTextPending]}>{status}</Text>
    </View>
  );
}

// ── Case card ─────────────────────────────────────────────────────────────────
function CaseCard({ item }: { item: CaseResult }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Pressable style={styles.card} onPress={() => setExpanded(v => !v)}>
      <View style={styles.cardTop}>
        <View style={styles.cnrRow}>
          <Ionicons name="document-text-outline" size={14} color={NAVY} />
          <Text style={styles.cnr} selectable>{item.cnr ?? '—'}</Text>
        </View>
        <StatusBadge status={item.case_status} />
      </View>
      {(item.court_name || item.district) && (
        <Text style={styles.court} numberOfLines={1}>
          {[item.court_name, item.district, item.state].filter(Boolean).join(' · ')}
        </Text>
      )}
      {item.next_hearing_date && (
        <View style={styles.hearingRow}>
          <Ionicons name="calendar-outline" size={12} color={theme.colors.brand} />
          <Text style={styles.hearingText}>Next hearing: {item.next_hearing_date}</Text>
        </View>
      )}
      {expanded && (
        <View style={styles.expanded}>
          {item.petitioners?.[0] && <View style={styles.partyRow}><Text style={styles.partyLabel}>Petitioner</Text><Text style={styles.partyVal}>{item.petitioners[0]}</Text></View>}
          {item.respondents?.[0] && <View style={styles.partyRow}><Text style={styles.partyLabel}>Respondent</Text><Text style={styles.partyVal}>{item.respondents[0]}</Text></View>}
          {item.case_type   && <View style={styles.partyRow}><Text style={styles.partyLabel}>Case type</Text><Text style={styles.partyVal}>{item.case_type}</Text></View>}
          {item.filing_date && <View style={styles.partyRow}><Text style={styles.partyLabel}>Filed on</Text><Text style={styles.partyVal}>{item.filing_date}</Text></View>}
        </View>
      )}
      <Text style={styles.toggle}>{expanded ? 'Show less ▲' : 'Show more ▼'}</Text>
    </Pressable>
  );
}

// ── PickerRow ─────────────────────────────────────────────────────────────────
function PickerRow({ label, value, placeholder, onPress, disabled = false }: {
  label: string; value: string; placeholder: string; onPress: () => void; disabled?: boolean;
}) {
  return (
    <View style={styles.filterBlock}>
      <Text style={styles.filterLabel}>{label}</Text>
      <Pressable
        style={[styles.filterBtn, disabled && { opacity: 0.4 }]}
        onPress={onPress}
        disabled={disabled}
      >
        <Text style={value ? styles.filterVal : styles.filterPlaceholder} numberOfLines={1}>
          {value || placeholder}
        </Text>
        <Ionicons name="chevron-down" size={15} color={NAVY} />
      </Pressable>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function LookupScreen() {
  const { token } = useAuth();
  const [mode, setMode] = useState<Mode>('cnr');

  // CNR state
  const [cnrQuery, setCnrQuery]   = useState('');
  const [cnrState, setCnrState]   = useState('');
  const [cnrCourt, setCnrCourt]   = useState('');
  const [results,  setResults]    = useState<CaseResult[]>([]);
  const [loading,  setLoading]    = useState(false);
  const [error,    setError]      = useState<string | null>(null);
  const [searched, setSearched]   = useState(false);

  // Party name state
  const [selState,   setSelState]   = useState<StateUT | null>(null);
  const [selDist,    setSelDist]    = useState<District | null>(null);
  const [selComplex, setSelComplex] = useState<Complex | null>(null);
  const [caseType,   setCaseType]   = useState(CASE_TYPES[0]);
  const [partyRole,  setPartyRole]  = useState<'Any' | 'Petitioner' | 'Respondent' | 'Accused'>('Any');
  const [partyName,  setPartyName]  = useState('');

  // Pickers visibility
  const [showState,   setShowState]   = useState(false);
  const [showDist,    setShowDist]    = useState(false);
  const [showComplex, setShowComplex] = useState(false);
  const [showType,    setShowType]    = useState(false);

  const inputRef = useRef<TextInput>(null);

  // Cascade reset
  const pickState = (s: StateUT) => { setSelState(s); setSelDist(null); setSelComplex(null); };
  const pickDist  = (d: District) => { setSelDist(d); setSelComplex(null); };

  // CNR auto-decode
  const handleCNR = (text: string) => {
    const v = formatCNR(text);
    setCnrQuery(v);
    setCnrState(v.length >= 2 ? (CNR_STATE_CODES[v.slice(0, 2)] ?? '') : '');
    setCnrCourt(v.length >= 4 ? (CNR_COURT_CODES[v.slice(2, 4)] ?? '') : '');
  };

  // CNR search (existing backend)
  const searchCNR = useCallback(async () => {
    if (cnrQuery.length !== 16 || !token) return;
    setLoading(true); setError(null); setResults([]); setSearched(false);
    try {
      const r = await fetch(`${API_BASE}/api/cases/cnr/${cnrQuery}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error((await r.json())?.detail ?? `Error ${r.status}`);
      setResults([await r.json()]);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); setSearched(true); }
  }, [cnrQuery, token]);

  // Party search → open eCourts in browser
  const searchParty = useCallback(() => {
    if (!selState || !partyName.trim()) return;
    const params = new URLSearchParams();
    params.set('state_code', selState.code);
    if (selDist)    params.set('dist_code',     selDist.code);
    if (selComplex && selComplex.code !== 'ALL') params.set('court_complex_code', selComplex.code);
    if (caseType.code)  params.set('case_type', caseType.code);
    params.set('party_name', partyName.trim());
    if (partyRole !== 'Any') params.set('party_type', partyRole.toLowerCase());
    const url = `https://services.ecourts.gov.in/ecourtindiaR2/cases/casestatus_index.php?${params.toString()}`;
    Linking.openURL(url);
  }, [selState, selDist, selComplex, caseType, partyRole, partyName]);

  const resetParty = () => {
    setSelState(null); setSelDist(null); setSelComplex(null);
    setCaseType(CASE_TYPES[0]); setPartyRole('Any'); setPartyName('');
  };

  const districts = selState ? getDistricts(selState.code) : [];
  const complexes = selState && selDist
    ? getComplexes(selState.code, selDist.code)
    : [];
  const defaultComplex: Complex = selDist
    ? { code: 'ALL', name: `All courts in ${selDist.name}` }
    : { code: 'ALL', name: 'All courts in district' };
  const complexList = complexes.length > 0 ? [defaultComplex, ...complexes] : [defaultComplex];

  const cnrComplete = cnrQuery.length === 16;
  const partyCanSearch = !!selState && partyName.trim().length >= 2;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <Ionicons name="search-outline" size={20} color="#fff" />
          <Text style={styles.headerTitle}>Dhara Lookup</Text>
        </View>
        <Text style={styles.headerSub}>Search Indian court cases via eCourtsIndia</Text>
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">

          {/* Mode toggle */}
          <View style={styles.modeRow}>
            {(['cnr', 'party'] as Mode[]).map(m => (
              <Pressable
                key={m}
                style={[styles.modeBtn, mode === m && styles.modeBtnActive]}
                onPress={() => { setMode(m); setResults([]); setError(null); setSearched(false); }}
              >
                <Ionicons
                  name={m === 'cnr' ? 'barcode-outline' : 'person-outline'}
                  size={15}
                  color={mode === m ? '#fff' : NAVY}
                />
                <Text style={[styles.modeBtnText, mode === m && { color: '#fff' }]}>
                  {m === 'cnr' ? 'By CNR' : 'By Party Name'}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* ── CNR MODE ─────────────────────────────────────────── */}
          {mode === 'cnr' && (
            <View style={styles.card}>
              <View style={styles.inputRow}>
                <TextInput
                  ref={inputRef}
                  style={styles.input}
                  value={cnrQuery}
                  onChangeText={handleCNR}
                  placeholder="CNR — e.g. DLHC010001232024"
                  placeholderTextColor={HINT}
                  autoCapitalize="characters"
                  autoCorrect={false}
                  maxLength={16}
                  returnKeyType="search"
                  onSubmitEditing={cnrComplete ? searchCNR : undefined}
                />
                {cnrQuery.length > 0 && (
                  <Pressable onPress={() => { setCnrQuery(''); setCnrState(''); setCnrCourt(''); setResults([]); }} hitSlop={8}>
                    <Ionicons name="close-circle" size={18} color={HINT} />
                  </Pressable>
                )}
              </View>

              {cnrQuery.length > 0 && (
                <View style={styles.cnrProgress}>
                  <View style={[styles.cnrBar, { width: `${(cnrQuery.length / 16) * 100}%` as any }]} />
                  <Text style={styles.cnrCount}>{cnrQuery.length}/16{cnrComplete ? ' ✓' : ''}</Text>
                </View>
              )}

              {/* Auto-decode labels */}
              {(cnrState || cnrCourt) ? (
                <View style={styles.decodedRow}>
                  {cnrState ? (
                    <View style={styles.decodedChip}>
                      <Ionicons name="location-outline" size={12} color={NAVY} />
                      <Text style={styles.decodedText}>{cnrQuery.slice(0, 2)} → {cnrState}</Text>
                    </View>
                  ) : null}
                  {cnrCourt ? (
                    <View style={styles.decodedChip}>
                      <Ionicons name="business-outline" size={12} color={NAVY} />
                      <Text style={styles.decodedText}>{cnrQuery.slice(2, 4)} → {cnrCourt}</Text>
                    </View>
                  ) : null}
                </View>
              ) : null}

              <Text style={styles.inputHint}>
                CNR = 16 characters · found on your case notice or the eCourts portal
              </Text>

              <Pressable
                style={[styles.searchBtn, !cnrComplete && styles.searchBtnDisabled]}
                onPress={searchCNR}
                disabled={!cnrComplete || loading}
              >
                {loading
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <><Ionicons name="search" size={16} color="#fff" /><Text style={styles.searchBtnText}>Search eCourts</Text></>}
              </Pressable>
            </View>
          )}

          {/* ── PARTY MODE ───────────────────────────────────────── */}
          {mode === 'party' && (
            <View style={styles.card}>
              {/* Step 1: State */}
              <PickerRow
                label="Step 1 — State / Union Territory *"
                value={selState?.name ?? ''}
                placeholder="Select State / UT"
                onPress={() => setShowState(true)}
              />

              {/* Step 2: District (cascades) */}
              {selState && (
                <PickerRow
                  label="Step 2 — District"
                  value={selDist?.name ?? ''}
                  placeholder="Select District"
                  onPress={() => setShowDist(true)}
                />
              )}

              {/* Step 3: Court Complex (cascades) */}
              {selDist && (
                <PickerRow
                  label="Step 3 — Court Complex"
                  value={selComplex?.name ?? defaultComplex.name}
                  placeholder="Select Court Complex"
                  onPress={() => setShowComplex(true)}
                />
              )}

              {/* Optional filters */}
              {selState && (
                <>
                  <View style={styles.divider} />
                  <PickerRow
                    label="Case Type (optional)"
                    value={caseType.name}
                    placeholder="All case types"
                    onPress={() => setShowType(true)}
                  />

                  {/* Party Role toggle */}
                  <View style={styles.filterBlock}>
                    <Text style={styles.filterLabel}>Party Role (optional)</Text>
                    <View style={styles.roleRow}>
                      {(['Any', 'Petitioner', 'Respondent', 'Accused'] as const).map(r => (
                        <Pressable
                          key={r}
                          style={[styles.roleBtn, partyRole === r && styles.roleBtnActive]}
                          onPress={() => setPartyRole(r)}
                        >
                          <Text style={[styles.roleBtnText, partyRole === r && { color: '#fff' }]}>{r}</Text>
                        </Pressable>
                      ))}
                    </View>
                  </View>
                </>
              )}

              {/* Party name input */}
              <View style={styles.filterBlock}>
                <Text style={styles.filterLabel}>Step {selState ? 5 : 2} — Party Name *</Text>
                <View style={styles.inputRow}>
                  <TextInput
                    style={[styles.input, { flex: 1 }]}
                    value={partyName}
                    onChangeText={setPartyName}
                    placeholder="Enter petitioner or respondent name"
                    placeholderTextColor={HINT}
                    autoCapitalize="words"
                    autoCorrect={false}
                    returnKeyType="search"
                    onSubmitEditing={partyCanSearch ? searchParty : undefined}
                  />
                  {partyName.length > 0 && (
                    <Pressable onPress={() => setPartyName('')} hitSlop={8}>
                      <Ionicons name="close-circle" size={18} color={HINT} />
                    </Pressable>
                  )}
                </View>
              </View>

              <Pressable
                style={[styles.searchBtn, !partyCanSearch && styles.searchBtnDisabled]}
                onPress={searchParty}
                disabled={!partyCanSearch}
              >
                <Ionicons name="open-outline" size={16} color="#fff" />
                <Text style={styles.searchBtnText}>Search eCourts</Text>
              </Pressable>

              <Pressable onPress={resetParty} style={{ alignItems: 'center', marginTop: 8 }}>
                <Text style={styles.clearText}>Clear filters</Text>
              </Pressable>
            </View>
          )}

          {/* Error */}
          {error && (
            <View style={styles.errorCard}>
              <Ionicons name="alert-circle-outline" size={16} color={theme.colors.error} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Results */}
          {results.length > 0 && (
            <View style={{ gap: 10 }}>
              <Text style={styles.resultsLabel}>{results.length === 1 ? '1 case found' : `${results.length} cases found`}</Text>
              {results.map((item, i) => <CaseCard key={item.cnr ?? i} item={item} />)}
            </View>
          )}

          {/* Empty state */}
          {searched && results.length === 0 && !error && (
            <View style={styles.emptyWrap}>
              <Ionicons name="file-tray-outline" size={40} color={HINT} />
              <Text style={styles.emptyTitle}>No cases found</Text>
              <Text style={styles.emptyBody}>Check the CNR number and try again.</Text>
            </View>
          )}

          {/* Hint cards */}
          {!searched && !loading && mode === 'cnr' && (
            <View style={styles.hintCard}>
              <Ionicons name="barcode-outline" size={20} color={NAVY} />
              <View style={{ flex: 1 }}>
                <Text style={styles.hintTitle}>Case Number Record (CNR)</Text>
                <Text style={styles.hintBody}>Your unique 16-character case ID. Find it on any court notice or at ecourts.gov.in</Text>
              </View>
            </View>
          )}

          {mode === 'party' && !selState && (
            <View style={styles.hintCard}>
              <Ionicons name="funnel-outline" size={20} color={NAVY} />
              <View style={{ flex: 1 }}>
                <Text style={styles.hintTitle}>Narrow your search</Text>
                <Text style={styles.hintBody}>Select a State first, then District and Court to get precise results. Opens eCourts portal in browser.</Text>
              </View>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Pickers */}
      <SheetPicker
        visible={showState} title="Select State / UT"
        items={STATES_UTS} selected={selState?.code ?? ''}
        onSelect={pickState} onClose={() => setShowState(false)}
      />
      <SheetPicker
        visible={showDist} title="Select District"
        items={districts} selected={selDist?.code ?? ''}
        onSelect={pickDist} onClose={() => setShowDist(false)}
      />
      <SheetPicker
        visible={showComplex} title="Select Court Complex"
        items={complexList} selected={selComplex?.code ?? 'ALL'}
        onSelect={c => setSelComplex(c.code === 'ALL' ? null : c)}
        onClose={() => setShowComplex(false)}
      />
      <SheetPicker
        visible={showType} title="Select Case Type"
        items={CASE_TYPES} selected={caseType.code}
        onSelect={setCaseType} onClose={() => setShowType(false)}
      />
    </SafeAreaView>
  );
}

const ps = StyleSheet.create({
  overlay:  { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  sheet:    { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: '75%', paddingHorizontal: 20, paddingBottom: 30 },
  handle:   { width: 36, height: 4, borderRadius: 2, backgroundColor: '#E5E7EB', alignSelf: 'center', marginVertical: 10 },
  title:    { fontSize: 16, fontWeight: '700', color: NAVY, marginBottom: 10 },
  item:     { paddingVertical: 13, borderBottomWidth: 1, borderBottomColor: '#F3F4F6', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemText: { fontSize: 14, color: '#374151', flex: 1 },
  itemActive: { color: NAVY, fontWeight: '700' },
});

const styles = StyleSheet.create({
  safe:   { flex: 1, backgroundColor: theme.colors.surface },
  header: { backgroundColor: NAVY, paddingHorizontal: 20, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: 'rgba(211,182,117,0.25)' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 3 },
  headerTitle: { fontSize: 20, fontWeight: '700', color: '#fff' },
  headerSub: { fontSize: 13, color: GOLD, fontWeight: '500' },
  scroll:  { flex: 1 },
  scrollContent: { padding: 16, gap: 14, paddingBottom: 40 },

  modeRow: { flexDirection: 'row', gap: 10 },
  modeBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 10, borderWidth: 1.5, borderColor: NAVY, backgroundColor: theme.colors.surface },
  modeBtnActive: { backgroundColor: NAVY },
  modeBtnText: { fontSize: 14, fontWeight: '700', color: NAVY },

  card: { backgroundColor: '#fff', borderRadius: 14, borderWidth: 1, borderColor: theme.colors.border, padding: 16, gap: 12 },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: 1, borderBottomColor: theme.colors.divider, paddingBottom: 8 },
  input: { flex: 1, fontSize: 15, color: theme.colors.onSurface, minHeight: 28 },

  cnrProgress: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  cnrBar: { height: 3, borderRadius: 2, backgroundColor: NAVY },
  cnrCount: { fontSize: 11, color: NAVY, fontWeight: '700' },

  decodedRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  decodedChip: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#EEF2FF', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8 },
  decodedText: { fontSize: 12, color: NAVY, fontWeight: '600' },

  inputHint: { fontSize: 12, color: HINT, lineHeight: 16 },

  filterBlock: { gap: 5 },
  filterLabel: { fontSize: 12, fontWeight: '700', color: NAVY, letterSpacing: 0.2 },
  filterBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderWidth: 1.5, borderColor: theme.colors.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10 },
  filterVal: { fontSize: 14, color: theme.colors.onSurface, flex: 1 },
  filterPlaceholder: { fontSize: 14, color: HINT, flex: 1 },

  divider: { height: 1, backgroundColor: theme.colors.divider },

  roleRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  roleBtn: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 8, borderWidth: 1.5, borderColor: NAVY },
  roleBtnActive: { backgroundColor: NAVY },
  roleBtnText: { fontSize: 12, fontWeight: '600', color: NAVY },

  searchBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: NAVY, paddingVertical: 13, borderRadius: 10 },
  searchBtnDisabled: { backgroundColor: theme.colors.borderStrong },
  searchBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  clearText: { fontSize: 13, color: HINT, textDecorationLine: 'underline' },

  errorCard: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, backgroundColor: '#FEF2F2', borderWidth: 1, borderColor: theme.colors.error, borderRadius: 10, padding: 12 },
  errorText: { flex: 1, color: theme.colors.error, fontSize: 13 },

  resultsLabel: { fontSize: 13, fontWeight: '700', color: HINT },

  card: { borderWidth: 1, borderColor: theme.colors.border, borderRadius: 12, padding: 14, backgroundColor: '#fff', gap: 6 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cnrRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  cnr: { fontSize: 13, fontWeight: '800', color: NAVY, letterSpacing: 0.5 },
  court: { fontSize: 13, color: theme.colors.onSurface },
  hearingRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  hearingText: { fontSize: 12, color: theme.colors.brand, fontWeight: '600' },
  expanded: { borderTopWidth: 1, borderTopColor: theme.colors.divider, paddingTop: 8, gap: 5 },
  partyRow: { flexDirection: 'row', gap: 8 },
  partyLabel: { width: 84, fontSize: 12, fontWeight: '700', color: HINT },
  partyVal: { flex: 1, fontSize: 12, color: theme.colors.onSurface },
  toggle: { fontSize: 11, color: NAVY, textAlign: 'right' },

  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  badgePending: { backgroundColor: '#FEF9EC' }, badgeDisposed: { backgroundColor: '#ECFDF5' },
  badgeText: { fontSize: 10, fontWeight: '700' },
  badgeTextPending: { color: '#B45309' }, badgeTextDisposed: { color: '#047857' },

  emptyWrap: { alignItems: 'center', paddingVertical: 40, gap: 8 },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: theme.colors.onSurface },
  emptyBody:  { fontSize: 13, color: HINT, textAlign: 'center' },

  hintCard: { backgroundColor: theme.colors.surfaceSecondary, borderRadius: 12, borderWidth: 1, borderColor: theme.colors.border, padding: 14, flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  hintTitle: { fontSize: 14, fontWeight: '700', color: theme.colors.onSurface, marginBottom: 3 },
  hintBody:  { fontSize: 13, color: HINT, lineHeight: 18 },
});
