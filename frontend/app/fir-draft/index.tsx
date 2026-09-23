/**
 * DHARA FIR Interview Engine — Conversational UI (v3)
 * Stage-based chat interface that guides citizens through FIR preparation.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, StyleSheet,
  ActivityIndicator, Platform, Alert, KeyboardAvoidingView, Linking, Image,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
// Platform-guarded: expo-location crashes on web due to version mismatch.
// On native, we load it dynamically. On web, Location stays null and GPS is skipped.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const Location: typeof import('expo-location') | null =
  Platform.OS !== 'web' ? (() => { try { return require('expo-location'); } catch { return null; } })() : null;
import * as DocumentPicker from 'expo-document-picker';
import { API_BASE, useAuth } from '@/src/auth';
import {
  useAudioRecorder, RecordingPresets, setAudioModeAsync, AudioModule,
} from 'expo-audio';
import { whisperTranscribeFile } from '@/src/voice/stt';
import FirSectionDrawer, { SectionItem, DroppedSection } from '@/src/components/FirSectionDrawer';

// ── Theme ─────────────────────────────────────────────────────────────────────
const NAVY   = '#14365A';
const GOLD   = '#D3B675';
const CREAM  = '#F5F0E6';
const SURFACE = '#FDFBF7';
const MUTED  = '#4A5A6E';
const RED    = '#B91C1C';
const GREEN  = '#2D6A4F';
const BORDER = '#D1D5DB';

// ── Language options ──────────────────────────────────────────────────────────
const FIR_LANGUAGES = [
  { code: 'en', label: 'English',  native: 'English',  sttLang: 'en-IN' },
  { code: 'hi', label: 'Hindi',    native: 'हिन्दी',   sttLang: 'hi-IN' },
  { code: 'mr', label: 'Marathi',  native: 'मराठी',    sttLang: 'mr-IN' },
  { code: 'ta', label: 'Tamil',    native: 'தமிழ்',    sttLang: 'ta-IN' },
];
const FIR_LANG_KEY = 'fir_draft_lang_v3';
const FIR_SESSION_KEY = 'fir_active_session_v3';

// Allowed file types for evidence upload
const ALLOWED_MIME = [
  'image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp',
  'video/mp4', 'video/quicktime', 'video/x-msvideo',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const ALLOWED_EXT = ['jpg','jpeg','png','heic','heif','webp','mp4','mov','avi','pdf','doc','docx'];

// ── Types ─────────────────────────────────────────────────────────────────────
interface Message {
  id: string;
  role: 'bot' | 'user';
  text: string;
  timestamp: string;
}
interface TurnResponse {
  session_id: string;
  stage: string;
  bot_message: string;
  input_type: string;
  quick_replies?: string[];
  skip_label?: string;
  confirmed_address?: string;
  suggested_sections?: any[];
  dropped_sections?: any[];
  slots_preview?: any;
  draft?: string;
  completed?: boolean;
  safety_flags?: string[];
  // v3.3: Emergency & alert fields
  show_emergency?: boolean;
  action?: string;
  emergency_numbers?: Array<{ label: string; number: string }>;
  show_cybercrime_alert?: boolean;
}
interface UploadedFile {
  file_id: string;
  filename: string;
  file_type: string;
  local_uri?: string;   // v3.3: client-side preview URI
  content_type?: string;
  caption?: string;     // Issue 17: evidence caption
}

function msgId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function FirDraftScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ resumeId?: string }>();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();

  // ── Session state ──────────────────────────────────────────────────────────
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputType, setInputType] = useState<string>('quick_reply');
  const [quickReplies, setQuickReplies] = useState<string[]>(["Yes, I'm safe", "No, I need help"]);
  const [skipLabel, setSkipLabel] = useState<string | undefined>(undefined);
  const [draft, setDraft] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [evidenceFiles, setEvidenceFiles] = useState<UploadedFile[]>([]);
  const [uploadingEvidence, setUploadingEvidence] = useState(false);
  const [gpsAvailable, setGpsAvailable] = useState(Platform.OS !== 'web');
  // v3.3: New state
  const [currentStage, setCurrentStage] = useState<string>('safety_gate');
  const [showEmergencyScreen, setShowEmergencyScreen] = useState(false);
  const [emergencyNumbers, setEmergencyNumbers] = useState<Array<{label: string; number: string}>>([]);
  const [savedSessionId, setSavedSessionId] = useState<string | null>(null);
  const [checkingResume, setCheckingResume] = useState(true);

  // Issue 9: Section drawer state
  const [showSectionDrawer, setShowSectionDrawer] = useState(false);
  const [suggestedSections, setSuggestedSections] = useState<SectionItem[]>([]);
  const [droppedSections, setDroppedSections] = useState<DroppedSection[]>([]);
  const [sectionMsgId, setSectionMsgId] = useState<string | null>(null);
  const messageYsRef = useRef<{[id: string]: number}>({});

  // ── Language ───────────────────────────────────────────────────────────────
  const [language, setLanguage] = useState('en');
  const [sessionStarted, setSessionStarted] = useState(false);

  // ── Voice recording ────────────────────────────────────────────────────────
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [isRecording, setIsRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);

  const scrollRef = useRef<ScrollView>(null);

  // ── Load saved language + check for saved session ────────────────────────
  useEffect(() => {
    const init = async () => {
      const savedLang = await AsyncStorage.getItem(FIR_LANG_KEY);
      if (savedLang) setLanguage(savedLang);
      // v3.3: If a resumeId was passed from home screen, auto-resume
      if (params.resumeId) {
        setSavedSessionId(params.resumeId);
        setCheckingResume(false);
        return;
      }
      // v3.3: Check for a paused/active session to resume
      const saved = await AsyncStorage.getItem(FIR_SESSION_KEY);
      if (saved) {
        try {
          const res = await fetch(`${API_BASE}/api/fir/session/${saved}`);
          if (res.ok) {
            const sess = await res.json();
            if (sess.status !== 'completed' && sess.status !== 'cancelled') {
              setSavedSessionId(saved);
            } else {
              await AsyncStorage.removeItem(FIR_SESSION_KEY);
            }
          } else {
            await AsyncStorage.removeItem(FIR_SESSION_KEY);
          }
        } catch { /* session gone */ }
      }
      setCheckingResume(false);
    };
    init();
  }, [params.resumeId]);

  const saveLanguage = async (code: string) => {
    setLanguage(code);
    await AsyncStorage.setItem(FIR_LANG_KEY, code);
  };

  // ── Auto-scroll to bottom ──────────────────────────────────────────────────
  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  }, [messages, isLoading]);

  // ── Add message helper ─────────────────────────────────────────────────────
  const addMessage = useCallback((role: 'bot' | 'user', text: string): string => {
    const id = msgId();
    setMessages(prev => [...prev, {
      id, role, text,
      timestamp: new Date().toISOString(),
    }]);
    return id;
  }, []);

  // ── Apply turn response ───────────────────────────────────────────────────
  const applyTurn = useCallback((res: TurnResponse) => {
    let botMsgId: string | undefined;
    if (res.bot_message) {
      botMsgId = addMessage('bot', res.bot_message);
    }
    setCurrentStage(res.stage || '');
    setInputType(res.input_type || 'text');
    setQuickReplies(res.quick_replies || []);
    setSkipLabel(res.skip_label);
    if (res.draft) setDraft(res.draft);
    // v3.3: Emergency screen
    if (res.show_emergency || res.action === 'EMERGENCY') {
      setEmergencyNumbers(res.emergency_numbers || [
        { label: 'Emergency', number: '112' },
        { label: 'Women Helpline', number: '181' },
        { label: 'Ambulance', number: '108' },
      ]);
      setShowEmergencyScreen(true);
    }
    // Issue 9: Capture sections when section_suggest stage is entered
    if (res.suggested_sections && res.suggested_sections.length > 0) {
      setSuggestedSections(res.suggested_sections);
      if (botMsgId) setSectionMsgId(botMsgId);
    }
    if (res.dropped_sections && res.dropped_sections.length > 0) {
      setDroppedSections(res.dropped_sections);
    }
  }, [addMessage]);

  // ── Create session ─────────────────────────────────────────────────────────
  const startSession = async () => {
    if (!language) return;
    setIsLoading(true);
    setSessionStarted(true);
    setMessages([]);
    setSavedSessionId(null);
    try {
      // Try to silently get GPS for session_location_start (native only)
      let sessionLocationStart = null;
      try {
        if (Location) {
          const { status } = await Location.requestForegroundPermissionsAsync();
          if (status === 'granted') {
            const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
            sessionLocationStart = { lat: loc.coords.latitude, lng: loc.coords.longitude };
          }
        }
      } catch { /* GPS optional at start */ }

      const res = await fetch(`${API_BASE}/api/fir/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user?.id || `anon-${Date.now()}`,
          language,
          session_location_start: sessionLocationStart,
        }),
      });
      if (!res.ok) throw new Error('Session creation failed');
      const data: TurnResponse = await res.json();
      setSessionId(data.session_id);
      // v3.3: Persist session for silent resume
      await AsyncStorage.setItem(FIR_SESSION_KEY, data.session_id);
      applyTurn(data);
    } catch {
      Alert.alert('Error', 'Could not start session. Please check your connection.');
      setSessionStarted(false);
    } finally {
      setIsLoading(false);
    }
  };

  // ── v3.3: Resume a saved session ─────────────────────────────────────────
  const resumeSession = async (sid: string) => {
    setIsLoading(true);
    setSessionStarted(true);
    setMessages([]);
    try {
      const res = await fetch(`${API_BASE}/api/fir/session/${sid}`);
      if (!res.ok) throw new Error('Session not found');
      const sess = await res.json();
      setSessionId(sid);
      setLanguage(sess.language || 'en');
      await AsyncStorage.setItem(FIR_SESSION_KEY, sid);

      // Issue 17: Restore evidence files with captions
      const storedEvidence: any[] = sess.evidence_files || [];
      if (storedEvidence.length > 0) {
        const restored = storedEvidence.map((e: any) => ({
          file_id: typeof e === 'string' ? e : e.file_id,
          filename: typeof e === 'string' ? e : (e.filename || e),
          file_type: e.file_type || 'document',
          local_uri: undefined,
          content_type: e.content_type,
          caption: e.caption || '',
        }));
        setEvidenceFiles(restored);
      }

      // Issue 9: Restore sections if already suggested
      if (sess.suggested_sections?.length > 0) {
        setSuggestedSections(sess.suggested_sections);
      }
      if (sess.dropped_sections?.length > 0) {
        setDroppedSections(sess.dropped_sections);
      }

      // Restore last bot message from narrative_turns
      const turns: any[] = sess.narrative_turns || [];
      const lastBot = turns.filter((t: any) => t.role === 'bot').pop();
      const lastUser = turns.filter((t: any) => t.role === 'user').pop();
      if (lastUser) addMessage('user', lastUser.content || lastUser.text || '');
      // Resume with current probe
      const currentProbe = sess.current_probe;
      if (currentProbe) {
        // Fetch the probe definition via a "continue" turn
        const tRes = await fetch(`${API_BASE}/api/fir/session/${sid}/turn`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'resume' }),
        });
        if (tRes.ok) {
          const tData: TurnResponse = await tRes.json();
          applyTurn(tData);
        } else if (lastBot) {
          addMessage('bot', `Welcome back! Continuing from where you left off.\n\n${lastBot.content || lastBot.text || ''}`);
        }
      } else if (lastBot) {
        addMessage('bot', `Welcome back! Continuing from where you left off.\n\n${lastBot.content || lastBot.text || ''}`);
      } else {
        addMessage('bot', 'Welcome back! Please tell me what happened in your own words.');
        setInputType('voice_or_text');
      }
    } catch {
      Alert.alert('Error', 'Could not resume session. Please start a new one.');
      setSessionStarted(false);
      await AsyncStorage.removeItem(FIR_SESSION_KEY);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Send a turn ────────────────────────────────────────────────────────────
  const sendTurn = useCallback(async (
    userMsg?: string,
    gps?: { lat: number; lng: number },
    action?: string,
  ) => {
    if (!sessionId || isLoading) return;
    if (userMsg) addMessage('user', userMsg);
    else if (action === 'skip') addMessage('user', skipLabel || 'Skip');
    else if (action === 'upload_done') addMessage('user', `${evidenceFiles.length} file(s) uploaded`);

    setIsLoading(true);
    setTextInput('');
    try {
      const body: any = {};
      if (userMsg) body.user_message = userMsg;
      if (gps) body.gps = gps;
      if (action) body.action = action;
      const res = await fetch(`${API_BASE}/api/fir/session/${sessionId}/turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Turn failed: ${res.status}`);
      const data: TurnResponse = await res.json();
      applyTurn(data);
    } catch {
      Alert.alert('Error', 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading, skipLabel, evidenceFiles.length, addMessage, applyTurn]);

  // ── GPS capture ────────────────────────────────────────────────────────────
  const handleGetGPS = async () => {
    // GPS not supported on web — fall back silently to typed input
    if (!Location) {
      setGpsAvailable(false);
      return;
    }
    let { status, canAskAgain } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      if (!canAskAgain) {
        Alert.alert(
          'Location Permission Required',
          'GPS access is needed to pinpoint the incident location. Please enable it in Settings.',
          [
            { text: 'Open Settings', onPress: () => Linking.openSettings() },
            { text: 'Skip GPS', onPress: () => sendTurn(undefined, undefined, 'skip') },
          ],
        );
      } else {
        Alert.alert('Permission Denied', 'GPS permission was denied.', [
          { text: 'Skip GPS', onPress: () => sendTurn(undefined, undefined, 'skip') },
        ]);
      }
      return;
    }
    setIsLoading(true);
    addMessage('user', '📍 Getting GPS location…');
    try {
      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
      await sendTurn(
        undefined,
        { lat: loc.coords.latitude, lng: loc.coords.longitude },
        undefined,
      );
    } catch {
      Alert.alert('GPS Error', 'Could not get location. Please try again.');
    } finally {
    }
  };

  // ── Evidence upload — with type validation + 413 handling ───────────────
  const handlePickEvidence = async () => {
    if (!sessionId) return;
    try {
      const result = await DocumentPicker.getDocumentAsync({
        multiple: true,
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;
      const assets = result.assets || [];
      if (assets.length === 0) return;

      setUploadingEvidence(true);
      const uploaded: UploadedFile[] = [];
      for (const asset of assets.slice(0, 10 - evidenceFiles.length)) {
        // v3.3: File type validation
        const ext = (asset.name?.split('.').pop() || '').toLowerCase();
        const mime = asset.mimeType || '';
        const allowed = ALLOWED_EXT.includes(ext) || ALLOWED_MIME.includes(mime);
        if (!allowed) {
          Alert.alert('Unsupported File', `"${asset.name}" is not supported.
Allowed: JPG, PNG, HEIC, MP4, MOV, PDF, DOC, DOCX`);
          continue;
        }
        try {
          const formData = new FormData();
          if (Platform.OS === 'web') {
            const blob = await (await fetch(asset.uri)).blob();
            formData.append('file', blob, asset.name);
          } else {
            formData.append('file', {
              uri: asset.uri, name: asset.name, type: asset.mimeType || 'application/octet-stream',
            } as any);
          }
          const res = await fetch(`${API_BASE}/api/fir/session/${sessionId}/evidence`, {
            method: 'POST',
            body: formData,
          });
          // v3.3: 413 error
          if (res.status === 413) {
            Alert.alert('File Too Large', `"${asset.name}" exceeds the size limit (20 MB). Please compress the file and try again.`);
            continue;
          }
          if (res.ok) {
            const data = await res.json();
            if (data.file) {
              uploaded.push({
                ...data.file,
                local_uri: asset.uri,           // store for thumbnail
                content_type: asset.mimeType,
              });
            }
          }
        } catch (e) {
          console.warn('Evidence upload failed for', asset.name, e);
        }
      }
      if (uploaded.length > 0) {
        setEvidenceFiles(prev => [...prev, ...uploaded]);
        addMessage('user', `📎 Uploaded: ${uploaded.map(f => f.filename).join(', ')}`);
      }
    } catch (err) {
      Alert.alert('Upload failed', 'Please try again.');
      console.warn('Evidence upload error:', err);
    } finally {
      setUploadingEvidence(false);
    }
  };

  // ── v3.3: Remove evidence file ─────────────────────────────────────────────
  const handleRemoveEvidence = async (fileId: string) => {
    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/api/fir/session/${sessionId}/evidence/${fileId}`, { method: 'DELETE' });
      setEvidenceFiles(prev => prev.filter(f => f.file_id !== fileId));
    } catch {
      Alert.alert('Error', 'Could not remove file. Please try again.');
    }
  };

  // Issue 17: Update evidence caption
  const captionTimersRef = useRef<{[fileId: string]: ReturnType<typeof setTimeout>}>({});
  const handleCaptionChange = useCallback((fileId: string, caption: string) => {
    // Update local state immediately
    setEvidenceFiles(prev => prev.map(f => f.file_id === fileId ? { ...f, caption } : f));
    // Debounce the PATCH to backend (500ms)
    if (captionTimersRef.current[fileId]) clearTimeout(captionTimersRef.current[fileId]);
    captionTimersRef.current[fileId] = setTimeout(async () => {
      if (!sessionId) return;
      try {
        await fetch(`${API_BASE}/api/fir/session/${sessionId}/evidence/${fileId}/caption`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ caption }),
        });
      } catch { /* best effort */ }
    }, 500);
  }, [sessionId]);

  // ── Voice recording ────────────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      await setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { status } = await AudioModule.requestRecordingPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Microphone access required', 'Please allow microphone access to use voice input.');
        return;
      }
      await recorder.record();
      setIsRecording(true);
    } catch {
      Alert.alert('Recording failed', 'Could not start recording.');
    }
  };

  const stopRecording = async () => {
    setIsRecording(false);
    setTranscribing(true);
    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) throw new Error('No recording URI');
      const langCode = FIR_LANGUAGES.find(l => l.code === language)?.sttLang || 'en-IN';
      const text = await whisperTranscribeFile(uri, langCode);
      if (text) setTextInput(prev => (prev ? prev + ' ' + text : text));
    } catch {
      Alert.alert('Transcription failed', 'Please type your response instead.');
    } finally {
      setTranscribing(false);
    }
  };

  // ── v3.3: Pause session — calls API ─────────────────────────────────────
  const handlePause = async () => {
    try {
      if (sessionId) {
        await fetch(`${API_BASE}/api/fir/session/${sessionId}/pause`, { method: 'POST' });
        // Keep session_id in AsyncStorage so user can resume
      }
    } catch { /* best effort */ }
    router.back();
  };

  // ── v3.3: Back navigation ─────────────────────────────────────────────────
  const handleBack = async () => {
    if (!sessionId || isLoading) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/fir/session/${sessionId}/back`, { method: 'POST' });
      if (!res.ok) return;
      const data = await res.json();
      if (data.ok) {
        addMessage('bot', `↩ Going back...

${data.bot_message}`);
        setCurrentStage(data.stage || 'probe');
        setInputType(data.input_type || 'text');
        setQuickReplies(data.quick_replies || []);
        setSkipLabel(data.skip_label);
      }
    } catch { /* ignore */ }
    finally { setIsLoading(false); }
  };

  // ── Navigate to result ────────────────────────────────────────────────────
  useEffect(() => {
    if (draft) {
      const sid = sessionId;
      const d = draft;
      setTimeout(() => {
        router.push({
          pathname: '/fir-draft/result',
          params: { sessionId: sid || '', draft: d },
        });
      }, 800);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  // ── Selected language ──────────────────────────────────────────────────────
  const selectedLang = FIR_LANGUAGES.find(l => l.code === language) || FIR_LANGUAGES[0];

  // ─────────────────────────────────────────────────────────────────────────
  // PRE-SESSION: Language picker + Start button
  // ─────────────────────────────────────────────────────────────────────────
  if (!sessionStarted) {
    if (checkingResume) {
      return (
        <SafeAreaView style={[styles.root, { justifyContent: 'center', alignItems: 'center' }]}>
          <ActivityIndicator size="large" color={NAVY} />
        </SafeAreaView>
      );
    }
    return (
      <SafeAreaView style={styles.root}>
        <View style={styles.preHeader}>
          <Pressable onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
            <Ionicons name="arrow-back" size={22} color={NAVY} />
          </Pressable>
          <Text style={styles.preTitle}>FIR Draft Assistant</Text>
        </View>
        <ScrollView contentContainerStyle={styles.preBody}>
          {/* v3.3: Resume banner */}
          {savedSessionId && (
            <Pressable style={styles.resumeCard} onPress={() => resumeSession(savedSessionId)}>
              <Ionicons name="refresh-circle-outline" size={24} color={GOLD} />
              <View style={{ flex: 1, marginLeft: 10 }}>
                <Text style={styles.resumeTitle}>Continue your complaint</Text>
                <Text style={styles.resumeSubtitle}>You have an unfinished session. Tap to resume.</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={MUTED} />
            </Pressable>
          )}

          <View style={styles.welcomeCard}>
            <Text style={styles.welcomeIcon}>⚖️</Text>
            <Text style={styles.welcomeTitle}>Prepare your FIR draft</Text>
            <Text style={styles.welcomeSubtitle}>
              I will guide you step by step through a conversation to prepare a
              formal complaint letter ready to present at the police station.
            </Text>
            <View style={styles.welcomeFeatures}>
              {['Bilingual draft (English + your language)', 'GPS-pinned incident location', 'Evidence attachment support', 'BNS section suggestions'].map((f) => (
                <View key={f} style={styles.featureRow}>
                  <Text style={styles.featureDot}>✓</Text>
                  <Text style={styles.featureText}>{f}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* Language picker */}
          <Text style={styles.langLabel}>Draft language</Text>
          <View style={styles.langRow}>
            {FIR_LANGUAGES.map(l => (
              <Pressable
                key={l.code}
                style={[styles.langChip, language === l.code && styles.langChipActive]}
                onPress={() => saveLanguage(l.code)}
              >
                <Text style={[styles.langChipText, language === l.code && styles.langChipTextActive]}>
                  {l.native}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Disclaimer */}
          <View style={styles.disclaimer}>
            <Ionicons name="information-circle-outline" size={16} color={MUTED} />
            <Text style={styles.disclaimerText}>
              This produces a citizen draft for reference only — NOT a registered FIR.
              Present it at the police station for official registration.
            </Text>
          </View>

          {/* Start button */}
          <Pressable style={styles.startBtn} onPress={startSession}>
            <Text style={styles.startBtnText}>{savedSessionId ? 'Start New Complaint' : 'Start My Complaint'}</Text>
            <Ionicons name="arrow-forward" size={20} color="#fff" />
          </Pressable>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // SESSION ACTIVE: Chat UI
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={styles.root}>
      {/* v3.3: Emergency overlay */}
      {showEmergencyScreen && (
        <EmergencyOverlay
          numbers={emergencyNumbers}
          onContinue={() => {
            setShowEmergencyScreen(false);
            // If still in safety_gate, advance to narrative
            if (currentStage === 'safety_gate') {
              sendTurn(undefined, undefined, 'continue_safe');
            }
          }}
          onExit={() => {
            setShowEmergencyScreen(false);
            handlePause();
          }}
        />
      )}

      {/* Header */}
      <View style={styles.chatHeader}>
        <Pressable onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
          <Ionicons name="arrow-back" size={22} color={SURFACE} />
        </Pressable>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>FIR Draft Assistant</Text>
          <Text style={styles.headerLang}>{selectedLang.native}</Text>
        </View>
        {/* v3.3: Back probe button */}
        {currentStage === 'probe' && (
          <Pressable onPress={handleBack} style={styles.pauseBtn} hitSlop={12}>
            <Ionicons name="arrow-undo-outline" size={20} color={GOLD} />
          </Pressable>
        )}
        {/* Issue 9: Section menu button — visible when sections are available */}
        {suggestedSections.length > 0 && (
          <Pressable
            onPress={() => setShowSectionDrawer(true)}
            style={styles.pauseBtn}
            hitSlop={12}
          >
            <Ionicons name="list-outline" size={22} color={GOLD} />
          </Pressable>
        )}
        <Pressable onPress={handlePause} style={styles.pauseBtn} hitSlop={12}>
          <Ionicons name="bookmark-outline" size={20} color={GOLD} />
        </Pressable>
      </View>

      <KeyboardAvoidingView
        style={styles.flex1}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        {/* Messages */}
        <ScrollView
          ref={scrollRef}
          style={styles.messageList}
          contentContainerStyle={styles.messageListContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(msg => (
            <View
              key={msg.id}
              onLayout={(e) => { messageYsRef.current[msg.id] = e.nativeEvent.layout.y; }}
            >
              <MessageBubble role={msg.role} text={msg.text} />
            </View>
          ))}
          {isLoading && <TypingIndicator />}
          {/* v3.3: Save & Continue Later link */}
          {sessionId && !isLoading && inputType !== 'done' && (
            <Pressable style={styles.saveLaterRow} onPress={handlePause}>
              <Text style={styles.saveLaterText}>Save & continue later</Text>
            </Pressable>
          )}
        </ScrollView>

        {/* Input Area */}
        {!isLoading && sessionId && (
          <View style={[styles.inputArea, { paddingBottom: Math.max(insets.bottom, 8) }]}>
            {inputType === 'quick_reply' && (
              <QuickReplyChips
                replies={quickReplies}
                skipLabel={skipLabel}
                currentStage={currentStage}
                onSelect={(reply) => {
                  const lc = reply.toLowerCase();
                  // v3.3: Safety gate button detection
                  if (currentStage === 'safety_gate' && (lc.includes('no') || lc.includes('need help'))) {
                    sendTurn(undefined, undefined, 'not_safe');
                  } else if (lc.includes("safe now") && lc.includes("continue")) {
                    setShowEmergencyScreen(false);
                    sendTurn(undefined, undefined, 'continue_safe');
                  } else if (lc.includes('exit for now')) {
                    handlePause();
                  } else {
                    sendTurn(reply);
                  }
                }}
                onSkip={() => sendTurn(skipLabel || 'Skip')}
              />
            )}

            {(inputType === 'text' || inputType === 'voice_or_text') && (
              <TextInputArea
                value={textInput}
                onChange={setTextInput}
                onSend={(t) => { if (t.trim()) sendTurn(t.trim()); }}
                onSkip={skipLabel ? () => sendTurn(undefined, undefined, 'skip') : undefined}
                skipLabel={skipLabel}
                showVoice={inputType === 'voice_or_text'}
                isRecording={isRecording}
                transcribing={transcribing}
                onStartRecord={startRecording}
                onStopRecord={stopRecording}
              />
            )}

            {inputType === 'gps' && gpsAvailable && (
              <GPSWidget
                onGetGPS={handleGetGPS}
                onSkip={() => sendTurn(undefined, undefined, 'skip')}
                skipLabel={skipLabel}
              />
            )}

            {inputType === 'gps' && !gpsAvailable && (
              /* Web fallback: typed place input when GPS is unavailable */
              <TextInputArea
                value={textInput}
                onChange={setTextInput}
                onSend={(t) => { if (t.trim()) sendTurn(t.trim()); }}
                onSkip={skipLabel ? () => sendTurn(undefined, undefined, 'skip') : undefined}
                skipLabel={skipLabel}
                showVoice={false}
                isRecording={false}
                transcribing={false}
                onStartRecord={() => {}}
                onStopRecord={() => {}}
              />
            )}

            {inputType === 'evidence' && (
              <EvidenceWidget
                files={evidenceFiles}
                uploading={uploadingEvidence}
                onPick={handlePickEvidence}
                onDone={() => sendTurn(undefined, undefined, 'upload_done')}
                onSkip={() => sendTurn(undefined, undefined, 'skip')}
                skipLabel={skipLabel}
                onRemove={handleRemoveEvidence}
                onCaptionChange={handleCaptionChange}
              />
            )}

            {inputType === 'confirm' && (
              <ConfirmButtons
                confirmLabel={quickReplies[0] || 'Yes, proceed'}
                cancelLabel={quickReplies[1] || 'Go back'}
                onConfirm={() => sendTurn(quickReplies[0] || 'Yes')}
                onCancel={() => sendTurn(quickReplies[1] || 'No')}
              />
            )}

            {inputType === 'done' && (
              <Pressable
                style={styles.viewDraftBtn}
                onPress={() => router.push({
                  pathname: '/fir-draft/result',
                  params: { sessionId: sessionId || '', draft: draft || '' },
                })}
              >
                <Ionicons name="document-text-outline" size={22} color="#fff" />
                <Text style={styles.viewDraftBtnText}>View Your FIR Draft</Text>
              </Pressable>
            )}
          </View>
        )}
      </KeyboardAvoidingView>

      {/* Issue 9: Section Drawer */}
      <FirSectionDrawer
        visible={showSectionDrawer}
        onClose={() => setShowSectionDrawer(false)}
        suggestedSections={suggestedSections}
        droppedSections={droppedSections}
        onJump={() => {
          if (sectionMsgId && messageYsRef.current[sectionMsgId] !== undefined) {
            scrollRef.current?.scrollTo({ y: Math.max(0, messageYsRef.current[sectionMsgId] - 20), animated: true });
          }
          setShowSectionDrawer(false);
        }}
      />
    </SafeAreaView>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MessageBubble({ role, text }: { role: 'bot' | 'user'; text: string }) {
  const isBot = role === 'bot';
  return (
    <View style={[styles.bubbleWrap, isBot ? styles.bubbleWrapBot : styles.bubbleWrapUser]}>
      {isBot && (
        <View style={styles.botAvatar}>
          <Text style={styles.botAvatarText}>⚖</Text>
        </View>
      )}
      <View style={[styles.bubble, isBot ? styles.bubbleBot : styles.bubbleUser]}>
        <Text style={[styles.bubbleText, isBot ? styles.bubbleTextBot : styles.bubbleTextUser]}>
          {text}
        </Text>
      </View>
    </View>
  );
}

function TypingIndicator() {
  return (
    <View style={[styles.bubbleWrap, styles.bubbleWrapBot]}>
      <View style={styles.botAvatar}>
        <Text style={styles.botAvatarText}>⚖</Text>
      </View>
      <View style={[styles.bubble, styles.bubbleBot, { paddingVertical: 10, paddingHorizontal: 16 }]}>
        <ActivityIndicator size="small" color={GOLD} />
      </View>
    </View>
  );
}

function QuickReplyChips({
  replies, skipLabel, onSelect, onSkip, currentStage,
}: { replies: string[]; skipLabel?: string; onSelect: (r: string) => void; onSkip: () => void; currentStage?: string }) {
  return (
    <View style={styles.chipsWrap}>
      {replies.map(r => {
        const isNoBtn = currentStage === 'safety_gate' && (r.toLowerCase().includes('no') || r.toLowerCase().includes('need help'));
        return (
          <Pressable
            key={r}
            style={[styles.chip, isNoBtn && styles.chipDanger]}
            onPress={() => onSelect(r)}
          >
            <Text style={[styles.chipText, isNoBtn && styles.chipTextDanger]}>{r}</Text>
          </Pressable>
        );
      })}
      {skipLabel && (
        <Pressable style={[styles.chip, styles.chipSkip]} onPress={onSkip}>
          <Text style={[styles.chipText, styles.chipTextSkip]}>{skipLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}

function TextInputArea({
  value, onChange, onSend, onSkip, skipLabel, showVoice,
  isRecording, transcribing, onStartRecord, onStopRecord,
}: {
  value: string; onChange: (v: string) => void; onSend: (v: string) => void;
  onSkip?: () => void; skipLabel?: string;
  showVoice: boolean; isRecording: boolean; transcribing: boolean;
  onStartRecord: () => void; onStopRecord: () => void;
}) {
  return (
    <View>
      <View style={styles.textRow}>
        <TextInput
          testID="fir-text-input"
          style={styles.textBox}
          value={value}
          onChangeText={onChange}
          placeholder="Type your response here…"
          placeholderTextColor={MUTED}
          multiline
          maxLength={2000}
        />
        {showVoice && (
          <Pressable
            style={[styles.micBtn, isRecording && styles.micBtnActive]}
            onPressIn={onStartRecord}
            onPressOut={onStopRecord}
          >
            {transcribing
              ? <ActivityIndicator size="small" color={SURFACE} />
              : <Ionicons name={isRecording ? 'mic' : 'mic-outline'} size={22} color={SURFACE} />}
          </Pressable>
        )}
        <Pressable
          testID="fir-send-btn"
          style={[styles.sendBtn, !value.trim() && styles.sendBtnDisabled]}
          onPress={() => onSend(value)}
          disabled={!value.trim()}
        >
          <Ionicons name="send" size={18} color="#fff" />
        </Pressable>
      </View>
      {onSkip && skipLabel && (
        <Pressable style={styles.skipRow} onPress={onSkip}>
          <Text style={styles.skipText}>{skipLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}

function GPSWidget({
  onGetGPS, onSkip, skipLabel,
}: { onGetGPS: () => void; onSkip: () => void; skipLabel?: string }) {
  return (
    <View style={styles.widgetWrap}>
      <Text style={styles.widgetHint}>
        Your precise GPS location helps police identify the exact spot
      </Text>
      <Pressable style={styles.gpsBtn} onPress={onGetGPS}>
        <Ionicons name="location" size={22} color="#fff" />
        <Text style={styles.gpsBtnText}>Get GPS Location</Text>
      </Pressable>
      <Pressable style={styles.skipRow} onPress={onSkip}>
        <Text style={styles.skipText}>{skipLabel || 'No, text description is enough'}</Text>
      </Pressable>
    </View>
  );
}

function EvidenceWidget({
  files, uploading, onPick, onDone, onSkip, skipLabel, onRemove, onCaptionChange,
}: {
  files: UploadedFile[]; uploading: boolean;
  onPick: () => void; onDone: () => void; onSkip: () => void;
  skipLabel?: string;
  onRemove?: (fileId: string) => void;
  onCaptionChange?: (fileId: string, caption: string) => void;
}) {
  return (
    <View style={styles.widgetWrap}>
      {files.length > 0 && (
        <View style={styles.evidenceList}>
          {files.map(f => {
            const isImage = f.file_type === 'image' || (f.content_type || '').startsWith('image/');
            const isVideo = f.file_type === 'video' || (f.content_type || '').startsWith('video/');
            return (
              <View key={f.file_id} style={styles.evidenceItemWrap}>
                <View style={styles.evidenceItem}>
                  {/* Thumbnail */}
                  {isImage && f.local_uri ? (
                    <Image
                      source={{ uri: f.local_uri }}
                      style={styles.evidenceThumb}
                      resizeMode="cover"
                    />
                  ) : (
                    <Ionicons
                      name={isImage ? 'image-outline' : isVideo ? 'videocam-outline' : 'document-outline'}
                      size={20} color={NAVY}
                      style={{ marginRight: 4 }}
                    />
                  )}
                  <Text style={styles.evidenceItemText} numberOfLines={1}>{f.filename}</Text>
                  {/* × remove button */}
                  {onRemove && (
                    <Pressable
                      onPress={() => onRemove(f.file_id)}
                      style={styles.evidenceRemoveBtn}
                      hitSlop={8}
                    >
                      <Ionicons name="close-circle" size={18} color={RED} />
                    </Pressable>
                  )}
                </View>
                {/* Issue 17: Caption input */}
                {onCaptionChange && (
                  <TextInput
                    style={styles.captionInput}
                    value={f.caption || ''}
                    onChangeText={(text) => onCaptionChange(f.file_id, text)}
                    placeholder="Add a caption (e.g. broken window at entry)"
                    placeholderTextColor={MUTED}
                    returnKeyType="done"
                    maxLength={200}
                  />
                )}
              </View>
            );
          })}
        </View>
      )}
      <View style={styles.evidenceBtns}>
        <Pressable
          style={[styles.evidenceAddBtn, uploading && { opacity: 0.6 }]}
          onPress={onPick}
          disabled={uploading}
        >
          {uploading
            ? <ActivityIndicator size="small" color={NAVY} />
            : <Ionicons name="attach" size={20} color={NAVY} />}
          <Text style={styles.evidenceAddText}>
            {uploading ? 'Uploading…' : `Add Files${files.length > 0 ? ` (${files.length})` : ''}`}
          </Text>
        </Pressable>
        {files.length > 0 && (
          <Pressable style={styles.evidenceDoneBtn} onPress={onDone}>
            <Text style={styles.evidenceDoneText}>Done ({files.length})</Text>
          </Pressable>
        )}
      </View>
      <Pressable style={styles.skipRow} onPress={onSkip}>
        <Text style={styles.skipText}>{skipLabel || 'No evidence to upload'}</Text>
      </Pressable>
    </View>
  );
}

function ConfirmButtons({
  confirmLabel, cancelLabel, onConfirm, onCancel,
}: { confirmLabel: string; cancelLabel: string; onConfirm: () => void; onCancel: () => void }) {
  return (
    <View style={styles.confirmWrap}>
      <Pressable style={styles.confirmYes} onPress={onConfirm}>
        <Text style={styles.confirmYesText}>{confirmLabel}</Text>
      </Pressable>
      <Pressable style={styles.confirmNo} onPress={onCancel}>
        <Text style={styles.confirmNoText}>{cancelLabel}</Text>
      </Pressable>
    </View>
  );
}

// ── Emergency Overlay (v3.3) ─────────────────────────────────────────────────
function EmergencyOverlay({
  numbers, onContinue, onExit,
}: { numbers: Array<{label: string; number: string}>; onContinue: () => void; onExit: () => void }) {
  const handleCall = (num: string) => {
    Linking.openURL(`tel:${num}`).catch(() =>
      Alert.alert('Cannot call', `Please manually dial ${num}`)
    );
  };
  return (
    <View style={eStyles.overlay}>
      <View style={eStyles.card}>
        <Text style={eStyles.title}>⚠️ Emergency Numbers</Text>
        <Text style={eStyles.subtitle}>
          If you are in immediate danger, please call for help first.
        </Text>
        {numbers.map(n => (
          <Pressable key={n.number} style={eStyles.callBtn} onPress={() => handleCall(n.number)}>
            <Ionicons name="call" size={22} color="#fff" />
            <View style={{ marginLeft: 10 }}>
              <Text style={eStyles.callLabel}>{n.label}</Text>
              <Text style={eStyles.callNum}>{n.number}</Text>
            </View>
          </Pressable>
        ))}
        <Pressable style={eStyles.continueBtn} onPress={onContinue}>
          <Text style={eStyles.continueBtnText}>{"I'm safe now \u2014 continue filing"}</Text>
        </Pressable>
        <Pressable style={eStyles.exitBtn} onPress={onExit}>
          <Text style={eStyles.exitBtnText}>Exit for now (session saved)</Text>
        </Pressable>
      </View>
    </View>
  );
}

const eStyles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.82)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 9999,
    paddingHorizontal: 20,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  title: { fontSize: 20, fontWeight: '700', color: '#B91C1C', marginBottom: 8, textAlign: 'center' },
  subtitle: { fontSize: 14, color: '#374151', marginBottom: 16, textAlign: 'center', lineHeight: 20 },
  callBtn: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#B91C1C', borderRadius: 10,
    padding: 14, marginBottom: 10,
  },
  callLabel: { color: '#fff', fontSize: 13, fontWeight: '600' },
  callNum: { color: '#fecaca', fontSize: 20, fontWeight: '700', letterSpacing: 1 },
  continueBtn: {
    backgroundColor: '#14365A', borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginTop: 8,
  },
  continueBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  exitBtn: { paddingVertical: 12, alignItems: 'center', marginTop: 6 },
  exitBtnText: { color: '#6B7280', fontSize: 14 },
});

// ── Styles ────────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: SURFACE },
  flex1: { flex: 1 },

  // Pre-session
  preHeader: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: BORDER,
  },
  preTitle: { fontSize: 17, fontWeight: '700', color: NAVY, marginLeft: 12 },
  preBody: { padding: 20, paddingBottom: 40 },
  welcomeCard: {
    backgroundColor: CREAM, borderRadius: 16, padding: 24,
    alignItems: 'center', marginBottom: 24,
  },
  welcomeIcon: { fontSize: 40, marginBottom: 12 },
  welcomeTitle: { fontSize: 20, fontWeight: '700', color: NAVY, textAlign: 'center', marginBottom: 8 },
  welcomeSubtitle: { fontSize: 14, color: MUTED, textAlign: 'center', lineHeight: 20, marginBottom: 16 },
  welcomeFeatures: { width: '100%', gap: 8 },
  featureRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  featureDot: { fontSize: 14, color: GREEN, fontWeight: '700', width: 16 },
  featureText: { fontSize: 13, color: NAVY, flex: 1 },
  langLabel: { fontSize: 14, fontWeight: '600', color: NAVY, marginBottom: 10 },
  langRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 20 },
  langChip: {
    paddingHorizontal: 14, paddingVertical: 8,
    borderRadius: 20, borderWidth: 1.5, borderColor: BORDER,
    backgroundColor: SURFACE,
  },
  langChipActive: { backgroundColor: NAVY, borderColor: NAVY },
  langChipText: { fontSize: 13, color: MUTED, fontWeight: '500' },
  langChipTextActive: { color: '#fff' },
  disclaimer: {
    flexDirection: 'row', gap: 8, backgroundColor: '#F0F4FF',
    borderRadius: 10, padding: 12, marginBottom: 24,
  },
  disclaimerText: { fontSize: 12, color: MUTED, flex: 1, lineHeight: 17 },
  startBtn: {
    backgroundColor: NAVY, borderRadius: 14, paddingVertical: 16,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10,
  },
  startBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  // Chat header
  chatHeader: {
    backgroundColor: NAVY, flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 16, paddingVertical: 12, gap: 12,
  },
  headerCenter: { flex: 1 },
  headerTitle: { fontSize: 15, fontWeight: '700', color: '#fff' },
  headerLang: { fontSize: 12, color: GOLD },
  backBtn: { padding: 4 },
  pauseBtn: { padding: 4 },

  // Messages
  messageList: { flex: 1, backgroundColor: '#F7F5F0' },
  messageListContent: { paddingHorizontal: 12, paddingTop: 16, paddingBottom: 8, gap: 12 },
  bubbleWrap: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  bubbleWrapBot: { justifyContent: 'flex-start' },
  bubbleWrapUser: { justifyContent: 'flex-end' },
  botAvatar: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: NAVY, alignItems: 'center', justifyContent: 'center',
    marginBottom: 2,
  },
  botAvatarText: { fontSize: 14 },
  bubble: { maxWidth: '80%', borderRadius: 16, paddingHorizontal: 14, paddingVertical: 10 },
  bubbleBot: { backgroundColor: NAVY, borderBottomLeftRadius: 4 },
  bubbleUser: { backgroundColor: CREAM, borderBottomRightRadius: 4 },
  bubbleText: { fontSize: 14, lineHeight: 20 },
  bubbleTextBot: { color: '#fff' },
  bubbleTextUser: { color: NAVY },

  // Input area
  inputArea: {
    backgroundColor: SURFACE, borderTopWidth: 1, borderTopColor: BORDER,
    paddingHorizontal: 12, paddingTop: 10,
  },

  // Quick reply chips
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingBottom: 4 },
  chip: {
    borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10,
    backgroundColor: NAVY, borderWidth: 0,
  },
  chipSkip: { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: BORDER },
  chipText: { fontSize: 13, color: '#fff', fontWeight: '600' },
  chipTextSkip: { color: MUTED },

  // Text input
  textRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginBottom: 4 },
  textBox: {
    flex: 1, borderWidth: 1.5, borderColor: BORDER, borderRadius: 12,
    paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: NAVY,
    maxHeight: 120, backgroundColor: SURFACE,
  },
  micBtn: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: NAVY, alignItems: 'center', justifyContent: 'center',
  },
  micBtnActive: { backgroundColor: RED },
  sendBtn: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: NAVY, alignItems: 'center', justifyContent: 'center',
  },
  sendBtnDisabled: { backgroundColor: BORDER },
  skipRow: { alignItems: 'center', paddingVertical: 8 },
  skipText: { fontSize: 13, color: MUTED, textDecorationLine: 'underline' },

  // GPS widget
  widgetWrap: { paddingBottom: 4, gap: 8 },
  widgetHint: { fontSize: 12, color: MUTED, textAlign: 'center' },
  gpsBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: NAVY, borderRadius: 12, paddingVertical: 14,
  },
  gpsBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },

  // Evidence widget
  evidenceList: { gap: 6, marginBottom: 4 },
  evidenceItemWrap: {
    borderRadius: 8, overflow: 'hidden',
    borderWidth: 1, borderColor: '#D1DCE8',
    marginBottom: 2,
  },
  evidenceItem: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: CREAM, paddingHorizontal: 10, paddingVertical: 6,
  },
  // Issue 17: caption input below each evidence thumbnail
  captionInput: {
    borderTopWidth: 1, borderTopColor: '#D1DCE8',
    paddingHorizontal: 10, paddingVertical: 7,
    fontSize: 12, color: NAVY,
    backgroundColor: '#FAFAF8',
    fontStyle: 'italic',
  },
  evidenceItemText: { fontSize: 13, color: NAVY, flex: 1 },
  evidenceBtns: { flexDirection: 'row', gap: 8 },
  evidenceAddBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    borderWidth: 1.5, borderColor: NAVY, borderRadius: 10, paddingVertical: 10, borderStyle: 'dashed',
  },
  evidenceAddText: { fontSize: 14, color: NAVY, fontWeight: '600' },
  evidenceDoneBtn: {
    backgroundColor: GREEN, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 16,
    alignItems: 'center', justifyContent: 'center',
  },
  evidenceDoneText: { color: '#fff', fontSize: 14, fontWeight: '700' },

  // Confirm
  confirmWrap: { gap: 8, paddingBottom: 4 },
  confirmYes: {
    backgroundColor: GREEN, borderRadius: 12, paddingVertical: 14,
    alignItems: 'center',
  },
  confirmYesText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  confirmNo: {
    backgroundColor: 'transparent', borderWidth: 1.5, borderColor: BORDER,
    borderRadius: 12, paddingVertical: 12, alignItems: 'center',
  },
  confirmNoText: { color: MUTED, fontSize: 14 },

  // View draft
  viewDraftBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10,
    backgroundColor: NAVY, borderRadius: 14, paddingVertical: 16, marginBottom: 4,
  },
  viewDraftBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  // v3.3: New styles
  resumeCard: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: NAVY, borderRadius: 12, padding: 14, marginBottom: 12,
  },
  resumeTitle: { color: GOLD, fontSize: 14, fontWeight: '700' },
  resumeSubtitle: { color: '#94a3b8', fontSize: 12, marginTop: 2 },
  saveLaterRow: { alignItems: 'center', paddingVertical: 8, marginTop: 4 },
  saveLaterText: { color: MUTED, fontSize: 13, textDecorationLine: 'underline' },
  evidenceThumb: { width: 36, height: 36, borderRadius: 6, marginRight: 4 },
  evidenceRemoveBtn: { padding: 2 },
  chipDanger: { backgroundColor: '#FEF2F2', borderColor: '#B91C1C' },
  chipTextDanger: { color: '#B91C1C' },
});
