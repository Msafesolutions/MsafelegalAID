/**
 * DHARA FIR Interview Engine — Conversational UI (v3)
 * Stage-based chat interface that guides citizens through FIR preparation.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, StyleSheet,
  ActivityIndicator, Platform, Alert, KeyboardAvoidingView, Linking,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
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
  slots_preview?: any;
  draft?: string;
  completed?: boolean;
  safety_flags?: string[];
}
interface UploadedFile {
  file_id: string;
  filename: string;
  file_type: string;
}

function msgId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function FirDraftScreen() {
  const router = useRouter();
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

  // ── Language ───────────────────────────────────────────────────────────────
  const [language, setLanguage] = useState('en');
  const [sessionStarted, setSessionStarted] = useState(false);

  // ── Voice recording ────────────────────────────────────────────────────────
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [isRecording, setIsRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);

  const scrollRef = useRef<ScrollView>(null);

  // ── Load saved language ────────────────────────────────────────────────────
  useEffect(() => {
    AsyncStorage.getItem(FIR_LANG_KEY).then((saved) => {
      if (saved) setLanguage(saved);
    });
  }, []);

  const saveLanguage = async (code: string) => {
    setLanguage(code);
    await AsyncStorage.setItem(FIR_LANG_KEY, code);
  };

  // ── Auto-scroll to bottom ──────────────────────────────────────────────────
  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  }, [messages, isLoading]);

  // ── Add message helper ─────────────────────────────────────────────────────
  const addMessage = useCallback((role: 'bot' | 'user', text: string) => {
    setMessages(prev => [...prev, {
      id: msgId(), role, text,
      timestamp: new Date().toISOString(),
    }]);
  }, []);

  // ── Apply turn response ───────────────────────────────────────────────────
  const applyTurn = useCallback((res: TurnResponse) => {
    if (res.bot_message) {
      addMessage('bot', res.bot_message);
    }
    setInputType(res.input_type || 'text');
    setQuickReplies(res.quick_replies || []);
    setSkipLabel(res.skip_label);
    if (res.draft) setDraft(res.draft);
  }, [addMessage]);

  // ── Create session ─────────────────────────────────────────────────────────
  const startSession = async () => {
    if (!language) return;
    setIsLoading(true);
    setSessionStarted(true);
    setMessages([]);
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
      applyTurn(data);
    } catch {
      Alert.alert('Error', 'Could not start session. Please check your connection.');
      setSessionStarted(false);
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

  // ── Evidence upload ────────────────────────────────────────────────────────
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
          if (res.ok) {
            const data = await res.json();
            if (data.file) uploaded.push(data.file);
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

  // ── Pause session ──────────────────────────────────────────────────────────
  const handlePause = () => {
    Alert.alert(
      'Save & Continue Later',
      'Your session is automatically saved. You can resume it later.',
      [{ text: 'OK', onPress: () => router.back() }],
    );
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
    return (
      <SafeAreaView style={styles.root}>
        <View style={styles.preHeader}>
          <Pressable onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
            <Ionicons name="arrow-back" size={22} color={NAVY} />
          </Pressable>
          <Text style={styles.preTitle}>FIR Draft Assistant</Text>
        </View>
        <ScrollView contentContainerStyle={styles.preBody}>
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
            <Text style={styles.startBtnText}>Start My Complaint</Text>
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
      {/* Header */}
      <View style={styles.chatHeader}>
        <Pressable onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
          <Ionicons name="arrow-back" size={22} color={SURFACE} />
        </Pressable>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>FIR Draft Assistant</Text>
          <Text style={styles.headerLang}>{selectedLang.native}</Text>
        </View>
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
            <MessageBubble key={msg.id} role={msg.role} text={msg.text} />
          ))}
          {isLoading && <TypingIndicator />}
        </ScrollView>

        {/* Input Area */}
        {!isLoading && sessionId && (
          <View style={[styles.inputArea, { paddingBottom: Math.max(insets.bottom, 8) }]}>
            {inputType === 'quick_reply' && (
              <QuickReplyChips
                replies={quickReplies}
                skipLabel={skipLabel}
                onSelect={(reply) => sendTurn(reply)}
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
  replies, skipLabel, onSelect, onSkip,
}: { replies: string[]; skipLabel?: string; onSelect: (r: string) => void; onSkip: () => void }) {
  return (
    <View style={styles.chipsWrap}>
      {replies.map(r => (
        <Pressable key={r} style={styles.chip} onPress={() => onSelect(r)}>
          <Text style={styles.chipText}>{r}</Text>
        </Pressable>
      ))}
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
  files, uploading, onPick, onDone, onSkip, skipLabel,
}: {
  files: UploadedFile[]; uploading: boolean;
  onPick: () => void; onDone: () => void; onSkip: () => void; skipLabel?: string;
}) {
  return (
    <View style={styles.widgetWrap}>
      {files.length > 0 && (
        <View style={styles.evidenceList}>
          {files.map(f => (
            <View key={f.file_id} style={styles.evidenceItem}>
              <Ionicons
                name={f.file_type === 'image' ? 'image-outline' : f.file_type === 'video' ? 'videocam-outline' : 'document-outline'}
                size={16} color={NAVY}
              />
              <Text style={styles.evidenceItemText} numberOfLines={1}>{f.filename}</Text>
            </View>
          ))}
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
  evidenceItem: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: CREAM, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6,
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
});
