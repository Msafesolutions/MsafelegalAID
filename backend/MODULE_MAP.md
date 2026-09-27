# MODULE MAP — Dhara Backend (Phase 1 Modularization)

Generated after Phase 1 extraction. server.py lines before: 4343.

---

## AUTH
**File:** `api/auth_router.py`

routes:
- POST /auth/register
- POST /auth/login
- POST /auth/session (Google OAuth)
- POST /auth/forgot-password
- POST /auth/reset-password
- POST /account/delete
- POST /account-deletion/request-otp
- POST /account-deletion/verify
- GET  /auth/me
- PATCH /auth/language
- PATCH /auth/state
- POST /auth/accept-terms

functions:
- register, login, google_auth_session
- forgot_password, reset_password
- delete_account_in_app, request_deletion_otp, verify_deletion_otp
- me, update_language, update_state, accept_terms
- _prune_sends, _prune_delete_sends, _finish_deletion (private helpers)

dependencies:
- dependencies.py: db, current_user, hash_pw, check_pw, make_token, public_user
- config/settings.py: JWT_SECRET, JWT_ALG, JWT_EXP_DAYS, PRO_FREE_SAMPLES, DRAFTS_FREE, FREE_DAILY_QUERIES
- mailer.py: send_email, password_reset_otp_email, account_deletion_otp_email, email_configured
- legal.py: TERMS_VERSION
- states.py: is_valid_state, state_name
- account_deletion.py: hard_delete_user
- corpus_db.py: STATE_CODE_TO_JURISDICTION

---

## CHAT
**File:** `api/chat_router.py`

routes:
- POST /chat/stream
- GET  /chat/sessions
- GET  /chat/sessions/{session_id}/messages
- DELETE /chat/sessions/{session_id}
- GET  /bookmarks
- PUT  /bookmarks
- DELETE /bookmarks/{client_id}
- POST /drafts/consume
- POST /voice/transcribe
- POST /voice/tts
- POST /client-error-log
- POST /register-push
- POST /chat/followup

functions:
- chat_stream, list_sessions, session_messages, delete_session
- list_bookmarks, upsert_bookmark, delete_bookmark, consume_draft
- transcribe, tts
- client_error_log, register_push
- chat_followup

dependencies:
- dependencies.py: db, current_user, current_user_optional, meter_llm_use, build_system_prompt, translate_for_retrieval, logger
- config/settings.py: SERVER_CHAT_PROVIDER, SERVER_CHAT_MODEL, EMERGENT_LLM_KEY
- corpus.py: retrieve, retrieve_state, is_non_indian_jurisdiction, is_non_legal_advice, etc.
- corpus_db.py: retrieve_db, lookup_section, check_query_for_orphan_warnings
- langpolicy.py: needs_language_repair, repair_prompt, needs_retrieval_translation
- personal_law.py: classify_personal_law_topic, detect_context, act_hint_phrase, etc.
- push.py: register_device, unregister_device
- openai: AsyncOpenAI (for voice TTS/STT)

---

## FIR
**File:** `api/fir_router.py`

routes:
- POST /fir/draft
- GET  /fir/drafts/{user_id}
- GET  /fir/draft/{draft_id}
- POST /fir/classify (410 gone)
- POST /fir/generate (410 gone)
- POST /fir/event (410 gone)
- POST /fir/followup (410 gone)
- POST /fir/session
- POST /fir/session/{session_id}/turn
- POST /fir/session/{session_id}/gps
- POST /fir/session/{session_id}/evidence
- GET  /fir/session/{session_id}/evidence/{file_id}
- GET  /fir/sessions/{user_id}
- GET  /fir/session/{session_id}
- GET  /fir/session/{session_id}/draft (old)
- POST /fir/session/{session_id}/pause
- POST /fir/session/{session_id}/back
- DELETE /fir/session/{session_id}/evidence/{file_id}
- PATCH /fir/session/{session_id}/evidence/{file_id}/caption
- GET  /fir/session/{session_id}/draft.pdf
- POST /voter/pdf

functions:
- fir_upsert_draft, fir_list_drafts, fir_get_draft
- fir_classify_gone, fir_generate_gone, fir_event_gone, fir_followup_gone
- fir_create_session, fir_session_turn, fir_log_gps
- fir_upload_evidence, fir_download_evidence
- fir_list_sessions, fir_get_session, fir_get_session_draft
- fir_pause_session, fir_back_session
- fir_delete_evidence, fir_update_evidence_caption
- fir_get_pdf, voter_generate_pdf

dependencies:
- dependencies.py: db, current_user, logger
- config/settings.py: EMERGENT_LLM_KEY
- fir_engine.py: create_session, process_turn, STAGE_COMPLETED, STAGE_SAFETY_GATE
- fir_storage.py: init_storage, upload_evidence, download_evidence

---

## MISSING PERSON (inline router, stays in server.py)
**File:** `missing_media.py`
routes: Injected via `app.include_router(create_missing_media_router(db, current_user))`

---

## ADMIN
**Stays in:** `server.py`

routes:
- GET  /admin/export/users.csv
- GET  /admin/export/messages.csv
- GET  /admin/stats
- GET  /admin/refusal-stats

functions:
- export_users_csv, export_messages_csv, admin_stats, admin_refusal_stats
- _check_admin_key (private helper)

---

## BILLING
**Stays in:** `server.py`

routes:
- POST /billing/checkout
- POST /billing/verify
- GET  /billing/razorpay/config
- POST /billing/razorpay/submit-payment-id
- POST /webhooks/stripe (app-level, not api)
- POST /webhooks/razorpay (app-level, not api)
- GET  /billing/pricing

functions:
- create_checkout, verify_checkout, razorpay_config, razorpay_submit_payment
- stripe_webhook, razorpay_webhook
- _mark_pro (shared billing helper)

---

## ADVOCATE
**Stays in:** `server.py`

routes:
- POST /advocate/register
- GET  /advocate/profile/{user_id}
- POST /advocate/intake/create
- GET  /advocate/intake/{token}
- POST /advocate/intake/{token}/submit
- GET  /advocate/intakes/{advocate_id}
- GET  /advocate/cross-reference

functions:
- advocate_register, advocate_profile, intake_create, intake_get, intake_submit
- intakes_list, cross_reference
- _load_xref, _xref_search, _generate_intake_summary (private helpers)

---

## ECOURTS / CASES
**Stays in:** `server.py`

routes:
- GET /cases/cnr/{cnr}
- GET /cases/search

functions: case_by_cnr, search_cases, _eci_get, _nc

---

## PRIVACY / GDPR
**Stays in:** `server.py`

routes:
- GET  /user/my-data
- GET  /user/my-data/export
- GET  /grievance
- POST /grievance
- POST /consent/log
- PATCH /user/privacy-choices
- POST /user/data-export

---

## REFERENCE
**Stays in:** `server.py`

routes:
- GET /reference/languages
- GET /reference/states
- GET /reference/models
- GET /reference/topics
- GET /reference/topics/{topic_id}
- GET /legal/terms
- GET /billing/pricing
- GET /health
- POST /retrieve

---

## SHARED UTILITIES
**File:** `dependencies.py`

functions used by more than one module:
- db, corpus_db (MongoDB connections)
- hash_pw, check_pw (auth)
- make_token (auth)
- public_user (auth + me endpoint)
- current_user, current_user_optional (used by ALL routes)
- meter_llm_use (chat + voice)
- build_system_prompt (chat)
- translate_for_retrieval (chat)
- logger

---

## CENTRAL CONFIGURATION
**File:** `config/settings.py`

All environment variables and constants. ONE place for model names.
SERVER_CHAT_MODEL default: "claude-sonnet-4-5-20250929"
SERVER_CHAT_FALLBACK_MODEL default: "claude-haiku-4-5"

---

## REMAINING IN server.py (after Phase 1)
- Billing (Stripe/Razorpay) routes
- Admin export routes
- Advocate / Intake routes
- eCourts case lookup routes
- Privacy / GDPR routes
- Reference data routes
- Startup / Shutdown lifecycle events
- App-level middleware (CORS)
- Missing Media router injection
- Cross-reference search (_load_xref, _xref_search)
- Voter PDF helper (moved to fir_router.py)

## RECOMMENDED NEXT REFACTOR (Phase 2)
1. Extract billing to `api/billing_router.py`
2. Extract admin to `api/admin_router.py`
3. Extract advocate to `api/advocate_router.py`
4. Extract privacy to `api/privacy_router.py`
