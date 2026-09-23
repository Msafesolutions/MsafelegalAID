# Icon clipping and browser voice permission error — September 2026

## User reports
- Bottom navigation cropped on iPhone; requested checking icon clipping on other screens.
- Many users encounter Safari's "request is not allowed by the user agent or the platform" error in FIR draft.

## Root causes
- 64pt navigation minus 16pt bar padding and border left 47pt, below the icon + label + internal button padding requirement. Hidden History also retained an unused tab slot.
- Installed expo-audio web player's `play(): void` discards `HTMLMediaElement.play()`'s promise. Synchronous catches cannot handle Safari autoplay rejection. Direct promise ownership now replaces that web player in both conversational screens.
- Additional check found `free_narrative` resume was rendered as text-only, hiding the microphone.

## Verification
- `cd /app/frontend && node --test tests/voice-playback.cjs`: **5/5 passed** (blocked playback/retry; stop during pending play; decode error feedback/cleanup; native synchronous player contract; browser promise propagation).
- Browser viewport checks: 320 and 390pt; Ask, Rights, Saved, Lookup, Advocate, Settings. Six equal-width visible tabs; no horizontal page overflow. Screenshot checks of labels/icons and disclaimer separation.
- History via its header button remains reachable without an empty tab slot. Drafts and draft history navigation checked.
- Main chat and FIR simulated Safari NotAllowedError: inline Play voice notice; retry starts already-prepared audio. No uncaught promise rejections. No blanket suppression.
- FIR denied microphone: inline guidance, text field remains editable, no unhandled errors.
- Start -> safe -> free narrative -> Save -> reopen -> Continue complaint: microphone and conversation restored. An initial test uncovered the old text-only resume; corrected exact backend stage name and final retest passed.
- Test audio bytes were supplied only within browser automation, avoiding paid synthesis calls. App integrations were not replaced. Tests used existing `voicetest2026@example.com`; no credentials changed.
- Last successful browser report: `/root/.emergent/automation_output/20260923_065315/console_20260923_065315.log` (tool environment).

## Limits / follow-up
- Physical iPhone Safari and native Android/iOS audio hardware remain for user confirmation. No real provider-generated speech or microphone transcription billed/tested this pass.
- Runtime checks covered the primary screens above; account deletion, completed FIR output, public intake forms and payment flows were not exercised. Their icon styles were included in the source scan.
- JavaScript lint: modified navigation/shared audio/components pass; FIR retains three existing array-style warnings only.
- Full `tsc --noEmit` still reports unrelated existing diagnostics: optional API_BASE passed to two main chat voice functions; missing legacy theme/style keys in chat/settings/login; intake speech listener typing; WhisperCloudSTT.start return type. No TypeScript errors remain in new player/notice/nav or modified FIR screen. Do not describe whole-project typecheck as clean.
- No testing subagent used, respecting the user's budget request. No Phase B work.