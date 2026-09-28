# Dhara (formerly Gandhikar) — PRD

## September 2026 — P0 APK/web stabilization
- Corrected the Expo SDK 54 incompatibility: `expo-crypto` is now pinned to `~15.0.9` through Expo's installer. The prior `57.0.3` package was incompatible with the SDK 54 native runtime and was a credible APK startup-crash cause.
- Added a root React error boundary around providers and navigation. Recoverable JavaScript/provider render failures now show a safe Dhara retry screen rather than terminating into a blank startup view.
- Claude Sonnet 4.6 remains the configured default model (`claude-sonnet-4-6`); it was not changed to an older model.
- The supplied Firebase `google-services.json` was not present in the job assets. `android.googleServicesFile` was intentionally not added because a nonexistent file would make the Android build fail. Add this only when the actual Firebase configuration file is supplied.
- Web export now uses Expo static output, allowing `app/+html.tsx` to bake GA4 and Cloudflare Web Analytics into the generated files. Verified a clean `npx expo export --platform web --clear`; `/app/downloads/dhara_web_build_v18.zip` passed archive validation.
- Backend and Expo services restarted; `/health` and `/api/health` both returned 200. Web preview rendered successfully at phone dimensions. A fresh V18 native build is still required to verify actual Android startup; desktop web preview cannot certify an APK.
- **Deferred under the user-selected P0 stability cap:** router extraction of the 4,343-line backend. This is a distinct, high-regression-risk refactor and has not been represented as completed.

## Vision
A dignified, free, bilingual+multilingual AI legal companion for every Indian citizen. Empower — never threaten. Named after Mahatma Gandhi. Truth, non-violence, rights.

## Current scope — September 2026 maintenance
- **26 September: latest Home mockup + missing-person photos/GPS.** Latest user request supersedes the earlier Profile/Conversations-tab arrangement: exactly five visible tabs **Home · Rights · Ask AI · Complaints · Lookup**, centred gold Ask AI, Profile through the Home/Lookup headers. No export, APK/IPA build or release performed.
- Home now has a compact gold Pro header chip, compact quick-help strip, the missing-person entry, only the latest unfinished FIR card (no fabricated case), See all to the dedicated Complaints tab, and a visible question field that hands text to Ask AI for confirmation. Complaint cards use compact rows with workflow-step progress. Complaints tab retains the full FIR list and the account's device-local missing-person draft shortcut. Lookup hub links Vote, BNS/IPC section search, existing court-case lookup and advocates.
- Chat no longer includes the FIR card/report list or saved-reports sheet. Header keeps New Chat/history; conversation reading area fills available height and composer remains separate without a screen-percentage minimum height. Existing answer/voice flows retained.
- Added optional missing-person attachments screen (`app/missing/attachments.tsx`, `src/missing/*`). Explicit photo-upload agreement; picker/camera; up to 3 photos, 5 MB each; private object storage via existing wrapper; authenticated owner-only retrieval and detach. Backend validates/re-encodes JPEG/PNG/WebP, limits dimensions and strips EXIF. `backend/missing_media.py` adds `/api/missing/{draft_id}/photos` routes and Pydantic metadata responses; MongoDB `missing_media` stores only owner/attachment metadata, never answers or GPS. Account cleanup revokes metadata access. Storage has no physical-delete API: removal detaches/revokes access and UI discloses a storage copy may remain.
- GPS is optional foreground-only capture with explicit last-seen confirmation, accuracy label, manual coordinate validation, map link and removal; it does NOT track the missing person. Text/GPS remain in account-scoped AsyncStorage. Missing interview resumes saved progress, surfaces save errors, and uses language.code correctly. Result includes actual attached photos and confirmed coordinates/map link in on-device PDF; web retains printable HTML/Save-as-PDF flow. No-photo drafts do not require an attachment-network call to generate.
- Centralised API resolver (`src/apiBase.ts`, `app.config.js`) uses Expo Constants: exact configured preview host and same backend host use relative `/api`; native/external Scala keep configured production base. Production `.env` URL and protected framework variables UNCHANGED; no credential/session logic changed. A stale Metro-generated starter manifest was diagnosed from served bundle and its generated cache rebuilt (no protected config edits).
- Incidental Vote-route blockers fixed: undefined `setAnswers` reset, language object vs code, `/api/voter/pdf` prefix, native SDK54 legacy file-system import.
- **Verified:** phone preview sign-in and navigation, 390×844 and 320×568 layouts, no horizontal overflow, no chat reading/composer overlap; text question handoff; real private photo upload, GPS permission simulation + confirmation, all 18 interview questions, printable output containing photo and coordinates/map link, attachments restored on return. Screenshots/logs: `/root/.emergent/automation_output/20260926_142659/`. Backend regression: **12 passed** (`test_reports/pytest/iteration_22_retest.xml`), including anonymous 401, owner reads, cross-user read/delete 404, bad image/5MB/max3 limits, detach, Vote PDF. Initial report `/app/test_reports/iteration_22.json` had removal status bug (fixed and retested) and incomplete frontend run; manual flow above then passed. New files lint clean; pre-existing unrelated TS diagnostics remain.
- **Budget instruction:** User now says “dont run to many tests as the minor changes consumed 60 credits”. Stop further test runs for this task. Do not start new work, exports or releases without user direction. No paid AI/voice/payment checks were performed in this pass.
- **P0:** No known blocker in the newly verified preview flow. **P1:** Physical iOS/Android camera, GPS permissions, keyboard and native PDF/share still require user/device confirmation; existing eCourts party lookup and regional-language `save_assistant` search issues from handoff remain outside this UI scope. **P2:** Language coverage for new attachment controls and existing legacy TS issues; no broad refactor. Native builds/Scala export remain pending explicit approval.
- **23 September: screenshot-matched Home + app-wide navy / white / gold.** User: “UI should be like this, make blue to navy blue, white text and orange to gold.” Confirmed Home layout plus shared app-wide colours, dark text on light cards. Reference: `https://customer-assets-39nsmqrw.emergentagent.net/job_ba9413f5-ba2c-460c-bae3-9971531c0434/artifacts/59ljw69k_image.png`.
- Added `app/(tabs)/home.tsx` with branded navy header, language/profile actions, greeting, Rights/Advocate/Emergency quick help, real saved complaint previews (latest unfinished + completed), all-complaints list, and Pro entry using existing plans (no fabricated price). Progress is labelled by workflow step rather than fake percentages. Empty/loading/error/retry states included. Home legal disclaimer remains non-dismissible in scroll content above navigation; other tabs retain its fixed footer placement.
- Five accessible navigation buttons: Home, Rights, gold Ask AI, Locate, Profile. Existing chat stays in `(tabs)/index.tsx`; login/onboarding/consent now land on `/(tabs)/home`. Saved, Legal Lookup and History remain accessible from Profile. Language changes from Home return to Home without sending signed-in users to login.
- Shared `theme.ts` palette: navy `#0B1D3A`, lighter navy `#152E59`, gold `#D4AF37`, white on navy, dark text on light cards. Migrated old blue/orange brand overrides throughout FIR, lookup, advocate/intake, chat, privacy and native splash configuration. No protected files or environment values changed.
- **Related navigation fixes verified:** FIR draft endpoint now reads engine's canonical `draft` with legacy `draft_text` fallback, after unchanged ownership checks. Existing 4,271-character draft returns correctly; anonymous 401 and another account 403 verified. Paused Continue now auto-restores the interview once instead of showing a second resume prompt; failure preserves saved session and shows retry instructions. Empty-string conditional render warnings in Pro/Settings/FIR removed.
- **Verification:** report `/app/test_reports/iteration_21.json` identified paused-resume and text-node issues; both then fixed and manually rechecked through phone preview. Final screenshots/logs `/root/.emergent/automation_output/20260923_213430/`: Home 390×844, Home 320×568, resumed FIR. Resume works from Home and See all; full draft view works; all five tabs, help links, language, Pro and Profile deep-links work; Settings Terms modal opens/closes; no horizontal overflow, navigation targets ≥44 points; final console errors empty. No paid AI/voice/payment or emergency-call tests. No production flows mocked by this change. New-feature type checks/lint clean; 11 unrelated legacy TS diagnostics and 3 existing array-style FIR lint warnings remain. Physical iOS/Android review remains pending.
- **Follow-up backlog (not part of this visual request):** translate all new Home copy, review regional terms, durable offline consent audit synchronization, split legacy 3,000-line chat / 1,800-line FIR modules, Phase B incident modules, evidence E2E validation. No broad legacy voice refactor attempted.
- **23 September: consent-screen blockage and visible Terms & Conditions** — user supplied a recording and approved focusing on Continue + readable terms, keeping optional consent optional. This pass does not expand Phase B.
- Fixed mismatched consent text keys (age options, Continue, optional purposes, never-collect sections were blank), a nonexistent storage-key import, and consent-return loops. Shared account-scoped storage prevents one signed-in account's local acceptance from applying to another; exact notice matching no longer compares legal version `2.0` to a notice date.
- Consent now has a safe-area-protected persistent Continue action, explicit missing-requirement guidance, unchanged adult/terms/core-data requirements, retryable local-save errors, and full v2.0 Terms & Conditions in a scrollable modal accessible before agreeing. Reading/closing terms does not check acceptance or lose selections. Full legal document remains English.
- Under-18 emergency numbers and read-only rights open inside consent rather than linking to authenticated tabs; no account or AI calls needed. No emergency calls placed during tests.
- **Verification:** manual phone-width browser interactions at 390×844 and 320×568. Real consent/log returned 200 with analytics/updates both false; pre-login Continue reached login; existing-credential login + authenticated consent reached tabs and Settings without looping. Required-field/under-18 blocking, terms document sections 1–21, state retention, small-phone layout, simulated terms-fetch failure/retry and local-storage failure/retry passed. Lint clean for changed files; no consent-related TypeScript errors (14 pre-existing unrelated diagnostics remain). Actual iOS/Android hardware confirmation is pending. No testing agent used.
- **Existing limitation retained:** consent server logging remains best-effort under the pre-existing offline-first policy; no durable server-retry queue was introduced in this focused UI fix. Local completion persists; an offline acceptance is not proof of server audit persistence. Separate notice/terms server fields and durable consent synchronization remain backlog.
- User reported cropped bottom navigation icons/labels and requested checking other screens.
- Additional report: iPhone Safari users opening the FIR assistant saw an uncaught browser permission error.
- Phase A stabilisation only. Phase B incident modules remain **ON HOLD**.
- Existing architecture remains Expo SDK 54 / Expo Router, FastAPI, MongoDB. FIR state machine: `backend/fir_engine.py`; conversation UI: `frontend/app/fir-draft/index.tsx`.

### Implemented and verified in this maintenance pass
- Bottom navigation now reserves enough height for icons, labels, and padding; hidden History no longer consumes a seventh slot. Bottom safe area is owned by the outer layout, with the disclaimer in normal flow below navigation.
- Phone-width header controls wrap instead of overlapping. FIR probe/section actions have a separate row and 44pt header touch targets.
- FIR and main chat web audio use a browser player that returns the actual `play()` promise. Safari `NotAllowedError` shows **Play voice / Use text**, retaining prepared audio for a direct user-tap retry without another synthesis call. Stop/navigation safely handle pending playback cancellation; no global error suppression added.
- FIR microphone denials show inline guidance rather than an invisible browser alert. Recorder is prepared before recording, early release is guarded, and web recordings use Blob multipart uploads. Native FIR speech uses the current File/Paths API.
- Resumed `free_narrative` sessions retain the microphone as well as their conversation thread. No backend interview logic changed.
- Verification: five local audio regression tests passed; 320/390pt browser checks across all six tabs, history, drafts and FIR; simulated Safari audio denial/retry and microphone denial recovered without unhandled rejections. Narrative save/resume retested successfully.

### Remaining priorities
- **P0:** Affected users to confirm the fix on physical iPhone Safari; actual native audio hardware and real-browser permission prompts cannot be certified by desktop simulation.
- **P1:** Global evidence upload end-to-end verification remains pending from the prior handoff (not expanded into this task). No paid STT/TTS provider checks in this pass.
- **P2 / ON HOLD:** Phase B incident modules, advocate-verified non-cognizable routing, translation review, Legal Vault/share links. Existing unrelated TypeScript diagnostics remain; see `memory/ui_voice_verification.md`.

## Problem
Most Indians (and even many officials) don't know the Bharatiya Nyaya Sanhita (BNS 2023), Constitution articles, or judgment guidelines. A citizen at a police stop, an FIR desk, or a traffic check should be able to instantly know what the law says — in their own language, spoken aloud if they can't read.

## MVP (built)
- **Auth**: JWT email/password (register, login, me, language update)
- **Chat**: Streaming (SSE) multi-model Q&A with system prompt that forces exact citations (BNS section / Article / judgment)
  - Providers: Anthropic **Claude Sonnet 4.5** (default), OpenAI GPT-5.2, Google Gemini 3.1 Pro
  - Streams via `emergentintegrations` `LlmChat.stream_message()`
  - Mid-stream persistence (`finally` block) — no data loss on client disconnect
- **Voice**
  - STT: OpenAI Whisper via `/api/voice/transcribe`
  - TTS in-app: `expo-speech` (offline, native, all 22 Indian langs via device engine)
  - TTS in-cloud: OpenAI `tts-1` via `/api/voice/tts` (fallback / higher quality)
- **Languages**: 23 (English + all 22 official Indian languages via Schedule 8)
- **Know Your Rights**: 8 curated topics (police stop, arrest, FIR, women safety, traffic, RTI, consumer, DV) each with exact legal citations
- **History**: Sessions list + session detail view with TTS per message
- **Settings**: Language picker, model picker, emergency helplines (112, 181, 15100, 1098, 14433), sign out

## Architecture
- FastAPI + MongoDB (motor). Collections: `users`, `sessions`, `messages`.
- Expo Router file-based routing: `/` (splash gate) → `/login` | `/signup` | `/(tabs)/{index,rights,history,settings}` + `/session/[id]`.
- Design system: Editorial Mobile LIGHT — Khadi white surface (#FDFBF7), Ashoka Navy (#0A1C3A), Saffron accent (#C65D3B), Ashoka Green (#4B6F54).

## Market Research (Feb 2026)
- **NyayaBot** (NLU Delhi) — research prototype, English/Hindi only, not consumer-grade, focused on constitutional Q&A
- **Vaquil / Vakilsearch / LawRato** — lawyer-consulting marketplaces, paid, not empowerment-focused
- **Nyaaya.org** (Vidhi Centre) — excellent plain-language content but static website, no voice, no personal AI
- **Kaanoon.com / IndianKanoon.org** — case search databases for lawyers, not for common citizens
- **Google Legal-BERT / MOSIP** — infrastructure, not consumer apps
- **Gap**: No consumer mobile app combines (1) BNS/BNSS/BSA 2023 knowledge, (2) 22-language voice I/O, (3) exact citation with judgment references, (4) empowerment ethos. Gandhikar is uniquely positioned.

## Roadmap
- Phase 2: RAG over uploaded BNS/BNSS/BSA/Constitution PDFs for verbatim clause retrieval
- Phase 3: Paid tier — lawyer connect, document drafting (RTI, complaint letters, cease-and-desist), notarized FIR templates
- Phase 4: Emergency mode — one-tap "record rights during police stop" with automatic legal narration and NALSA alert
- Phase 5: White-label API for NGOs, panchayats, government helplines

---

## June 2026 — Corpus expansion, SOS reposition, security hardening

### Corpus
- Added `/app/backend/corpus_ipc.py`: 26 IPC 1860 sections + 16 CrPC 1973 sections,
  verbatim, each with a BNS/BNSS mapping note (old codes still govern all matters
  arising before 1 July 2024). Appended to `CORPUS` at import. Total = 87 entries
  (Constitution, BNS, BNSS, IPC, CrPC, MV Act, CMVR, RTI Act + Rules, Consumer
  Protection Act + E-Comm Rules, PWDVA).
- Retrieval ranking rewritten in `corpus.py`: label hit 12, phrase hit 6, and
  IDF-style token weights (rare token 4 → common token 1), min score 3, plus an
  expanded stop-word list. Fixes wrong-section ranking (e.g. "driving without
  helmet" now returns MV 129, previously BNSS 35).

### UI
- SOS is no longer a floating FAB in the root layout (it overlapped the chat mic).
  It is now a compact red SOS chip in the Chat header + the existing dialable
  Emergency Helplines card in Settings.

### Security (post-audit fixes)
- **Payments fail closed.** Removed the Razorpay "trust the pasted payment id"
  fallback; `submit-payment-id` returns 503 without server keys. Stripe and
  Razorpay webhooks now REQUIRE their signing secret (503 if unset, 400 on bad
  signature) — previously an unsigned webhook could grant Pro to any user id.
  `razorpay.enabled` in pricing/config is now `bool(razor_client)`.
- **Password reset replaced with emailed OTP.** New `mailer.py` (Emergent-managed
  Resend). `POST /api/auth/forgot-password {email}` emails a 6-digit code (bcrypt
  hashed at rest, 10-min expiry, single use, 5 wrong-code limit, 60s/3-per-hour
  send throttle) and always returns a generic response (no account enumeration).
  `POST /api/auth/reset-password {email, code, new_password}` returns {token,user}.
  The old email+phone reset (account takeover risk) is deleted.
- **Admin export** now requires the `X-Admin-Key` header (was `?key=`, which leaks
  into logs). `ADMIN_KEY` rotated; compared with `hmac.compare_digest`.

### Known / deferred
- Paytm payment gateway to replace Razorpay for India — playbook obtained, blocked
  on user creating a Paytm merchant account (needs PAYTM_MID + PAYTM_MERCHANT_KEY).
  Paytm/UPI checkout cannot be tested in Expo Go; needs a native build.
- P3 hardening not done (user deferred): generic API error strings, upload
  size/type cap on /api/voice/transcribe, SecureStore for the auth token,
  shorter JWT lifetime with aud/iss.
- A browser-accessible web version of Dhara for the MSafe website must be built as
  a separate Emergent Full Stack (web) project — Expo mobile deploys only ship the
  QR/landing link and store builds.

## Build 17 (June 2026) — direct build command (no tests run, per user)
- **Mic**: `expo-speech-recognition` pinned to `3.1.3` in `package.json`; `yarn.lock`
  already matched; stale `package-lock.json` entry (bogus `56.0.1`) corrected to
  `3.1.3` with the right tarball + integrity so npm-based builds can't pull a
  different native module. Added crash guards: `startRecording()` promise rejection
  is caught in `onMicPressIn`, and all PanResponder mic callbacks are try/catch wrapped.
- **Corpus (Motor Vehicles Act 1988, amended 2019)** — 10 new verbatim sections:
  194D (no-helmet ₹1,000 + 3-month DL suspension), 194C (triple riding), 177
  (general penalty), 181 (no licence), 180 (owner permitting unlicensed driver),
  183 (over-speeding), 184 (dangerous driving: red light, phone, wrong side),
  196 (no insurance), 199A (juvenile offences — guardian liable), 130 (documents
  on demand by uniformed officer).
- **Corpus (RTI Act 2005)** — 5 new verbatim sections: 2 (definitions/scope),
  4 (proactive disclosure + reasons for decisions), 5 (PIO/APIO designation),
  8 (exemptions + public-interest override + 20-year rule), 18 (complaint to the
  Information Commission). Corpus total now 102 entries; retrieval verified for
  helmet fine, minor driving, red light, insurance, RTI refusal/complaint queries.
- **Branding**: theme switched to Royal Blue + Gold — `brand/brandPrimary #12328C`,
  `brandSecondary #9A6E00` (gold, WCAG-safe with white text), `brandTertiary #1B4BB8`,
  plus `gold #D4AF37` / `goldSoft #F5E3A3` tokens. `app.json` splash + adaptive-icon
  background updated to `#12328C`. All screens read from the theme, so the palette
  is consistent app-wide.
- **Cleanup**: removed the "Claude Sonnet 4.5" model name from the user-facing
  Pro comparison row (now "Priority AI responses").

## Iteration 13 (June 2026) — four user-selected features
1. **Cheque bounce (Negotiable Instruments Act)** — new `backend/corpus_ni.py` with NI 138
   (verbatim, incl. the 6-month presentation / 30-day notice / 15-day payment proviso),
   142 (complaint within one month, jurisdiction = payee's bank branch), 139
   (presumption for the holder), 143A (interim compensation up to 20%), 148 (20%
   deposit on appeal). Scope notes spell the clock out in plain words.
2. **Cyber fraud** — new `backend/corpus_cyber.py`: IT Act 66C / 66D / 43, BNS 318
   (cheating) and 319 (cheating by personation), plus two official REPORTING entries —
   the MHA National Cyber Crime Reporting Portal + helpline 1930 (golden hour, account
   freeze) and the RBI limited-liability rule (report to the bank within 3 working days =
   zero liability; bank must credit within 10 working days). Settings now lists 1930.
3. **State rules (jurisdiction layer)** — `users.state` (ISO 3166-2:IN code) with
   `PATCH /api/auth/state` and `GET /api/reference/states`; new `app/state.tsx` picker
   shown once right after signup and reachable from Settings. `corpus_state.py` gained
   verified rent entries for DL (Delhi Rent Control 14), MH (MRC 16), KA (Karnataka Rent
   Act 27), TN (Tenancy Act 4 + 11: 3-month deposit cap), UP (Tenancy Act 4 + 11:
   2-month deposit cap) alongside the existing GJ/BR prohibition entries. State hits are
   returned as extra citation chips with `state` + `text_kind` on the payload.
   `STATE_SENSITIVE_TOPICS` (rent, traffic compounding, liquor, stamp duty) drives two new
   SSE frames: `state_prompt` (no state set → gold "set your state" card in chat) and
   `state_note` (state known but no verified local rule → honest note naming the
   authority to check). We never guess a local amount.
4. **Saved answers** — `PUT/GET/DELETE /api/bookmarks` (idempotent on `client_id`, soft
   delete) + `frontend/src/bookmarks.ts` (AsyncStorage-first, two-way sync) + new "Saved"
   tab (`app/(tabs)/saved.tsx`) and a bookmark button on every assistant bubble. Reads
   work fully offline; the server copy only survives reinstalls.

**Retrieval accuracy hardening** (the dangerous-bug class in this app):
`RETRIEVAL_MIN_SCORE` raised 3 → 4 (a single moderately-common token is no longer proof),
a relative cutoff drops any hit below 50% of the top score, and a per-entry `require_any`
guard was added to the NI, RTI/RTIR, MV 194C/194D and state-rent entries so generic words
("notice", "deposit", "fine", "ask") can no longer pull an unrelated section into an answer.

Tested by the testing agent (iteration_13): 18/18 backend pytest + all frontend flows, no bugs.

## Iteration 14 (June 2026) — labour law, notice drafts, fraud checklist, more state rent
- **Wages / termination / gratuity**: new `backend/corpus_labour.py` on the four Labour Codes
  (in force 21 Nov 2025): Code on Wages 17 (7th-of-month; 2 working days on exit), 18
  (deduction limits, 50% cap), 45 (claim before the wage authority within 3 years, up to
  10x compensation), IR Code 70 (1 month notice + 15 days' pay per year on retrenchment),
  IR Code 71 (last in first out + re-employment preference), SS Code 53 (gratuity), and the
  SAMADHAN portal grievance pathway. All guarded with `require_any` work-context keywords.
- **Notice drafts**: `frontend/src/drafts.ts` builds three notices ON DEVICE from fixed
  templates (no LLM call, so deadlines can never be hallucinated): cheque-bounce demand
  (§138 30-day/15-day), security-deposit refund, unpaid-salary demand. Screens at
  `app/drafts/index.tsx` + `app/drafts/[type].tsx` with copy/share. Entitlement metered by
  `POST /api/drafts/consume` — `DRAFTS_FREE=1` free draft, then Pro (402 paywall).
  `drafts_used/free_limit/remaining` exposed on the user.
- **Fraud golden-hour checklist**: `app/fraud-checklist.tsx` — free for everyone, 7 ordered
  steps (call 1930 → cybercrime.gov.in → bank in writing within 3 working days → block
  card/UPI → evidence → acknowledgement numbers → 10th-working-day follow-up), live timer
  and tick state persisted in AsyncStorage, tel:/https: action buttons.
- **State rent**: added Telangana (Rent Control 10), West Bengal (Premises Tenancy 6-7) and
  Kerala (Rent Control 11) to `corpus_state.py`, all with the rent `require_any` guard.
- **Contextual next step in chat**: an answer citing NI/labour/rent/cyber sources now shows
  a gold chip taking the user straight to the matching draft or the fraud checklist.
- Verified by the testing agent (iteration_14): 17/17 backend tests + all UI flows, no bugs.

## Iteration 15 — LLM spend caps (user directive: "make sure the credits are capped")
Every paid call on the Emergent key is now metered in `db.usage_daily` (per user per day
and app-wide) by `meter_llm_use()` in `server.py`:
- Free users: **10 questions/day**, **15 voice actions/day** (STT + TTS share the voice bucket).
- Pro users: 60 questions/day, 90 voice actions/day. App-wide backstop: 3000 paid calls/day.
- All limits are env-overridable: `FREE_DAILY_QUESTIONS`, `FREE_DAILY_VOICE`,
  `PRO_DAILY_QUESTIONS`, `PRO_DAILY_VOICE`, `APP_DAILY_LLM_CALLS`.
- Refusals (no verified source / non-Indian / not-legal) never reach the model, so they are
  NOT counted — verified: a refusal still answers after the question cap is hit.
- Over-cap responses are HTTP 429 with a plain-language `detail.message`; the chat shows it
  in the answer bubble, voice shows an alert. `GET /api/auth/me` returns
  `daily_questions_left/cap` and `daily_voice_left/cap`, shown in Settings → "Today's free usage".
- Self-tested with curl (11th question in a day → 429 at exactly the cap; refusal after the
  cap → 200; TTS unaffected by the question bucket). Per the user's directive, no further
  testing-agent or sub-agent runs.

## Iteration 16 — surgical fixes (user cap: 35 ECU)
- **Mic pin** re-verified: `expo-speech-recognition` exactly `3.1.3` in package.json, yarn.lock,
  package-lock.json and node_modules.
- **SOS button moved to Settings only.** The root-layout floating mount was removed; the red
  pill now renders inline in Settings → Emergency Helplines (`sos-row` / `sos-button-floating`),
  opening the same one-tap dialer sheet (112 / 100 / 181 / 1098 / 15100 / 108). Verified absent
  from every other screen and no longer able to cover the chat composer or mic.
- **Reply-language enforcement**: new `backend/langpolicy.py` maps each of the 22 languages to
  its Unicode script and measures the script coverage of the finished reply
  (`MIN_SCRIPT_RATIO = 0.35`, acronyms/numbers tolerated). If a non-English reply comes back in
  the wrong script, `server.py` runs ONE repair translation and emits a `final` SSE frame that
  overwrites the bubble. English is untouched and the repair costs nothing on the happy path.
  Verified by testing agent (iteration_16): Hindi/Tamil/Bengali replies scored a 1.000 script
  ratio; 6/6 backend tests; new test file `backend/tests/test_lang_policy.py`.

### KNOWN GAP found during iteration 16 — FIXED this session
Corpus retrieval keywords are ENGLISH-ONLY, so a question typed in Hindi/Tamil/Bengali usually
matched nothing and fell into the (correctly localized) "no verified source" refusal. Voice
input transcribes to the spoken language, so voice users hit this too.
**Fix implemented**: `backend/langpolicy.py::needs_retrieval_translation()` detects non-Latin
script (>30% of alphabetic chars non-ASCII). If true, `server.py::translate_for_retrieval()`
runs ONE non-streaming Claude call (via Emergent LLM key) that translates the question to English
SOLELY for matching — `retrieval_text` replaces `body.message` everywhere retrieval logic is used
(is_non_indian_jurisdiction, is_non_legal_advice, corpus_retrieve, corpus_retrieve_state,
state_sensitive_topic, explicit id/section regex, classify_topic, top_candidate_debug). The
verified corpus text remains the only source of legal fact; the model still answers the user's
own original wording in their own language. English queries are untouched (zero extra cost/latency).

### Session additions (post iteration 16)
- **Usage meter in chat**: `/(tabs)/index.tsx` now shows a glanceable "`X/Y questions today`" /
  "`X/Y voice today`" pill row right under the header (previously only visible in Settings).
  Refreshes on chat-screen mount and after every message via `refreshUser()`.
- **Draft history wired up**: `src/draftHistory.ts` existed but nothing called it. Now
  `drafts/[type].tsx` saves every generated notice via `addToHistory()`, and a new
  `drafts/history.tsx` screen (reachable from a header icon + a card on `drafts/index.tsx`) lists,
  expands, copies, shares and deletes past notices — all on-device (AsyncStorage), no backend cost.
- **Mic gestures — WhatsApp lock + waveform**: slide-left-to-cancel and the transcript
  Send/Edit/Re-record confirmation already existed. Added slide-UP-to-lock (drag past -55px on
  the Y axis locks hands-free recording; a floating lock-with-chevron hint fades in above the mic
  as you drag) with a dedicated locked bar (trash = discard, checkmark = finish → existing
  transcribe/confirm flow). Added a 5-bar live "listening" waveform driven by plain
  `Animated.loop` timings (deliberately NOT native audio metering — flaky across Android OEMs and
  undefined on web per Expo's own issue tracker — so it looks identical on every phone).
- **Speaker volume control**: `ttsVolume` (0–1, default 1.0) persisted in `auth.tsx`
  (`dhara_tts_volume`), applied to the TTS `AudioPlayer.volume` in `(tabs)/index.tsx`, adjustable
  via a new slider in Settings (`@react-native-community/slider`, installed via `yarn expo
  install`).
- **Root-level `/health` added** (`server.py`) — platform readiness/liveness probes hit `/health`
  at the root, not `/api/health`; both now return 200.


## June 2026 — P0/P1 Sprint: Push verification, Layer M, AI Gateway
- **P0 #1 — Push notification 9-step verification**: added `googleServicesFile:
  "./google-services.json"` to `app.json` Android block (was missing). Backend now exposes
  `GET /api/health/push` returning the full 9-step readiness matrix + gateway status; the
  `EMERGENT_PUSH_KEY` placeholder is expected in dev and is swapped in at deploy time.
- **P0 #2 — Layer M (Answer Generator) hardening**: new `backend/engine/answer_generator.py`.
  If Layer S filters every provision to REPEALED/SUPERSEDED, chat_router now emits a
  deterministic `build_cannot_verify_response()` (no LLM call, no hallucination risk) using the
  sprint-brief format (ANSWER / WHY / WHAT YOU CAN DO / VERIFIED SOURCES). Also appends a
  plain-language status-guard notice to the LLM prompt when at least one cited provision is dead.
- **P1 — AI Gateway service**: new `backend/services/ai_gateway.py`. Centralises provider +
  model selection (`SERVER_CHAT_PROVIDER` / `SERVER_CHAT_MODEL` / `SERVER_CHAT_FALLBACK_MODEL`),
  supports `EMERGENT_OFF=1` + `COMPANY_LLM_KEY` for provider abstraction, and exposes
  `build_chat()` (drop-in for `.with_model`), `send_with_fallback()`, `stream_with_fallback()`,
  and `gateway_status()`. Every call produces a structured log line with a stable `error_id`.
  chat_router's primary chat call now flows through `build_chat()`.

## June 2026 — Follow-up sprint: Gateway consolidation + self-test push
- **Gateway consolidation**: `chat_router.py` no longer instantiates `LlmChat` directly anywhere.
  The language-repair pass (`langfix`) and the follow-up-question generator now both use
  `services.ai_gateway.build_chat()`, so all three chat LLM sites share the same provider,
  model, error-ID, and structured log line. `LlmChat` import removed from the router.
- **Push self-test endpoint**: new `POST /api/push/self-test` — sends a Dhara push to the calling
  user's own device only (rate-limited to 1/min per user). Settings now shows a "Send test
  notification" row directly under the Push toggle when granted. Works on real Android/iOS
  builds — Expo Go / web cannot receive push and the UI says so explicitly.
- **Emergent-independence verifier**: new `scripts/verify_emergent_off.py`. Runs three env
  combinations (default / EMERGENT_OFF + COMPANY_LLM_KEY / EMERGENT_OFF only) and asserts the
  gateway's key resolution matches expectations. All three currently pass.
