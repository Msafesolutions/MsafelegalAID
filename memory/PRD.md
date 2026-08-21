# Gandhikar — PRD

## Vision
A dignified, free, bilingual+multilingual AI legal companion for every Indian citizen. Empower — never threaten. Named after Mahatma Gandhi. Truth, non-violence, rights.

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

