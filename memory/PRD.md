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
