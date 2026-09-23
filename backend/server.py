"""Dhara - AI Legal Empowerment Bot Backend."""
import os
import io
import re
import json
import httpx
import uuid
import asyncio
import hmac
import hashlib
import secrets
import logging
import bcrypt
import jwt
import stripe
try:
    import razorpay
except Exception:
    razorpay = None
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, AsyncGenerator

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Header, Request, Query
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field
from openai import AsyncOpenAI

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from legal import TERMS_AND_CONDITIONS, TERMS_VERSION, DISCLAIMER_SHORT
from mailer import send_email, password_reset_otp_email, account_deletion_otp_email, email_configured
from corpus import (
    retrieve as corpus_retrieve,
    retrieve_state as corpus_retrieve_state,
    state_sensitive_topic,
    is_non_indian_jurisdiction,
    is_non_legal_advice,
    public_citation,
    sanitize_model_output,
    REFUSAL_NO_CORPUS,
    REFUSAL_NON_INDIAN,
    REFUSAL_NOT_LEGAL,
    localize_refusal,
    top_candidate_debug,
    classify_topic,
)
from corpus_db import (
    retrieve_db as db_retrieve,
    lookup_section as db_lookup_section,
    check_query_for_orphan_warnings as db_orphan_check,
    STATE_CODE_TO_JURISDICTION,
)
from states import STATES, STATE_BY_CODE, is_valid_state, state_name
from langpolicy import needs_language_repair, repair_prompt, needs_retrieval_translation
from corpus_migration import run_corpus_migration
from push import register_device, unregister_device
from push_jobs import run_push_jobs_loop
from account_deletion import hard_delete_user
from script_guard import check_script_mismatch
from personal_law import (
    classify_personal_law_topic,
    detect_context as detect_personal_law_context,
    act_hint_phrase,
    disambiguation_question,
    act_disclaimer,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
CORPUS_DB_NAME = os.environ.get("CORPUS_DB_NAME", "bns-know-your-rights-gandhikar_db")
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_ME_HANDLE = os.environ.get("RAZORPAY_ME_HANDLE", "calviltech")
RAZORPAY_ME_URL = os.environ.get("RAZORPAY_ME_URL", "https://razorpay.me/@calviltech")

# ─── eCourtsIndia partner API ──────────────────────────────────────────────────
ECOURTS_TOKEN = os.getenv("ECOURTS_API_TOKEN", "")
ECOURTS_BASE  = os.getenv("ECOURTS_API_BASE", "https://webapi.ecourtsindia.com")
PRO_PRICE_INR = int(os.environ.get("PRO_PRICE_INR", "9900"))  # paise (₹99)
PRO_PRICE_LABEL = os.environ.get("PRO_PRICE_LABEL", "₹99")
PRO_PRICE_USD = int(os.environ.get("PRO_PRICE_USD", "500"))  # cents
PRO_PRICE_USD_LABEL = os.environ.get("PRO_PRICE_USD_LABEL", "$5")
PRO_FREE_SAMPLES = int(os.environ.get("PRO_FREE_SAMPLES", "5"))
# Ready-to-send notice drafts: the first one is free, the rest are a Pro feature.
DRAFTS_FREE = int(os.environ.get("DRAFTS_FREE", "1"))

# ---------------------------------------------------------------------------
# LLM spend caps. Voice is an accessibility floor (not a premium feature), so
# free users get ONE unified daily bucket of 30 queries covering both text and
# voice together. Pro users are unlimited on a per-user basis (only the
# app-wide backstop applies to them).
# ---------------------------------------------------------------------------
FREE_DAILY_QUERIES = int(os.environ.get("FREE_DAILY_QUERIES", "30"))   # unified text + voice
APP_DAILY_LLM_CALLS = int(os.environ.get("APP_DAILY_LLM_CALLS", "3000"))
# Legacy env vars kept for backward compat but no longer used for limits.
_LEGACY_FREE_Q = int(os.environ.get("FREE_DAILY_QUESTIONS", "30"))
_LEGACY_FREE_V = int(os.environ.get("FREE_DAILY_VOICE", "9999"))
JWT_ALG = "HS256"
JWT_EXP_DAYS = 30

if STRIPE_API_KEY:
    stripe.api_key = STRIPE_API_KEY

razor_client = None
if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        razor_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception:
        razor_client = None

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
corpus_db = client[CORPUS_DB_NAME]   # separate DB holding 70,397 legal sections

app = FastAPI(title="Dhara API")
api = APIRouter(prefix="/api")


@app.get("/health")
async def root_health():
    """Root-level health check for the platform's readiness/liveness probes
    (which hit /health, not /api/health). Kept intentionally tiny — no DB call
    — so it can't itself become a source of probe flakiness."""
    return {"status": "ok"}


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gandhikar")

# ---------- Models ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)
    phone: str = Field(min_length=6, max_length=20)
    state: Optional[str] = None
    terms_accepted: bool
    terms_version: str = TERMS_VERSION

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordIn(BaseModel):
    """Step 1 — ask for a one-time code to be emailed to the account address."""
    email: EmailStr

class ResetPasswordIn(BaseModel):
    """Step 2 — prove ownership of the mailbox with the emailed code."""
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)
    new_password: str = Field(min_length=6)

class DeleteAccountIn(BaseModel):
    """In-app deletion (Settings) — re-auth with the account password before
    an irreversible, total-data-loss action."""
    password: str

class RequestDeletionOTPIn(BaseModel):
    """Public web deletion page, step 1 — email a one-time code."""
    email: EmailStr

class VerifyDeletionOTPIn(BaseModel):
    """Public web deletion page, step 2 — prove ownership of the mailbox,
    then permanently delete the account."""
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)

class AuthOut(BaseModel):
    token: str
    user: dict

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: str = "en"
    language_name: str = "English"
    language_native: Optional[str] = None
    model_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-5-20250929"
    mode: str = "basic"  # "basic" | "pro"

class ClientErrorLogIn(BaseModel):
    """Structured client-side error report — see POST /client-error-log."""
    context: str  # e.g. "chat_stream_fetch", "chat_stream_native_read"
    error_name: Optional[str] = None
    error_message: Optional[str] = None
    platform: Optional[str] = None  # "ios" | "android" | "web"
    retried: Optional[bool] = None

class RegisterPushBody(BaseModel):
    """Emergent-managed push (SuprSend relay) device registration."""
    user_id: str
    platform: str   # "android" | "ios"
    device_token: str

class TTSIn(BaseModel):
    text: str
    language: str = "en"
    voice: str = "alloy"
    # Stable id for the answer this text belongs to (the assistant message id).
    # Chunked playback sends several requests per answer; they all carry the same
    # group so the answer is metered once. Absent => metered per request, as before.
    group: Optional[str] = None

class CheckoutIn(BaseModel):
    return_url: str

class AcceptTermsIn(BaseModel):
    terms_version: str = TERMS_VERSION

class AdvocateRegisterIn(BaseModel):
    user_id: str
    bar_council_number: str          # required — must be a non-empty enrolment number
    state_bar: str
    specializations: List[str]

class IntakeCreateIn(BaseModel):
    advocate_id: str
    template_id: str = "general"
    template_title: str = "General Intake"

class IntakeSubmitIn(BaseModel):
    client_name: str
    transcript: List[str] = []
    answers: Optional[dict] = None  # structured {question_id: answer}

# ---------- Helpers ----------
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def check_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def make_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def public_user(u: dict) -> dict:
    state_code = u.get("state") or ""
    return {
        "id": u["id"],
        "email": u["email"],
        "name": u["name"],
        "phone": u.get("phone", ""),
        "language": u.get("language", "en"),
        "state": state_code or None,
        "state_name": state_name(state_code),
        # is_pro — always present, default False for safety
        "is_pro": bool(u.get("is_pro", False)),
        "pro_since": u.get("pro_since"),
        "pro_samples_used": int(u.get("pro_samples_used", 0)),
        "pro_samples_limit": PRO_FREE_SAMPLES,
        "pro_samples_remaining": max(0, PRO_FREE_SAMPLES - int(u.get("pro_samples_used", 0))),
        "drafts_used": int(u.get("drafts_used", 0)),
        "drafts_free_limit": DRAFTS_FREE,
        "drafts_remaining": max(0, DRAFTS_FREE - int(u.get("drafts_used", 0))),
        # is_grandfathered — early users keep access even if paywalled later
        "is_grandfathered": bool(u.get("is_grandfathered", True)),
        # state_jurisdiction — full corpus jurisdiction string derived from state code
        # e.g. "MH" → "Maharashtra".  Used by /api/retrieve to prioritise state Acts.
        "state_jurisdiction": (
            u.get("state_jurisdiction")
            or STATE_CODE_TO_JURISDICTION.get(state_code.upper(), "")
        ),
        "terms_accepted": u.get("terms_accepted", False),
        "terms_version": u.get("terms_version"),
        "terms_accepted_at": u.get("terms_accepted_at"),
    }

async def current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user

# ---------- System prompts ----------
def build_system_prompt(
    language_name: str,
    is_pro: bool = False,
    corpus_context: str = "",
    language_native: Optional[str] = None,
    advocate_mode: bool = False,
) -> str:
    """
    Grade-6 answer prompt with strict citation-integrity rule.

    CITATION-INTEGRITY (see corpus.py):
    - Model output MUST NEVER contain section numbers, article numbers, or verbatim
      statutory text. The UI renders citations from `citations` SSE frames served
      from the verified corpus, not from the model.
    - When corpus_context is provided, base the answer on that verified text.
    - When corpus_context is empty, decline politely with the refusal line and stop.
    """
    # Display both English and native names to remove ambiguity
    lang_display = (
        f"{language_name} ({language_native})" if language_native and language_native != language_name
        else language_name
    )
    is_english = language_name.strip().lower() == "english"

    # ── Advocate / Professional Mode ──────────────────────────────────────────
    # Completely different system prompt for licensed advocates. Allows section
    # citations (unlike citizen mode), uses formal legal language, and grounds
    # all analysis in the verified corpus provided.
    if advocate_mode:
        verified_block_adv = ""
        if corpus_context:
            verified_block_adv = (
                "\n\nVERIFIED SOURCES (cite these directly by Act name and section):\n"
                + corpus_context + "\n"
            )
        return (
            "You are Dhara — an AI legal analysis assistant for licensed Indian advocates.\n\n"
            "PROFESSIONAL MODE: You are addressing a licensed Indian advocate. "
            "Use formal legal language. You MAY cite specific Act names, section numbers, "
            "sub-sections, and provisos found in the VERIFIED SOURCES below. "
            "Assume the reader has legal training. "
            "Flag areas where the advocate should verify with current gazette notifications or state amendments.\n\n"
            "HARD RULES:\n"
            "1. Base your analysis ONLY on the VERIFIED SOURCES provided. "
            "If VERIFIED SOURCES are empty, decline with: "
            "'Insufficient verified corpus material for a professional brief on this topic. Please consult primary sources.'\n"
            "2. No markdown headers (#, ##). No bold (**). No emoji.\n"
            "3. If the corpus does not cover this topic, state so explicitly rather than extrapolating.\n\n"
            "FORMAT — respond in this four-part structure:\n\n"
            "Issue: <one-sentence statement of the legal question>\n\n"
            "Applicable Law: <cite the Act(s) and section(s) from verified sources>\n\n"
            "Legal Position: <technical analysis in 3–5 sentences>\n\n"
            "Practitioner Notes:\n"
            "- <procedural step or verification point>\n"
            "- <state amendment flag or gazette check needed>\n"
            "- <escalation path or time-limit note>\n"
            "- <optional 4th note>"
            f"{verified_block_adv}"
        )

    disclaimer_line = (
        "\n\nAt the end of your reply, add exactly this line, WRITTEN IN " + lang_display + ":\n"
        '"⚠️ Legal information, not legal advice. Consult an advocate. © Callistus Moses · MSafe Solutions."'
    )

    verified_block = ""
    if corpus_context:
        verified_block = (
            "\n\nVERIFIED SOURCES (already shown to the user by the UI — DO NOT repeat verbatim, "
            "DO NOT quote, DO NOT emit section/article numbers). Use these to shape your plain-language "
            "explanation ONLY:\n" + corpus_context + "\n"
        )

    # STRICT language enforcement — the earlier prompt let English format labels leak into
    # non-English replies. We now (a) shout the language rule, (b) tell the model to
    # translate the section labels, and (c) allow only proper-noun acronyms like FIR/RTI.
    language_rule = (
        f"REPLY LANGUAGE: {lang_display}. Write your ENTIRE reply — every word, every heading, "
        f"every bullet, and the final disclaimer — in {lang_display}. Use the {lang_display} script. "
        "The ONLY things that may stay in English are widely-used acronyms like FIR, RTI, POSH, PIO, SP, "
        "and proper nouns. Do NOT reply in English if the language above is not English. "
        "If you catch yourself writing in English, translate everything before answering."
        if not is_english else
        "REPLY LANGUAGE: English. Simple, dignified, Grade 6 reading level. Talk to the person as \"you\"."
    )

    # Format labels: keep English tokens ONLY as internal cues; instruct model to render
    # them in the reply language. We also give a concrete Tamil example if the target isn't
    # English, so the model doesn't default to copying the English tokens verbatim.
    label_hint = (
        ""
        if is_english else
        f"\n\nIMPORTANT — TRANSLATE THE SECTION HEADINGS. In your reply, the two section headings "
        f"(the equivalents of 'Answer:' and 'What you can do:') MUST be written in {lang_display}, "
        f"NOT in English. The user is a native {lang_display} speaker and will not understand English headings."
    )

    base_rules = f"""You are Dhara — an AI legal information assistant for Indian citizens.

{language_rule}{label_hint}

HARD RULES (do not break — the app will strip your reply if you break them):
1. NEVER write section numbers, article numbers, or clause numbers in your reply. Do NOT write "Article 21", "Section 35", "BNS", "BNSS", "BNSS 43(5)", "Section", "Article" etc. anywhere in your reply text. The user sees the exact citations in a separate box below your reply.
2. NEVER quote statutory text verbatim. Do NOT copy the words of the law. Only explain in your own plain words.
3. NEVER use markdown headers (# or ##). No bold with **. No emoji.
4. NEVER use Latin phrases or unexplained legal jargon.
5. If the law has an exception (except, unless, provided that, save in), your reply MUST mention the exception plainly. Never state a right as absolute if the law qualifies it.
6. If your VERIFIED SOURCES block is empty or missing, reply exactly: "{REFUSAL_NO_CORPUS}" and STOP.
7. If the question is about non-Indian law, or asks for personal/moral advice (should I forgive, should I marry, etc.), reply exactly: "{REFUSAL_NOT_LEGAL}" and STOP.

FORMAT — respond in exactly this two-part shape and nothing else. The two headings below appear here in English as placeholders; you MUST write them in {lang_display} in your reply:

<heading meaning "Answer:" in {lang_display}> <the direct answer in AT MOST TWO sentences, each under 15 words. First sentence must be the answer.>

<heading meaning "What you can do:" in {lang_display}>
- <one short bullet, plain action in {lang_display}>
- <one short bullet, plain action in {lang_display}>
- <one short bullet, plain action in {lang_display}>
- <optional 4th bullet in {lang_display}>
- <optional 5th bullet in {lang_display}>

Then a blank line, then the disclaimer line (also in {lang_display}).{verified_block}{disclaimer_line}
"""

    if is_pro:
        return base_rules + (
            f"\n\nPRO MODE: after the standard reply above, add another section titled with the {lang_display} "
            f"equivalent of 'For your situation:' (in {lang_display}) with 3–4 more bullets giving a step-by-step "
            f"action plan (offices to visit, forms, escalation contacts) — all in {lang_display}. "
            "Same rules — no section numbers, no verbatim law, no markdown headers."
        )
    return base_rules

# ---------- Auth ----------
@api.post("/auth/register", response_model=AuthOut)
async def register(body: RegisterIn):
    if not body.terms_accepted:
        raise HTTPException(400, "You must accept the Terms & Conditions to register")
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": uid,
        "email": body.email.lower(),
        "name": body.name,
        "phone": body.phone,
        "password_hash": hash_pw(body.password),
        "language": "en",
        "is_pro": False,
        "pro_since": None,
        "pro_samples_used": 0,
        "is_grandfathered": True,
        "state_jurisdiction": STATE_CODE_TO_JURISDICTION.get((body.state or "").upper(), ""),
        "terms_accepted": True,
        "terms_version": body.terms_version,
        "terms_accepted_at": now,
        "created_at": now,
    }
    await db.users.insert_one(doc)
    # Persist terms acknowledgement in a separate audit collection too
    await db.terms_acknowledgements.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "email": body.email.lower(),
        "name": body.name,
        "phone": body.phone,
        "terms_version": body.terms_version,
        "accepted_at": now,
        "source": "register",
    })
    return {"token": make_token(uid), "user": public_user(doc)}

@api.post("/auth/login", response_model=AuthOut)
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not check_pw(body.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid credentials")
    return {"token": make_token(user["id"]), "user": public_user(user)}


# ---- Google Sign-In via Emergent OAuth ----
class GoogleSessionIn(BaseModel):
    session_id: str

# Guard: prevent replaying the same session_id twice (deep links can fire twice on Android)
_USED_GOOGLE_SESSIONS: set[str] = set()

@api.post("/auth/session", response_model=AuthOut)
async def google_auth_session(body: GoogleSessionIn):
    """Exchange an Emergent OAuth session_id for a Dhara JWT.

    The frontend never calls Emergent directly — it only sends the session_id
    here. We call demobackend.emergentagent.com once, upsert the user by email
    (so existing email/password accounts are linked), and return our own JWT.
    """
    sid = body.session_id.strip()
    if sid in _USED_GOOGLE_SESSIONS:
        raise HTTPException(401, "Session already used")
    _USED_GOOGLE_SESSIONS.add(sid)
    # Keep the in-memory guard from growing unboundedly
    if len(_USED_GOOGLE_SESSIONS) > 5000:
        _USED_GOOGLE_SESSIONS.clear()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": sid},
            )
    except Exception:
        raise HTTPException(502, "Could not reach auth service")

    if r.status_code != 200:
        raise HTTPException(401, "Invalid or expired Google session")

    data = r.json()
    email = (data.get("email") or "").lower().strip()
    name  = (data.get("name")  or "").strip() or (email.split("@")[0] if email else "User")

    if not email:
        raise HTTPException(401, "Google did not return an email address")

    now = datetime.now(timezone.utc).isoformat()

    # Upsert: reuse existing account if the email is already registered
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        uid  = existing["id"]
        user = existing
    else:
        uid  = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "id":               uid,
            "email":            email,
            "name":             name,
            "phone":            "",
            "language":         "en",
            "is_pro":           False,
            "pro_since":        None,
            "pro_samples_used": 0,
            "is_grandfathered":  True,
            "state":            None,
            "state_jurisdiction": "",
            "terms_accepted":   True,
            "terms_version":    TERMS_VERSION,
            "terms_accepted_at": now,
            "auth_provider":    "google",
            "created_at":       now,
        }
        await db.users.insert_one(user)

    return {"token": make_token(uid), "user": public_user(user)}


# ---- Password reset via emailed one-time code (OTP) ----
# The old flow accepted an email + registered phone number and immediately issued
# a JWT. Anyone who knew a user's email and mobile number could take the account
# over, so it was replaced: the code is delivered to the mailbox on the account,
# is hashed at rest, expires in 10 minutes, is single-use, and is rate limited.
OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
_RESET_SENDS: dict[str, list[datetime]] = {}
_RESET_MAX_SENDS = 3
_RESET_SEND_WINDOW = timedelta(hours=1)
_RESET_MIN_GAP = timedelta(seconds=60)


def _prune_sends(email: str) -> list[datetime]:
    cutoff = datetime.now(timezone.utc) - _RESET_SEND_WINDOW
    kept = [t for t in _RESET_SENDS.get(email, []) if t > cutoff]
    _RESET_SENDS[email] = kept
    return kept


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordIn):
    """Step 1 — email a 6-digit one-time code to the address on the account.

    Always returns the same generic response so the endpoint cannot be used to
    discover which email addresses are registered.
    """
    if not email_configured():
        raise HTTPException(503, "Password reset by email is not configured on this server.")

    email = body.email.lower().strip()
    now = datetime.now(timezone.utc)
    sends = _prune_sends(email)
    if sends and (now - sends[-1]) < _RESET_MIN_GAP:
        raise HTTPException(429, "Please wait a minute before requesting another code.")
    if len(sends) >= _RESET_MAX_SENDS:
        raise HTTPException(429, "Too many reset requests. Please try again in an hour.")

    generic = {
        "sent": True,
        "message": "If that email is registered, we've sent a 6-digit code to it. It expires in 10 minutes.",
        "expires_in_minutes": OTP_TTL_MINUTES,
    }

    user = await db.users.find_one({"email": email})
    # Count the request either way so a missing account cannot be probed cheaply.
    _RESET_SENDS.setdefault(email, []).append(now)
    if not user:
        return generic

    code = f"{secrets.randbelow(1_000_000):06d}"
    await db.password_resets.update_one(
        {"email": email},
        {"$set": {
            "email": email,
            "user_id": user["id"],
            "code_hash": hash_pw(code),
            "expires_at": (now + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
            "attempts": 0,
            "used": False,
            "created_at": now.isoformat(),
        }},
        upsert=True,
    )

    subject, html = password_reset_otp_email(
        name=user.get("name") or "", code=code, minutes=OTP_TTL_MINUTES
    )
    # Fail closed: if the mail cannot be delivered, the user must not be told to
    # go looking for a code that will never arrive.
    await send_email(to=email, subject=subject, html=html)
    logger.info(f"password reset code emailed to {email}")
    return generic


@api.post("/auth/reset-password", response_model=AuthOut)
async def reset_password(body: ResetPasswordIn):
    """Step 2 — verify the emailed code, set the new password, sign the user in."""
    email = body.email.lower().strip()
    now = datetime.now(timezone.utc)
    rec = await db.password_resets.find_one({"email": email})
    invalid = HTTPException(400, "That code is not valid or has expired. Please request a new one.")
    if not rec or rec.get("used"):
        raise invalid
    if rec.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
        raise HTTPException(429, "Too many wrong codes. Please request a new one.")
    try:
        expired = datetime.fromisoformat(rec["expires_at"]) < now
    except Exception:
        expired = True
    if expired:
        await db.password_resets.delete_one({"email": email})
        raise invalid

    if not check_pw(body.code.strip(), rec["code_hash"]):
        await db.password_resets.update_one({"email": email}, {"$inc": {"attempts": 1}})
        raise invalid

    user = await db.users.find_one({"id": rec["user_id"]})
    if not user:
        raise invalid

    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_pw(body.new_password), "password_reset_at": now.isoformat()}},
    )
    await db.password_resets.delete_one({"email": email})
    _RESET_SENDS.pop(email, None)
    updated = await db.users.find_one({"id": user["id"]})
    return {"token": make_token(user["id"]), "user": public_user(updated)}

# ---- Account deletion (Google Play "Account deletion" requirement) ----
# Two paths, one shared underlying hard_delete_user() (see account_deletion.py)
# so they can never drift apart:
#   1. In-app (authenticated, Settings → Delete account) — re-auth by password.
#   2. Public web page, no login required (for users who already uninstalled
#      the app) — proves identity via emailed OTP instead of a session, same
#      pattern as /auth/forgot-password + /auth/reset-password.
# Both permanently erase the account and every user-linked collection — there
# is no soft-delete and no recovery window.
_DELETE_SENDS: dict[str, list[datetime]] = {}


def _prune_delete_sends(email: str) -> list[datetime]:
    cutoff = datetime.now(timezone.utc) - _RESET_SEND_WINDOW
    kept = [t for t in _DELETE_SENDS.get(email, []) if t > cutoff]
    _DELETE_SENDS[email] = kept
    return kept


async def _finish_deletion(user_id: str) -> None:
    """Shared tail of both deletion paths: hard-delete every collection,
    then best-effort tell the push relay to forget this user. A relay
    hiccup must never stop the account from actually being deleted."""
    await hard_delete_user(db, user_id)
    try:
        await unregister_device(user_id)
    except Exception as e:
        logger.warning(f"[account_deletion] push unregister failed for {user_id}: {type(e).__name__}: {e}")


@api.post("/account/delete")
async def delete_account_in_app(body: DeleteAccountIn, user: dict = Depends(current_user)):
    """In-app path. Requires re-entering the account password as proof of
    intent — a bare button tap is not enough for an irreversible action."""
    if not check_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect password.")
    await _finish_deletion(user["id"])
    return {"deleted": True}


@api.post("/account-deletion/request-otp")
async def request_deletion_otp(body: RequestDeletionOTPIn):
    """Public web page, step 1 — email a 6-digit one-time code. Always
    returns the same generic response so the endpoint cannot be used to
    discover which email addresses are registered."""
    if not email_configured():
        raise HTTPException(503, "Account deletion by email is not configured on this server.")

    email = body.email.lower().strip()
    now = datetime.now(timezone.utc)
    sends = _prune_delete_sends(email)
    if sends and (now - sends[-1]) < _RESET_MIN_GAP:
        raise HTTPException(429, "Please wait a minute before requesting another code.")
    if len(sends) >= _RESET_MAX_SENDS:
        raise HTTPException(429, "Too many requests. Please try again in an hour.")

    generic = {
        "sent": True,
        "message": "If that email is registered, we've sent a 6-digit code to it. It expires in 10 minutes.",
        "expires_in_minutes": OTP_TTL_MINUTES,
    }

    user = await db.users.find_one({"email": email})
    _DELETE_SENDS.setdefault(email, []).append(now)
    if not user:
        return generic

    code = f"{secrets.randbelow(1_000_000):06d}"
    await db.account_deletion_otps.update_one(
        {"email": email},
        {"$set": {
            "email": email,
            "user_id": user["id"],
            "code_hash": hash_pw(code),
            "expires_at": (now + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
            "attempts": 0,
            "used": False,
            "created_at": now.isoformat(),
        }},
        upsert=True,
    )

    subject, html = account_deletion_otp_email(name=user.get("name") or "", code=code, minutes=OTP_TTL_MINUTES)
    await send_email(to=email, subject=subject, html=html)
    logger.info(f"account deletion code emailed to {email}")
    return generic


@api.post("/account-deletion/verify")
async def verify_deletion_otp(body: VerifyDeletionOTPIn):
    """Public web page, step 2 — verify the emailed code and permanently
    delete the account. No login required; mailbox ownership IS the proof
    of identity for this one irreversible action."""
    email = body.email.lower().strip()
    now = datetime.now(timezone.utc)
    rec = await db.account_deletion_otps.find_one({"email": email})
    invalid = HTTPException(400, "That code is not valid or has expired. Please request a new one.")
    if not rec or rec.get("used"):
        raise invalid
    if rec.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
        raise HTTPException(429, "Too many wrong codes. Please request a new one.")
    try:
        expired = datetime.fromisoformat(rec["expires_at"]) < now
    except Exception:
        expired = True
    if expired:
        await db.account_deletion_otps.delete_one({"email": email})
        raise invalid

    if not check_pw(body.code.strip(), rec["code_hash"]):
        await db.account_deletion_otps.update_one({"email": email}, {"$inc": {"attempts": 1}})
        raise invalid

    user_id = rec["user_id"]
    await db.account_deletion_otps.delete_one({"email": email})
    _DELETE_SENDS.pop(email, None)
    await _finish_deletion(user_id)
    return {"deleted": True, "message": "Your Dhara account and all associated data have been permanently deleted."}

@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    out = public_user(user)
    # Today's LLM allowance. Free users share ONE 30-query/day bucket across
    # both text and voice — voice is an accessibility floor, not a premium
    # feature. Pro users are unlimited (no per-user cap).
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    is_pro = bool(user.get("is_pro"))
    if is_pro:
        # Unlimited — surface None so UI knows to hide the meter
        out["daily_queries_cap"] = None
        out["daily_queries_left"] = None
        # Backward-compat fields (some older clients may still read these)
        out["daily_questions_cap"] = None
        out["daily_questions_left"] = None
        out["daily_voice_cap"] = None
        out["daily_voice_left"] = None
    else:
        cap = FREE_DAILY_QUERIES
        q_doc = await db.usage_daily.find_one({"scope": "user", "user_id": user["id"], "day": day, "kind": "query"})
        used = int((q_doc or {}).get("count", 0))
        left = max(0, cap - used)
        out["daily_queries_cap"] = cap
        out["daily_queries_left"] = left
        # Backward-compat fields kept so older clients don't break
        out["daily_questions_cap"] = cap
        out["daily_questions_left"] = left
        out["daily_voice_cap"] = cap
        out["daily_voice_left"] = left
    return out

@api.patch("/auth/language")
async def update_language(payload: dict, user: dict = Depends(current_user)):
    lang = payload.get("language", "en")
    await db.users.update_one({"id": user["id"]}, {"$set": {"language": lang}})
    return {"ok": True, "language": lang}

@api.patch("/auth/state")
async def update_state(payload: dict, user: dict = Depends(current_user)):
    """Set the user's state / UT so state-specific rules (rent, liquor, traffic
    compounding, stamp duty) can be served alongside the central law."""
    code = (payload.get("state") or "").upper()
    if code and not is_valid_state(code):
        raise HTTPException(400, "Unknown state code")
    await db.users.update_one({"id": user["id"]}, {"$set": {"state": code or None}})
    return {"ok": True, "state": code or None, "state_name": state_name(code)}

@api.post("/auth/accept-terms")
async def accept_terms(body: AcceptTermsIn, user: dict = Depends(current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"terms_accepted": True, "terms_version": body.terms_version, "terms_accepted_at": now}},
    )
    await db.terms_acknowledgements.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "phone": user.get("phone"),
        "terms_version": body.terms_version,
        "accepted_at": now,
        "source": "in_app",
    })
    return {"ok": True, "terms_version": body.terms_version, "accepted_at": now}

# ---------- LLM spend metering ----------
async def meter_llm_use(user: dict, kind: str) -> None:
    """Count one paid LLM call for this user and for the app as a whole.

    kind is "question" (chat answer) or "voice" (transcription / spoken reply).

    Free users share a single 30-query/day bucket ("query" kind) covering both
    text and voice — voice is an accessibility floor, not a premium feature.
    Pro users are unlimited on a per-user basis; only the app-wide backstop
    applies to them.

    Raises HTTP 429 with a plain-language message + helplines when capped.
    Called ONLY on paths that actually hit the model.
    """
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    is_pro = bool(user.get("is_pro"))

    # App-wide backstop first — protects the key even if a single account is
    # compromised or many users spike on the same day.
    app_doc = await db.usage_daily.find_one_and_update(
        {"scope": "app", "day": day},
        {"$inc": {"count": 1}},
        upsert=True,
        return_document=True,
    )
    if int(app_doc.get("count", 0)) > APP_DAILY_LLM_CALLS:
        raise HTTPException(
            status_code=429,
            detail={
                "limit": True,
                "scope": "app",
                "message": "Dhara is unusually busy today and has paused new answers. Please try again tomorrow.",
            },
        )

    # Pro users have no per-user cap — only the app-wide backstop applies.
    if is_pro:
        return

    # Free users: unified "query" bucket for both text and voice.
    cap = FREE_DAILY_QUERIES
    doc = await db.usage_daily.find_one_and_update(
        {"scope": "user", "user_id": user["id"], "day": day, "kind": "query"},
        {"$inc": {"count": 1}},
        upsert=True,
        return_document=True,
    )
    used = int(doc.get("count", 0))
    if used > cap:
        raise HTTPException(
            status_code=429,
            detail={
                "limit": True,
                "scope": "user",
                "kind": "query",
                "used": used - 1,
                "cap": cap,
                "is_pro": False,
                "message": (
                    f"You've used all {cap} free questions for today. "
                    "Upgrade to Pro for unlimited access, or come back tomorrow.\n\n"
                    "In an emergency, free help is available:\n"
                    "• NALSA Legal Aid: 15100 (free)\n"
                    "• Consumer Helpline: 1800-11-4000 (toll-free)"
                ),
                "helplines": [
                    {"name": "NALSA Legal Aid", "number": "15100"},
                    {"name": "Consumer Helpline", "number": "1800-11-4000"},
                ],
            },
        )

async def translate_for_retrieval(text: str, model_provider: str, model_name: str) -> str:
    """One-shot, non-streaming translation of a non-English question into English,
    used ONLY so the deterministic corpus retrieval (English keywords) can find
    the right verified law. Never shown to the user and never treated as a legal
    source itself — the verified corpus text remains the only source of truth for
    the answer; this call only helps the search understand what was asked. Falls
    back to the original text on any failure so a translation hiccup can never
    turn into a broken chat.

    Bug-fix: added asyncio.wait_for(timeout=7 s) so a cold-start or slow LLM
    response never blocks the retrieval pipeline indefinitely, which was causing
    intermittent "no verified source" fallbacks for valid Hindi queries.
    """
    import asyncio as _aio

    def _is_mostly_english(s: str) -> bool:
        """True when the string is predominantly ASCII text (i.e. English-script)."""
        if not s:
            return False
        non_ascii = sum(1 for c in s if ord(c) >= 128)
        return non_ascii / max(len(s), 1) < 0.25  # <25% non-ASCII → likely English

    try:
        translator = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"retrieval-translate-{uuid.uuid4()}",
            system_message=(
                "You are a legal keyword extractor for an Indian law search engine. "
                "Given a question in any Indian language, output ONLY 4-6 space-separated "
                "English keywords that best represent the legal topic. Include: the act name "
                "(abbreviated if known), section number if mentioned, and the key legal nouns. "
                "NEVER output a full sentence. NEVER output punctuation. "
                "Examples:\n"
                "Input: 'बिना हेलमेट के जुर्माना' → Output: helmet fine penalty Motor Vehicles Act\n"
                "Input: 'दहेज के लिए उत्पीड़न' → Output: dowry harassment Dowry Prohibition Act IPC 498A\n"
                "Input: 'UPI धोखाधड़ी शिकायत' → Output: UPI fraud cyber crime IT Act cheating\n"
                "Input: 'किरायेदार बेदखली' → Output: tenant eviction rent landlord Transfer Property Act\n"
                "Output ONLY the keywords — no explanation, no notes."
            ),
        ).with_model(model_provider, model_name)
        result = await _aio.wait_for(
            translator.send_message(UserMessage(text=text)),
            timeout=7.0,   # never block retrieval > 7 s
        )
        out = str(result or "").strip().strip('"').strip()
        if out and _is_mostly_english(out) and out != text:
            logger.info("retrieval-translate | ok | q=%r | → %r", text[:80], out[:80])
            print(f"[RTRANSLATE] OK q={text[:40]!r} → {out[:60]!r}", flush=True)
            return out
        else:
            logger.warning(
                "retrieval-translate | BAD_OUTPUT | q=%r | got=%r",
                text[:80], out[:80],
            )
            print(f"[RTRANSLATE] BAD_OUTPUT got={out[:60]!r}", flush=True)
            return text
    except _aio.TimeoutError:
        logger.warning(
            "retrieval-translate | TIMEOUT (7 s) | q=%r | falling back to original",
            text[:80],
        )
        print(f"[RTRANSLATE] TIMEOUT q={text[:60]!r}", flush=True)
        return text
    except Exception as exc:
        logger.warning("retrieval translation failed; falling back to original text", exc_info=True)
        print(f"[RTRANSLATE] EXCEPTION {type(exc).__name__}: {exc!s:.100}", flush=True)
        return text

# ---------- Client-side error logging ----------
# The chat UI swallows real JS/network exceptions into a friendly "Something
# went wrong" message so users never see a stack trace. That previously meant
# a real failure (e.g. a native chunked-response read failing) left NO trace
# anywhere — the next investigation was pure guesswork. This endpoint gives
# every such failure a durable, inspectable record, without ever surfacing
# the raw error back to the user. Deliberately minimal: no PII beyond the
# already-authenticated user id, capped message length, best-effort (the
# client fires this and ignores its result).
@api.post("/client-error-log")
async def client_error_log(body: ClientErrorLogIn, user: dict = Depends(current_user)):
    await db.client_error_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "context": body.context[:100],
        "error_name": (body.error_name or "")[:200],
        "error_message": (body.error_message or "")[:1000],
        "platform": (body.platform or "")[:20],
        "retried": bool(body.retried),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}

# ---------- Push notifications (Emergent-managed / SuprSend relay) ----------
# Registers this device's push token with the relay so it can be targeted by
# user_id later (daily nudge + dead-law bookmark alert — see push_jobs.py, or
# any future ad-hoc send). Never stores the raw device token in our own DB —
# the relay is the source of truth for token -> user_id mapping.
@api.post("/register-push")
async def register_push(body: RegisterPushBody, user: dict = Depends(current_user)):
    if body.user_id != user["id"]:
        raise HTTPException(403, "user_id mismatch")
    try:
        await register_device(user_id=body.user_id, platform=body.platform, device_token=body.device_token)
    except Exception as e:
        logger.warning(f"[push] register_push failed for user {user['id']}: {type(e).__name__}: {e}")
        # Never fail the caller's app flow over a push-registration hiccup —
        # the user just won't get push this session; nothing else breaks.
        return {"status": "failed"}
    return {"status": "registered"}

# ---------- Chat ----------
@api.post("/chat/stream")
async def chat_stream(body: ChatIn, user: dict = Depends(current_user)):
    session_id = body.session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # -------- Paywall enforcement for Pro-mode capabilities --------
    # Basic mode → always allowed, unlimited.
    # Pro mode + is_pro → allowed, no counter.
    # Pro mode + not is_pro + samples_used < N → allowed as SAMPLE (increment counter).
    # Pro mode + not is_pro + samples_used >= N → HTTP 402 with paywall payload.
    mode = (body.mode or "basic").lower()
    is_pro_user = bool(user.get("is_pro"))
    samples_used = int(user.get("pro_samples_used", 0))
    is_sample_consumption = False
    # Advocate mode: professional prompt for licensed advocates — no paywall
    is_advocate_mode = (mode == "advocate")

    if mode == "pro" and not is_pro_user and not is_advocate_mode:
        if samples_used >= PRO_FREE_SAMPLES:
            # Log the blocked attempt so the operator sees who's hitting the paywall
            # and what they were trying to ask. Otherwise the query vanishes from the DB.
            try:
                await db.messages.insert_one({
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "user_id": user["id"],
                    "role": "user",
                    "content": body.message,
                    "language": body.language,
                    "mode": mode,
                    "status": "blocked_paywall",
                    "created_at": now,
                    "timestamp": now,
                })
            except Exception:
                logger.exception("Failed to log paywall-blocked query")
            raise HTTPException(
                status_code=402,
                detail={
                    "paywall": True,
                    "reason": "pro_samples_exhausted",
                    "samples_used": samples_used,
                    "samples_limit": PRO_FREE_SAMPLES,
                    "pro_price_inr_paise": PRO_PRICE_INR,
                    "pro_price_label": PRO_PRICE_LABEL,
                    "pro_price_usd_cents": PRO_PRICE_USD,
                    "pro_price_usd_label": PRO_PRICE_USD_LABEL,
                    "message": (
                        f"You've used all {PRO_FREE_SAMPLES} free Pro-quality samples. "
                        "Upgrade to Pro to unlock unlimited lawyer-style deep answers, drafts, "
                        "action plans and escalation paths."
                    ),
                },
            )
        is_sample_consumption = True

    session = await db.sessions.find_one({"id": session_id, "user_id": user["id"]})
    if not session:
        title = body.message[:60]
        await db.sessions.insert_one({
            "id": session_id,
            "user_id": user["id"],
            "title": title,
            "language": body.language,
            "mode": mode,
            "tier": "pro" if is_pro_user else "free",
            "created_at": now,
            "updated_at": now,
        })

    await db.messages.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": user["id"],
        "role": "user",
        "content": body.message,
        "language": body.language,
        "mode": mode,
        "status": "ok",  # updated below if refusal fires
        "created_at": now,
        "timestamp": now,  # explicit alias for CSV clarity
    })

    # -------- Retrieval-language bridge (Hindi/Indic search fix) --------
    retrieval_text = body.message
    _is_indic = needs_retrieval_translation(body.message)
    if _is_indic:
        retrieval_text = await translate_for_retrieval(body.message, body.model_provider, body.model_name)
        _same = retrieval_text == body.message
        logger.info(
            "retrieval-bridge | indic=True | translation_ok=%s | q=%r | t=%r",
            not _same, body.message[:80], retrieval_text[:80],
        )
    else:
        logger.info("retrieval-bridge | indic=False | q=%r", body.message[:80])

    # -------- Retrieval + citation integrity (P1) --------
    # (a) Non-legal / non-Indian jurisdiction → hard refusal, no LLM call
    early_refusal: Optional[str] = None
    if is_non_indian_jurisdiction(retrieval_text):
        early_refusal = REFUSAL_NON_INDIAN
    elif is_non_legal_advice(retrieval_text):
        early_refusal = REFUSAL_NOT_LEGAL

    # -------- Personal-law disambiguation (marriage/succession) --------
    # Hindu Marriage Act vs Special Marriage Act vs Muslim/Christian personal
    # law (same for succession) give DIFFERENT sections for the same real-life
    # question — answering under the wrong one is a wrong citation. Ask once
    # (remembered for the rest of THIS chat thread) instead of guessing; see
    # personal_law.py for the full design note.
    personal_law_topic: Optional[str] = None
    personal_law_note: Optional[str] = None
    if not early_refusal:
        personal_law_topic = classify_personal_law_topic(retrieval_text)
        if personal_law_topic:
            personal_law_ctx = detect_personal_law_context(retrieval_text) or (
                (session or {}).get("personal_law_context") or {}
            ).get(personal_law_topic)
            if not personal_law_ctx:
                early_refusal = disambiguation_question(personal_law_topic, body.language)
            else:
                await db.sessions.update_one(
                    {"id": session_id},
                    {"$set": {f"personal_law_context.{personal_law_topic}": personal_law_ctx}},
                )
                hint = act_hint_phrase(personal_law_ctx, personal_law_topic)
                if hint:
                    retrieval_text = f"{retrieval_text} ({hint})"
                personal_law_note = act_disclaimer(personal_law_ctx, personal_law_topic, body.language)

    # (b) Corpus retrieval — deterministic keyword match against verified statutes
    retrieved = [] if early_refusal else corpus_retrieve(retrieval_text, limit=3)

    # (b0) State / UT layer — rent, liquor, traffic compounding and stamp duty are
    # state subjects. If the user has told us their state we serve its verified
    # rules ALONGSIDE the central law; we never substitute another state's rule.
    user_state = (user.get("state") or "").upper()
    state_hits = [] if early_refusal else corpus_retrieve_state(retrieval_text, user_state, limit=2)
    state_topic = None if early_refusal else state_sensitive_topic(retrieval_text)

    # (b1) Citation integrity: if the user's query explicitly names a section/article
    # identifier (e.g. "BNS Section 999", "Article 350", "BNSS 220") and NONE of the
    # retrieved entries actually match that identifier, void the retrieval. Otherwise
    # unrelated but keyword-adjacent chips would appear alongside a refusal, which is
    # dangerous and contradicts the P1 accuracy rule.
    if retrieved and not early_refusal:
        import re as _re_id
        def _norm_short(s: str) -> str:
            return _re_id.sub(r"[^a-z0-9()]+", " ", (s or "").lower()).strip()
        query_ids: list[str] = []
        # "Article 21", "Article 21A"
        for m in _re_id.finditer(r"\b[Aa]rticle\s+(\d+[A-Za-z]?)\b", retrieval_text):
            query_ids.append(f"article {m.group(1).lower()}")
        # "BNS Section 999", "BNSS Section 43(5)", "Sec. 43 BNSS", "BNSS 43(5)",
        # "RTI Section 6", "CPA 34", "MV 185", "Motor Vehicles Section 185"
        for m in _re_id.finditer(
            r"\b(BNS|BNSS|BSA|IPC|CrPC|PWDVA|RTI|CPA|MV|MVA)\b[^\w]*(?:Sec(?:tion|\.)?\s*)?(\d+[A-Za-z]?(?:\(\d+\))?)\b",
            retrieval_text, _re_id.IGNORECASE,
        ):
            query_ids.append(f"{m.group(1).lower()} {m.group(2).lower()}")
        if query_ids:
            hit_labels = { _norm_short(it["short_label"]) for it in retrieved }
            if not any(qid in hit_labels or any(qid in hl for hl in hit_labels) for qid in query_ids):
                # Query names an identifier we don't cover → void retrieval so user sees refusal only
                retrieved = []

    # (b2) MongoDB corpus — 70,397 sections across CENTRAL + 12 states.
    # Runs ALONGSIDE the Python corpus, not instead of it. Python corpus
    # contributes scope_notes and citizen-language explanations; MongoDB
    # contributes verbatim government text and breadth (2,120 Acts).
    # Three safety guards enforced in code (not prompts):
    #   G1 — dead_warning  : serve_warning prepended for is_dead_law sections
    #   G2 — judicial_flag : user_warning from judicial_invalidations (status != UPHELD)
    #   G3 — badge         : verify_tier==1 + verified_by → "Advocate Verified"
    db_hits: list[dict] = []
    if not early_refusal:
        try:
            db_hits = await db_retrieve(corpus_db, retrieval_text, state_code=user_state or None, limit=3)
        except Exception:
            db_hits = []   # MongoDB unavailable — Python corpus handles it

    # (b3) Cross-corpus citation-conflict guard. Logged issue, now fixed:
    # querying "Information Technology Act section 66A" surfaced the hand-
    # curated Python-corpus entry "IT 43" FIRST (it scores on the generic
    # phrase "information technology act", which the query obviously
    # contains), ahead of MongoDB's own exact match for the section the user
    # actually asked about. The (b1) integrity check above only recognises a
    # closed whitelist of Act prefixes (BNS, IPC, MV, ...) and never covers
    # this case since "Information Technology" isn't one of them.
    #
    # Generalised fix: whenever the query cites an explicit section number
    # AND MongoDB found an EXACT match for that exact number, any Python-
    # corpus hit whose OWN section number (parsed off the end of its
    # short_label, e.g. "43" in "IT 43") is a DIFFERENT number is dropped —
    # the user asked about one specific section, not "something in this Act
    # family". Hits with no trailing number (e.g. "Cyber report 1930" is a
    # helpline, not a section) are left untouched.
    if retrieved and db_hits and not early_refusal:
        _cited_sec_match = re.search(
            r"(?:section|sections|sec|s\.|art(?:icle)?\.?)\s*(\d+[A-Za-z]{0,3})",
            retrieval_text, re.IGNORECASE,
        )
        if _cited_sec_match:
            _cited_sec = _cited_sec_match.group(1).upper()
            if any((h.get("section_number") or "").upper() == _cited_sec for h in db_hits):
                def _own_section_number(short_label: str) -> Optional[str]:
                    m = re.search(r"(\d+[A-Za-z]{0,3})$", short_label or "")
                    return m.group(1).upper() if m else None
                retrieved = [
                    it for it in retrieved
                    if _own_section_number(it.get("short_label", "")) in (None, _cited_sec)
                ]

    # Orphan-invalidation check — sections in judicial_invalidations but NOT
    # in legal_sections (e.g. IPC §377: IPC replaced by BNS, absent from corpus
    # but Supreme Court ruling is tracked).  Fires only when db_hits is empty.
    db_orphan: dict | None = None
    if not early_refusal and not db_hits:
        try:
            db_orphan = await db_orphan_check(corpus_db, retrieval_text)
        except Exception:
            db_orphan = None

    # (c) If no retrieval hit AND no early refusal, we still refuse (no verified source).
    # db_hits = MongoDB verbatim sections; db_orphan = standalone judicial ruling
    # for an act not in the corpus.  Either of these counts as a verified source.
    if not early_refusal and not retrieved and not state_hits and not db_hits and not db_orphan:
        early_refusal = REFUSAL_NO_CORPUS

    logger.info(
        "retrieval-result | corpus=%d | state=%d | db=%d | orphan=%s | branch=%s",
        len(retrieved), len(state_hits), len(db_hits),
        bool(db_orphan),
        "refusal" if early_refusal else "rag",
    )

    # (c0) Cross-engine noise suppression (general rule, not per-Act — lives
    # here once, not duplicated per topic). The curated Python corpus
    # (`retrieved`) is hand-verified: every entry was deliberately keyword-
    # tagged for that exact scenario. MongoDB's fuzzy $text search, in
    # contrast, can pass a hit on nothing more than two generic words ("day",
    # "every") shared with a completely unrelated Act — e.g. "my husband
    # beats me every day" once also surfaced "The Representation of the
    # People Act... paid holiday to employees on the day of poll" (shared
    # words: "day", "every"), and "can an Indian marry twice" surfaced "The
    # National Commission for Indian System of Medicine Act" (shared word:
    # "indian"). `is_anchored` (corpus_db.py) marks a MongoDB hit as
    # STRUCTURALLY trustworthy — an exact section-number lookup, or an
    # explicit Act-label match — as opposed to bare generic-word overlap.
    # Once ANY verified answer already exists for this query (the curated
    # corpus answered, OR MongoDB itself found an anchored hit), a
    # non-anchored MongoDB hit adds noise, not evidence, and is dropped. It
    # is kept ONLY when it is the sole thing found for the query at all —
    # never leaving the user with a refusal just because the one hit we have
    # happens to be unanchored.
    if db_hits and (retrieved or any(h.get("is_anchored") for h in db_hits)):
        db_hits = [h for h in db_hits if h.get("is_anchored")]

    # (c1) Merge the state rules into the citation list the user will see. State
    # rules go LAST so the central position is read first, and the combined list
    # stays capped at three chips.
    if state_hits:
        keep_central = max(0, 3 - len(state_hits))
        retrieved = retrieved[:keep_central] + state_hits

    # -------- Refusal analytics (A4 instrumentation) --------
    # Anonymized, aggregate-only event: NO user_id, NO session_id, NO raw
    # query text — only cause code, topic bucket, language, jurisdiction
    # (currently always null — no state field exists yet), and the best
    # retrieval candidate's score even when it fell below the confidence
    # threshold or nothing matched at all. This lets us tell "no law in the
    # corpus for this topic" apart from "a candidate existed but scored too
    # low" apart from "the query was too vague to score anything" — a
    # decision on where to spend corpus-building credits should never be
    # made without this breakdown.
    if early_refusal:
        if early_refusal == REFUSAL_NON_INDIAN:
            cause_code = "non_indian_jurisdiction"
            sub_cause = None
            dbg = {"top_score": None, "top_key": None, "content_tokens": None}
        elif early_refusal == REFUSAL_NOT_LEGAL:
            cause_code = "not_legal_advice_request"
            sub_cause = None
            dbg = {"top_score": None, "top_key": None, "content_tokens": None}
        elif personal_law_topic and personal_law_note is None:
            # This early_refusal is the disambiguation clarifying question,
            # not a genuine "nothing verified for this topic" refusal.
            cause_code = "personal_law_disambiguation"
            sub_cause = personal_law_topic
            dbg = {"top_score": None, "top_key": None, "content_tokens": None}
        else:
            cause_code = "no_corpus_match"
            dbg = top_candidate_debug(retrieval_text)
            if dbg["top_score"] == 0 and dbg["content_tokens"] <= 1:
                sub_cause = "query_too_vague"
            elif dbg["top_score"] == 0:
                sub_cause = "no_candidate_scored"  # true coverage gap OR a
                # phrasing mismatch against an entry that already exists —
                # only a human spot-check of a sample can tell those apart;
                # the score alone cannot.
            else:
                sub_cause = "below_confidence_threshold"  # candidate existed
                # (dbg["top_key"]) but scored under RETRIEVAL_MIN_SCORE — a
                # retrieval-tuning question, not necessarily a missing law.
        try:
            await db.refusal_events.insert_one({
                "id": str(uuid.uuid4()),
                "cause_code": cause_code,
                "sub_cause": sub_cause,
                "category": classify_topic(retrieval_text),
                "language": body.language,
                "state": user_state or None,
                "top_score": dbg["top_score"],
                "top_key": dbg["top_key"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            logging.getLogger(__name__).warning("refusal_events insert failed", exc_info=True)

    # Build the verified-source context for the prompt (used ONLY when we have hits)
    corpus_context = ""
    if retrieved:
        corpus_context = "\n---\n".join([
            (
                f"STATE RULE — applies in {state_name(it['state'])} only: {it['scope_note']}"
                if it.get("state") else f"Scope: {it['scope_note']}"
            )
            for it in retrieved
        ])

    # Merge MongoDB corpus hits into context.  Safety guards (G1 dead-law, G2
    # judicial-invalidation) are encoded as SAFETY WARNING / JUDICIAL ALERT
    # lines BEFORE the statutory text so the LLM reads them first.
    if db_hits:
        db_parts: list[str] = []
        for hit in db_hits:
            lines: list[str] = []
            if hit.get("dead_warning"):
                lines.append(f"SAFETY WARNING (DEAD LAW): {hit['dead_warning']}")
            if hit.get("judicial_flag"):
                lines.append(f"JUDICIAL ALERT: {hit['judicial_flag']}")
            sec_heading = hit.get("section_heading", "")
            act_label = f"{hit.get('act_name', '')}, Section {hit.get('section_number', '')}"
            if sec_heading:
                act_label += f" — {sec_heading}"
            lines.append(f"Source: {act_label}")
            if hit.get("no_current_text"):
                lines.append(
                    "NOTE: Current statutory text for this section is not available "
                    "in the corpus — the act may have been repealed or replaced by "
                    "successor legislation (e.g. IPC superseded by BNS). "
                    "Tell the user plainly that this section may no longer be in force "
                    "and advise them to consult an advocate for the current legal position."
                )
            else:
                sec_text = (hit.get("section_text") or "")[:600]
                if sec_text:
                    lines.append(f"Text: {sec_text}")
            db_parts.append("\n".join(lines))
        db_block = "\n---\n".join(db_parts)
        corpus_context = (corpus_context + "\n---\n" + db_block) if corpus_context else db_block

    # Orphan judicial warnings (section in judicial_invalidations but NOT in
    # legal_sections — e.g. IPC §377).  No statutory text available, but the
    # ruling itself is the verified source.
    if db_orphan:
        orphan_line = (
            f"JUDICIAL ALERT [{db_orphan.get('status', '')}]: {db_orphan.get('user_warning', '')}\n"
            f"Note: '{db_orphan.get('act_name', '')}' may no longer be in force in its original form "
            "(e.g. replaced by a successor code). Advise the user to consult an advocate for current law."
        )
        corpus_context = (corpus_context + "\n---\n" + orphan_line) if corpus_context else orphan_line
    # Tell the model, in plain words, when the local rule is the missing piece so
    # it never presents the central position as the complete answer.
    if state_topic and not state_hits:
        if user_state:
            corpus_context += (
                f"\n---\nJURISDICTION GAP: {state_topic['label']} are decided by STATE law and "
                f"no verified rule for {state_name(user_state)} is available. Say plainly that the "
                f"local rule decides this and that the user must confirm it with "
                f"{state_topic['authority']}. Do NOT state any local amount, limit or deadline."
            )
        else:
            corpus_context += (
                f"\n---\nJURISDICTION GAP: {state_topic['label']} are decided by STATE law and the "
                "user has not told us their state. Say plainly that the answer depends on their "
                "state and ask them to set their state in the app. Do NOT state any local amount, "
                "limit or deadline."
            )

    # Pro-quality prompt if user is Pro OR consuming a free sample; else basic prompt.
    use_pro_prompt = is_pro_user or is_sample_consumption

    # Daily LLM spend cap — only counted when we are actually going to call the
    # model (a refusal costs nothing, so it must not eat the user's allowance).
    if not early_refusal:
        await meter_llm_use(user, "question")

    # Derive native name — fall back to LANGUAGES table if client didn't send it
    lang_native = body.language_native
    if not lang_native:
        for _lang in LANGUAGES:
            if _lang["code"] == body.language:
                lang_native = _lang.get("native")
                break
    system_prompt = build_system_prompt(
        body.language_name,
        is_pro=use_pro_prompt,
        corpus_context=corpus_context,
        language_native=lang_native,
        advocate_mode=is_advocate_mode,
    )

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(body.model_provider, body.model_name)

    def sse(obj: dict) -> bytes:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")

    async def save_assistant(content: str, error: Optional[str] = None):
        now_ts = datetime.now(timezone.utc).isoformat()
        # Infer status for CSV exports & analytics
        if error:
            status = "error"
        elif early_refusal == REFUSAL_NO_CORPUS:
            status = "refused_no_corpus"
        elif early_refusal == REFUSAL_NON_INDIAN:
            status = "refused_non_indian"
        elif early_refusal == REFUSAL_NOT_LEGAL:
            status = "refused_not_legal"
        elif personal_law_topic and personal_law_note is None and early_refusal:
            status = "personal_law_disambiguation_asked"
        else:
            status = "ok"
        doc = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user["id"],
            "role": "assistant",
            "content": content,
            "language": body.language,
            "mode": mode,
            "model_provider": body.model_provider,
            "model_name": body.model_name,
            "tier": "pro" if is_pro_user else "free",
            "sample_consumed": is_sample_consumption,
            "status": status,
            "created_at": now_ts,
            "timestamp": now_ts,
        }
        if error:
            doc["error"] = error
        # Also attach the citations that the user was shown, so the CSV export
        # can show what verified statutes accompanied each answer.
        if retrieved:
            doc["citations"] = [
                {"short_label": it.get("short_label", ""), "citation": it.get("citation", "")}
                for it in retrieved
            ]
        await db.messages.insert_one(doc)
        await db.sessions.update_one(
            {"id": session_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        # Only debit a sample if the assistant actually returned real content (not empty error).
        if is_sample_consumption and content and not error:
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {"pro_samples_used": 1}},
            )

    async def event_gen() -> AsyncGenerator[bytes, None]:
        yield sse({
            "type": "session",
            "session_id": session_id,
            "tier": "pro" if is_pro_user else "free",
            "mode": mode,
            "sample_consumed": is_sample_consumption,
            "samples_remaining_after": max(0, PRO_FREE_SAMPLES - samples_used - (1 if is_sample_consumption else 0)),
        })
        # Emit verified citations FIRST — the UI shows these in a separate boxed panel.
        # The model is instructed NEVER to include section numbers/statutory text in its
        # own reply; the source of truth is here (from corpus.py).
        for it in retrieved:
            yield sse({"type": "citation", "citation": public_citation(it)})

        # Emit MongoDB-corpus citations.  G1/G2 safety warnings are prepended to
        # official_text so they appear at the top of the citation card in the UI.
        for hit in db_hits:
            dead_warn = hit.get("dead_warning") or ""
            ji_warn = hit.get("judicial_flag") or ""
            warning_prefix = "\n\n".join(filter(None, [dead_warn, ji_warn]))
            if hit.get("no_current_text"):
                no_text_notice = (
                    "⚠️ Current statutory text is not available for this section. "
                    "This may reflect a repeal or replacement by successor legislation. "
                    "Please consult an advocate for the current legal position."
                )
                official = (warning_prefix + "\n\n" + no_text_notice) if warning_prefix else no_text_notice
            else:
                raw_text = (hit.get("section_text") or "")[:2000]
                official = (warning_prefix + "\n\n" + raw_text) if warning_prefix else raw_text
            sec_heading = hit.get("section_heading", "")
            act_label = (
                f"{hit.get('act_name', '')}, Section {hit.get('section_number', '')}"
                + (f" — {sec_heading}" if sec_heading else "")
            )
            yield sse({
                "type": "citation",
                "citation": {
                    "key": f"{hit.get('act_name', '')} § {hit.get('section_number', '')}",
                    "citation": act_label,
                    "short_label": f"§ {hit.get('section_number', '')}",
                    "act": hit.get("act_name", ""),
                    "official_text": official,
                    "source_url": hit.get("source_url") or "",
                    "verified_at": hit.get("badge") or "Sourced from Government of India",
                    "text_kind": "verbatim" if not hit.get("no_current_text") else "judicial_ruling",
                    "state": None if (hit.get("jurisdiction") or "CENTRAL") == "CENTRAL" else hit.get("jurisdiction"),
                    "is_dead_law": hit.get("is_dead_law", False),
                    "dead_warning": hit.get("dead_warning"),
                    "judicial_flag": hit.get("judicial_flag"),
                    "no_current_text": hit.get("no_current_text", False),
                },
            })

        # Orphan judicial-invalidation warning (section in judicial_invalidations
        # but NOT in legal_sections — e.g. IPC §377 replaced by BNS).
        if db_orphan:
            yield sse({
                "type": "citation",
                "citation": {
                    "key": f"{db_orphan.get('act_name', '')} § {db_orphan.get('section_number', '')}",
                    "citation": (
                        f"{db_orphan.get('act_name', '')}, Section {db_orphan.get('section_number', '')}"
                        f" [{db_orphan.get('status', '')}]"
                    ),
                    "short_label": f"§ {db_orphan.get('section_number', '')}",
                    "act": db_orphan.get("act_name", ""),
                    "official_text": db_orphan.get("user_warning", ""),
                    "source_url": "",
                    "verified_at": "Judicial Ruling",
                    "text_kind": "judicial_ruling",
                    "state": None,
                    "is_dead_law": False,
                    "judicial_flag": db_orphan.get("user_warning"),
                    "status": db_orphan.get("status"),
                },
            })

        # State-jurisdiction signalling. Two distinct cases, both honest:
        #  - the user has no state set → ask for it once, in context
        #  - the state is known but we hold no verified local rule yet → say so
        if state_topic and not state_hits:
            if not user_state:
                yield sse({
                    "type": "state_prompt",
                    "topic": state_topic["topic"],
                    "label": state_topic["label"],
                    "message": (
                        f"{state_topic['label'].capitalize()} are decided by state law. "
                        "Set your state once to get the rules that actually apply to you."
                    ),
                })
            else:
                yield sse({
                    "type": "state_note",
                    "topic": state_topic["topic"],
                    "state": user_state,
                    "message": (
                        f"No verified {state_topic['label']} rule for {state_name(user_state)} is "
                        f"in Dhara yet. Confirm the local position with {state_topic['authority']}."
                    ),
                })

        # Refusal path — do not call the LLM. Send the refusal as a delta so the frontend
        # shows it in the normal chat bubble.
        if early_refusal:
            # Localize the refusal into the user's selected language (falls back to English)
            refusal_text = localize_refusal(early_refusal, body.language)
            yield sse({"type": "delta", "content": refusal_text})
            await save_assistant(refusal_text, error=None)
            yield sse({"type": "done"})
            return

        full = ""
        errored: Optional[str] = None
        try:
            async for ev in chat.stream_message(UserMessage(text=body.message)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    yield sse({"type": "delta", "content": ev.content})
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.exception("LLM stream error")
            errored = str(e)[:300]
            yield sse({"type": "error", "error": errored})

        # Post-processing runs outside try/finally so that a `return` here can
        # never swallow an in-flight exception (the except above already handles
        # stream failures).
        # Citation-integrity: strip any leaked section/article/statute names from
        # the model's output. The verified citations are shown by the UI from the
        # `citation` frames — the model MUST NOT emit them itself.
        sanitized = sanitize_model_output(full) if full else full

        # Reply-language enforcement. A user who selected Tamil and receives
        # English has been given nothing, so if the finished reply is not in the
        # expected script we translate it ONCE and overwrite the bubble.
        if sanitized and not errored and needs_language_repair(sanitized, body.language):
            lang_display = (
                f"{body.language_name} ({lang_native})"
                if lang_native and lang_native != body.language_name
                else body.language_name
            )
            logger.warning("reply-language repair: model answered outside the %s script", lang_display)
            try:
                fixer = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"{session_id}-langfix",
                    system_message=repair_prompt(lang_display),
                ).with_model(body.model_provider, body.model_name)
                translated = await fixer.send_message(UserMessage(text=sanitized))
                translated = sanitize_model_output(str(translated or "")).strip()
                if translated and not needs_language_repair(translated, body.language):
                    sanitized = translated
            except Exception:
                logger.exception("reply-language repair failed")

        # Append the personal-law disclaimer (see above) so the user always
        # sees which religion/marriage-type's law was applied.
        if personal_law_note and not errored and (sanitized or full):
            sanitized = (sanitized or full) + f"\n\n{personal_law_note}"

        if sanitized != full:
            # Overwrite the accumulated text on the client with the sanitized version.
            yield sse({"type": "final", "content": sanitized})
        await save_assistant(sanitized or full, errored)
        yield sse({"type": "done"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )

@api.get("/chat/sessions")
async def list_sessions(user: dict = Depends(current_user)):
    sessions = await db.sessions.find({"user_id": user["id"]}, {"_id": 0}).sort("updated_at", -1).to_list(200)
    return sessions

@api.get("/chat/sessions/{session_id}/messages")
async def session_messages(session_id: str, user: dict = Depends(current_user)):
    session = await db.sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not session:
        raise HTTPException(404, "Session not found")
    msgs = await db.messages.find({"session_id": session_id, "user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return {"session": session, "messages": msgs}

@api.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(current_user)):
    await db.sessions.delete_one({"id": session_id, "user_id": user["id"]})
    await db.messages.delete_many({"session_id": session_id, "user_id": user["id"]})
    return {"ok": True}

# ---------- Saved answers (bookmarks) ----------
# The device keeps its own copy in AsyncStorage so a saved answer opens with no
# network at all (the "standing in a police station" case). The server copy is
# only a sync target so the collection survives a reinstall or a new phone.
class BookmarkIn(BaseModel):
    client_id: str
    question: str
    answer: str
    language: str = "en"
    citations: List[dict] = []
    created_at: Optional[str] = None


@api.get("/bookmarks")
async def list_bookmarks(user: dict = Depends(current_user)):
    items = await db.bookmarks.find(
        {"user_id": user["id"], "deleted": {"$ne": True}}, {"_id": 0, "user_id": 0}
    ).sort("created_at", -1).to_list(500)
    return items


@api.put("/bookmarks")
async def upsert_bookmark(body: BookmarkIn, user: dict = Depends(current_user)):
    """Idempotent on (user, client_id) so the device can re-push its queue after
    being offline without creating duplicates."""
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "client_id": body.client_id,
        "user_id": user["id"],
        "question": body.question,
        "answer": body.answer,
        "language": body.language,
        "citations": body.citations,
        "created_at": body.created_at or now,
        "deleted": False,
        "synced_at": now,
    }
    await db.bookmarks.update_one(
        {"user_id": user["id"], "client_id": body.client_id},
        {"$set": doc, "$setOnInsert": {"id": str(uuid.uuid4())}},
        upsert=True,
    )
    saved = await db.bookmarks.find_one(
        {"user_id": user["id"], "client_id": body.client_id}, {"_id": 0, "user_id": 0}
    )
    return saved


@api.delete("/bookmarks/{client_id}")
async def delete_bookmark(client_id: str, user: dict = Depends(current_user)):
    # Soft delete — a tombstone keeps a second device from resurrecting the row.
    await db.bookmarks.update_one(
        {"user_id": user["id"], "client_id": client_id},
        {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True}

# ---------- Ready-to-send notice drafts ----------
# The draft text itself is assembled ON THE DEVICE from a fixed template (no LLM
# call, so it is deterministic and costs nothing). This endpoint only meters the
# entitlement: the first draft is free, after that it is a Pro feature.
DRAFT_TYPES = {"cheque_bounce", "deposit_refund", "unpaid_salary"}


@api.post("/drafts/consume")
async def consume_draft(payload: dict, user: dict = Depends(current_user)):
    draft_type = (payload.get("draft_type") or "").strip()
    if draft_type not in DRAFT_TYPES:
        raise HTTPException(400, "Unknown draft type")
    used = int(user.get("drafts_used", 0))
    if not user.get("is_pro") and used >= DRAFTS_FREE:
        raise HTTPException(
            status_code=402,
            detail={
                "paywall": True,
                "reason": "drafts_exhausted",
                "drafts_used": used,
                "drafts_free_limit": DRAFTS_FREE,
                "pro_price_label": PRO_PRICE_LABEL,
                "pro_price_usd_label": PRO_PRICE_USD_LABEL,
                "message": (
                    f"Your {DRAFTS_FREE} free notice draft has been used. Upgrade to Pro for "
                    "unlimited ready-to-send legal notices."
                ),
            },
        )
    if not user.get("is_pro"):
        await db.users.update_one({"id": user["id"]}, {"$inc": {"drafts_used": 1}})
        used += 1
    await db.draft_events.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "draft_type": draft_type,
        "is_pro": bool(user.get("is_pro")),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "ok": True,
        "draft_type": draft_type,
        "drafts_used": used,
        "drafts_remaining": max(0, DRAFTS_FREE - used),
    }

# ---------- Voice ----------
def openai_client() -> AsyncOpenAI:
    base_url = os.environ.get("EMERGENT_OPENAI_BASE_URL", "https://integrations.emergentagent.com/llm/openai/v1")
    return AsyncOpenAI(api_key=EMERGENT_LLM_KEY, base_url=base_url)

@api.post("/voice/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form(None),
    user: dict = Depends(current_user),
):
    """
    Whisper cloud transcription. `language` is an optional ISO 639-1 hint
    (e.g. "hi", "ta", "en") that dramatically improves accuracy for Indian
    languages compared to Whisper's auto-detect. Falls back to auto-detect
    if not provided OR if the Emergent Whisper proxy rejects the specific
    language code (silently retries without the hint so the user never
    experiences a silent mic failure).
    """
    # Whisper supports these ISO 639-1 language codes in principle. The
    # actual Emergent proxy currently rejects some of them (bn/te/gu/ml/pa/
    # or/as/sa/sd) with a 400 unsupported_language error. We keep the full
    # set here as an OPTIMISTIC hint list and let the retry-without-hint
    # fallback below rescue any rejection — this is safer than a hardcoded
    # narrow list that would silently ignore a valid hint if Emergent adds
    # support later.
    WHISPER_HINT_SET = {
        "en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa",
        "or", "as", "ur", "sa", "sd", "ne",
    }
    await meter_llm_use(user, "voice")
    try:
        data = await audio.read()
        oc = openai_client()
        base_kwargs: dict = {
            "model": "whisper-1",
            "file": (audio.filename or "audio.m4a", data, audio.content_type or "audio/m4a"),
        }
        lang_hint = None
        if language and language.lower() in WHISPER_HINT_SET:
            lang_hint = language.lower()

        # First attempt: with the language hint if we have one.
        try:
            kwargs = {**base_kwargs, **({"language": lang_hint} if lang_hint else {})}
            result = await oc.audio.transcriptions.create(**kwargs)
            return {"text": result.text, **check_script_mismatch(result.text, language)}
        except Exception as first_err:
            # If we sent a language hint and the proxy rejected it as
            # unsupported, silently retry without the hint so the user still
            # gets a transcript. Any other error re-raises.
            err_msg = str(first_err).lower()
            if lang_hint and (
                "unsupported_language" in err_msg
                or "unsupported language" in err_msg
                or "400" in err_msg and "language" in err_msg
            ):
                logger.info(
                    "Whisper rejected language hint '%s' — retrying without hint",
                    lang_hint,
                )
                result = await oc.audio.transcriptions.create(**base_kwargs)
                return {"text": result.text, **check_script_mismatch(result.text, language)}
            raise
    except Exception as e:
        # A very short hold-and-release (or a race where the recorder captures
        # almost no audio) makes Whisper reject the clip with "audio_too_short" --
        # this is a routine, expected user action, not a server failure. Surfacing
        # OpenAI's raw JSON error text through a 500 (as the generic branch below
        # would) looks like a crash to the user; return a clean, actionable 400
        # instead so the app can show "hold longer and try again" rather than a
        # technical error blob.
        err_msg = str(e).lower()
        if "audio_too_short" in err_msg or "too short" in err_msg:
            logger.info("Whisper rejected clip as too short")
            raise HTTPException(400, "Recording was too short. Please hold the mic button and speak for at least a second.")
        logger.exception("transcribe failed")
        raise HTTPException(500, f"Transcription failed: {e}")

@api.post("/voice/tts")
async def tts(body: TTSIn, user: dict = Depends(current_user)):
    # Reject empty / whitespace-only text with a clean 400 instead of letting
    # OpenAI's own 400 bubble up as a generic 500 — the frontend caches the
    # response as an MP3 and would otherwise write the JSON error blob to
    # disk, causing createAudioPlayer to fail silently.
    if not body.text or not body.text.strip():
        raise HTTPException(400, "Text is required to synthesise speech.")

    # The client splits an answer into sentences and requests them separately, so
    # the first words start playing in ~2s instead of after the whole answer has
    # been synthesised (which measured 13s for a 990-char reply). Metering every
    # request would then charge a free user ~6 of their 30 daily questions for a
    # single answer, so an answer costs one: only the first chunk of a `group`
    # meters, the rest ride along.
    #
    # Reuses usage_daily deliberately — it is already partitioned by day like the
    # counters, so this needs no new collection and no TTL index (there is no
    # index-creation or startup hook in this service to hang one off).
    should_meter = True
    if body.group:
        _day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _res = await db.usage_daily.update_one(
            {
                "scope": "user",
                "user_id": user["id"],
                "day": _day,
                "kind": f"voice_group:{body.group[:64]}",
            },
            {"$setOnInsert": {"count": 1}},
            upsert=True,
        )
        # Inserted => first chunk of this answer => charge. Matched => already paid.
        should_meter = _res.upserted_id is not None
    if should_meter:
        await meter_llm_use(user, "voice")
    try:
        oc = openai_client()
        resp = await oc.audio.speech.create(
            model="tts-1",
            voice=body.voice,
            input=body.text[:4000],
            response_format="mp3",
        )
        audio_bytes = await resp.aread()
        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
    except Exception as e:
        logger.exception("tts failed")
        raise HTTPException(500, f"TTS failed: {e}")

# ---------- Pro / Stripe ----------
@api.post("/billing/checkout")
async def create_checkout(body: CheckoutIn, user: dict = Depends(current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(500, "Stripe not configured")
    if user.get("is_pro"):
        return {"already_pro": True}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Dhara Pro — Lawyer-style AI Consultation",
                        "description": "Deep, structured legal answers with drafts, escalation paths & action plans."
                    },
                    "unit_amount": PRO_PRICE_USD,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=body.return_url + ("&" if "?" in body.return_url else "?") + "status=success",
            cancel_url=body.return_url + ("&" if "?" in body.return_url else "?") + "status=cancel",
            client_reference_id=user["id"],
            customer_email=user["email"],
            metadata={"user_id": user["id"], "email": user["email"], "product": "dhara_pro"},
        )
        # Log intent
        await db.billing_intents.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "provider": "stripe",
            "stripe_session_id": session.id,
            "amount_usd_cents": PRO_PRICE_USD,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "created",
        })
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        logger.exception("stripe checkout failed")
        raise HTTPException(500, f"Checkout failed: {e}")

async def _mark_pro(user_id: str, session_id: Optional[str] = None, provider: str = "stripe", payment_ref: Optional[str] = None):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_pro": True, "pro_since": now, "pro_provider": provider, "pro_payment_ref": payment_ref}},
    )
    filter_q: dict
    if provider == "stripe" and session_id:
        filter_q = {"stripe_session_id": session_id}
    elif provider == "razorpay" and payment_ref:
        filter_q = {"razorpay_payment_id": payment_ref}
    else:
        filter_q = {"user_id": user_id, "status": "created"}
    await db.billing_intents.update_one(
        filter_q,
        {"$set": {"status": "paid", "paid_at": now, "provider": provider}},
    )

@api.post("/billing/verify")
async def verify_checkout(payload: dict, user: dict = Depends(current_user)):
    """Fallback verification: frontend calls this after returning from Stripe to fast-track Pro flip.
    (Webhook is the source of truth; this only confirms if session is paid.)"""
    sid = payload.get("session_id")
    if not sid or not STRIPE_API_KEY:
        raise HTTPException(400, "session_id required")
    try:
        s = stripe.checkout.Session.retrieve(sid)
        if s.payment_status == "paid" and s.client_reference_id == user["id"]:
            await _mark_pro(user["id"], session_id=sid, provider="stripe")
            return {"is_pro": True}
        return {"is_pro": bool(user.get("is_pro"))}
    except Exception as e:
        logger.exception("verify failed")
        raise HTTPException(500, str(e))

@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    # Fail closed. Without a configured signing secret ANY caller could POST a
    # fake "checkout.session.completed" and unlock Pro for any user id, so an
    # unsigned webhook is never processed.
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("stripe webhook rejected: STRIPE_WEBHOOK_SECRET is not configured")
        raise HTTPException(503, "Webhook not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        logger.warning("stripe webhook rejected: bad signature")
        raise HTTPException(400, "Invalid webhook signature")

    et = event["type"] if isinstance(event, dict) else event.get("type")
    if et == "checkout.session.completed":
        session = (event["data"]["object"] if isinstance(event, dict) else event.data.object)
        user_id = session.get("client_reference_id") if isinstance(session, dict) else session.client_reference_id
        sid = session.get("id") if isinstance(session, dict) else session.id
        if user_id:
            await _mark_pro(user_id, session_id=sid, provider="stripe")
    return {"ok": True}

# ---------- Razorpay ----------
class RazorpayVerifyIn(BaseModel):
    payment_id: str = Field(min_length=4, max_length=64)

@api.get("/billing/razorpay/config")
async def razorpay_config():
    return {
        # Only advertise the India payment path when the server can actually
        # verify a payment. Without keys we cannot prove anyone paid, so the
        # option is hidden rather than granted on trust.
        "enabled": bool(razor_client),
        "handle": RAZORPAY_ME_HANDLE,
        "link_url": RAZORPAY_ME_URL,
        "key_id_public": RAZORPAY_KEY_ID or None,
        "server_verify": bool(razor_client),
        "webhook_enabled": bool(RAZORPAY_WEBHOOK_SECRET),
        "amount_paise": PRO_PRICE_INR,
        "amount_label": PRO_PRICE_LABEL,
        "currency": "INR",
    }

@api.post("/billing/razorpay/submit-payment-id")
async def razorpay_submit_payment(body: RazorpayVerifyIn, user: dict = Depends(current_user)):
    """User pastes the Razorpay Payment ID (pay_xxx) shown after paying.

    FAIL CLOSED: Pro is granted only when Razorpay itself confirms the payment is
    captured/authorised for at least the Pro price. The old build fell back to
    trusting the pasted id whenever server keys were missing, which let anyone
    unlock Pro for free by typing "pay_" followed by anything.
    """
    if user.get("is_pro"):
        return {"is_pro": True, "already_pro": True}

    if not razor_client:
        raise HTTPException(
            503,
            "Online payment is temporarily unavailable. Please try again later.",
        )

    pid = body.payment_id.strip()
    if not pid.startswith("pay_"):
        raise HTTPException(400, "Payment ID must start with pay_")

    now = datetime.now(timezone.utc).isoformat()
    intent_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "email": user["email"],
        "provider": "razorpay",
        "razorpay_payment_id": pid,
        "amount_paise": PRO_PRICE_INR,
        "status": "submitted",
        "created_at": now,
    }

    verified = False
    verify_error: Optional[str] = None

    try:
        payment = razor_client.payment.fetch(pid)
        intent_doc["razorpay_payment"] = {
            "status": payment.get("status"),
            "amount": payment.get("amount"),
            "currency": payment.get("currency"),
            "email": payment.get("email"),
            "contact": payment.get("contact"),
            "method": payment.get("method"),
        }
        status = payment.get("status")
        amount = int(payment.get("amount") or 0)
        if status in ("captured", "authorized") and amount >= PRO_PRICE_INR:
            verified = True
        else:
            verify_error = f"Payment status={status}, amount={amount} paise (required {PRO_PRICE_INR})"
    except Exception as e:
        logger.exception("razorpay fetch failed")
        verify_error = str(e)[:200]

    # Duplicate protection: a payment_id should only unlock Pro once
    existing = await db.billing_intents.find_one({"razorpay_payment_id": pid, "status": "paid"})
    if existing and existing.get("user_id") != user["id"]:
        raise HTTPException(400, "This payment has already been used by another account.")

    if verified:
        intent_doc["status"] = "paid"
        intent_doc["paid_at"] = now
        await db.billing_intents.insert_one(intent_doc)
        await _mark_pro(user["id"], provider="razorpay", payment_ref=pid)
        return {"is_pro": True, "verified": True}
    else:
        intent_doc["status"] = "verify_failed"
        intent_doc["verify_error"] = verify_error
        await db.billing_intents.insert_one(intent_doc)
        raise HTTPException(400, "We could not confirm that payment yet. Please try again in a few minutes.")

@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """Configure this URL in Razorpay Dashboard → Settings → Webhooks.
    Event: payment.captured. Set the webhook secret and put it in RAZORPAY_WEBHOOK_SECRET."""
    payload = await request.body()
    sig = request.headers.get("x-razorpay-signature", "")

    # Fail closed — an unsigned webhook is an unauthenticated "make this user
    # Pro" endpoint, so it is rejected when no secret is configured.
    if not RAZORPAY_WEBHOOK_SECRET:
        logger.error("razorpay webhook rejected: RAZORPAY_WEBHOOK_SECRET is not configured")
        raise HTTPException(503, "Webhook not configured")
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        logger.warning("razorpay webhook rejected: bad signature")
        raise HTTPException(400, "Invalid signature")

    try:
        event = json.loads(payload)
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    et = event.get("event")
    if et in ("payment.captured", "payment.authorized"):
        payment = (event.get("payload") or {}).get("payment", {}).get("entity", {})
        pid = payment.get("id")
        email = (payment.get("email") or "").lower()
        contact = payment.get("contact") or ""
        amount = int(payment.get("amount") or 0)
        # Find user by email or phone (razorpay.me collects both)
        user = None
        if email:
            user = await db.users.find_one({"email": email})
        if not user and contact:
            # try last 10 digits of phone
            digits = "".join(ch for ch in contact if ch.isdigit())[-10:]
            if digits:
                user = await db.users.find_one({"phone": {"$regex": digits + "$"}})
        if user and amount >= PRO_PRICE_INR:
            # Record intent if missing
            existing = await db.billing_intents.find_one({"razorpay_payment_id": pid})
            if not existing:
                await db.billing_intents.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"],
                    "email": user["email"],
                    "provider": "razorpay",
                    "razorpay_payment_id": pid,
                    "amount_paise": amount,
                    "status": "paid_via_webhook",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "paid_at": datetime.now(timezone.utc).isoformat(),
                    "razorpay_payment": payment,
                })
            await _mark_pro(user["id"], provider="razorpay", payment_ref=pid)
            logger.info(f"razorpay webhook: marked user {user['email']} pro via {pid}")
    return {"ok": True}

# ---------- Reference data ----------
LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "tts": "en-IN"},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "tts": "hi-IN"},
    {"code": "bn", "name": "Bengali", "native": "বাংলা", "tts": "bn-IN"},
    {"code": "ta", "name": "Tamil", "native": "தமிழ்", "tts": "ta-IN"},
    {"code": "te", "name": "Telugu", "native": "తెలుగు", "tts": "te-IN"},
    {"code": "mr", "name": "Marathi", "native": "मराठी", "tts": "mr-IN"},
    {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "tts": "gu-IN"},
    {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ", "tts": "kn-IN"},
    {"code": "ml", "name": "Malayalam", "native": "മലയാളം", "tts": "ml-IN"},
    {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ", "tts": "pa-IN"},
    {"code": "or", "name": "Odia", "native": "ଓଡ଼ିଆ", "tts": "or-IN"},
    {"code": "as", "name": "Assamese", "native": "অসমীয়া", "tts": "as-IN"},
    {"code": "ur", "name": "Urdu", "native": "اردو", "tts": "ur-IN"},
    {"code": "sd", "name": "Sindhi", "native": "سنڌي", "tts": "sd-IN"},
    {"code": "ks", "name": "Kashmiri", "native": "कॉशुर", "tts": "ks-IN"},
    {"code": "ne", "name": "Nepali", "native": "नेपाली", "tts": "ne-NP"},
    {"code": "sa", "name": "Sanskrit", "native": "संस्कृतम्", "tts": "sa-IN"},
    {"code": "kok", "name": "Konkani", "native": "कोंकणी", "tts": "kok-IN"},
    {"code": "mai", "name": "Maithili", "native": "मैथिली", "tts": "mai-IN"},
    {"code": "mni", "name": "Manipuri", "native": "মৈতৈলোন্", "tts": "mni-IN"},
    {"code": "sat", "name": "Santali", "native": "ᱥᱟᱱᱛᱟᱲᱤ", "tts": "sat-IN"},
    {"code": "doi", "name": "Dogri", "native": "डोगरी", "tts": "doi-IN"},
    {"code": "brx", "name": "Bodo", "native": "बर'", "tts": "brx-IN"},
]

MODELS = [
    {"provider": "anthropic", "name": "claude-sonnet-4-5-20250929", "label": "Dhara AI", "recommended": True},
    {"provider": "openai", "name": "gpt-5.2", "label": "GPT-5.2"},
    {"provider": "gemini", "name": "gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro"},
]

TOPICS = [
    {"id": "police-stop", "icon": "shield", "title": "Rights During a Police Stop", "summary": "What police can and cannot do when they stop or question you.", "law": "Article 22; Section 35 BNSS; D.K. Basu vs State of WB (1997)", "points": ["Right to know officer name & badge number (D.K. Basu).", "Right to know reason for detention (Article 22(1)).", "Right to consult lawyer of choice (Article 22(1)).", "Right to inform family of arrest.", "Police cannot torture, slap or abuse — violates Article 21.", "Must be produced before magistrate in 24 hours (Article 22(2))."]},
    {"id": "arrest", "icon": "handcuffs", "title": "Rights When Arrested", "summary": "Non-negotiable rights every citizen has on arrest.", "law": "Articles 20, 21, 22; Sec 35-46 BNSS; Arnesh Kumar (2014)", "points": ["Arrest memo must be witnessed & countersigned (D.K. Basu).", "Medical examination within 48 hours by govt doctor.", "Cannot be forced to be witness against self (Art 20(3)).", "For offences <7yrs, arrest not automatic (Arnesh Kumar).", "Women arrested only between 6AM-6PM by a woman officer (Sec 43 BNSS).", "Right to bail for bailable offences (Sec 478 BNSS)."]},
    {"id": "fir", "icon": "file-text", "title": "How to File an FIR", "summary": "Step-by-step process for a First Information Report.", "law": "Sec 173 BNSS; Lalita Kumari vs State of UP (2013)", "points": ["Go to police station of jurisdiction.", "If police refuse FIR they commit an offence (Sec 199 BNS).", "FIR mandatory for cognizable offences (Lalita Kumari).", "Right to free copy of FIR (Sec 173(2) BNSS).", "If refused: SP in writing → Magistrate under Sec 175(3) BNSS.", "Zero FIR can be filed at ANY police station."]},
    {"id": "women-safety", "icon": "heart", "title": "Women's Safety Rights", "summary": "Key legal protections for women in India.", "law": "BNS Sec 63-79, 85-86; DV Act 2005; POSH Act 2013", "points": ["Woman cannot be called to police station (Sec 179 BNSS).", "Rape statement must be recorded by woman officer (Sec 176).", "Free legal aid guaranteed (Article 39A).", "One-Stop Centres (Sakhi) — call 181.", "DV includes physical, emotional, sexual, economic abuse.", "POSH: IC mandatory at every workplace with 10+ employees."]},
    {"id": "traffic", "icon": "car", "title": "Traffic Stop & Vehicle Rights", "summary": "Rules for traffic-police interactions.", "law": "Motor Vehicles Act 1988 (amended 2019); Sec 132", "points": ["Only ASI+ officers can issue challans.", "Right to see officer ID before handing over documents.", "Constable cannot seize licence — only magistrate can.", "Pay fines via mParivahan — no cash bribes are legal.", "DigiLocker documents are legally valid.", "Right to contest challan in Lok Adalat / traffic court."]},
    {"id": "rti", "icon": "info", "title": "Right to Information (RTI)", "summary": "Demand information from any public authority.", "law": "RTI Act 2005; Art 19(1)(a)", "points": ["Any citizen can file RTI — no reason required.", "Fee ₹10 (free for BPL). Reply in 30 days.", "Life & liberty issues: reply in 48 hours.", "Denied → first appeal in 30 days; second appeal to CIC/SIC.", "PIO fined ₹250/day for delays.", "Special rules for corruption / human rights / security."]},
    {"id": "consumer", "icon": "shopping-bag", "title": "Consumer Rights", "summary": "Protection against fraud, defective goods, and poor service.", "law": "Consumer Protection Act, 2019", "points": ["6 rights: safety, information, choice, be heard, redressal, education.", "File complaints at consumerhelpline.gov.in or call 1915.", "District Commission handles claims up to ₹1 crore.", "E-commerce platforms strictly liable for defective goods.", "Misleading ads: fine up to ₹10 lakh, jail up to 2 years.", "Product liability makes manufacturers liable for defects."]},
    {"id": "domestic-violence", "icon": "home", "title": "Domestic Violence Protection", "summary": "Legal shield for women facing domestic abuse.", "law": "Protection of Women from Domestic Violence Act 2005", "points": ["Covers physical, sexual, verbal, emotional, economic abuse.", "Right to reside in shared household — cannot be thrown out.", "Protection / Residence / Monetary / Custody / Compensation Orders.", "Free legal aid, medical treatment, shelter home access.", "Protection Officer in every district.", "Helplines: 181 (Women); 1091 (Police Women)."]},
]

@api.get("/reference/languages")
async def get_languages():
    return LANGUAGES

@api.get("/reference/states")
async def get_states():
    return STATES

@api.get("/reference/models")
async def get_models():
    return MODELS

# ── /api/retrieve — standalone corpus search ────────────────────────────────
# Searches the MongoDB legal_sections corpus with optional state jurisdiction
# prioritisation.  The answer pipeline (chat/stream) also calls corpus_db
# internally; this endpoint exposes it for external clients and front-end
# debug tooling.
#
# Request body:
#   query          (str, required)  — user's natural-language question
#   state_code     (str, optional)  — 2-letter code e.g. "MH"; boosts state Acts
#   limit          (int, optional)  — max results returned, default 5, max 10
#   mode           (str, optional)  — "text" (default) | "exact"
#   section_number (str, optional)  — required when mode="exact"
#   act_hint       (str, optional)  — act name substring for exact lookup
class RetrieveIn(BaseModel):
    query: str
    state_code: Optional[str] = None
    limit: int = 5
    mode: str = "text"
    section_number: Optional[str] = None
    act_hint: Optional[str] = None

@api.post("/retrieve")
async def retrieve(body: RetrieveIn, user: dict = Depends(current_user)):
    """Search the legal corpus.  Returns up to `limit` matching sections,
    ranked by full-text relevance and boosted by the user's state jurisdiction.

    Safety guards (G1 dead-law, G2 judicial join, G3 badge) are applied
    automatically inside corpus_db.retrieve_db / lookup_section.
    Falls back gracefully if the corpus collection is empty or the text index
    is still building."""
    limit = max(1, min(int(body.limit), 10))

    if body.mode == "exact" and body.section_number:
        result = await db_lookup_section(corpus_db, body.section_number, body.act_hint)
        results = [result] if result else []
    else:
        # Use the user's own state_jurisdiction if the caller didn't specify
        state_code = body.state_code or user.get("state") or None
        try:
            results = await db_retrieve(corpus_db, body.query, state_code=state_code, limit=limit)
        except Exception:
            results = []

    return {
        "query": body.query,
        "count": len(results),
        "results": results,
        "corpus_source": "mongodb",
        "state_priority": (
            STATE_CODE_TO_JURISDICTION.get((body.state_code or user.get("state") or "").upper(), None)
        ),
    }


@api.get("/reference/topics")
async def get_topics():
    return TOPICS

@api.get("/reference/topics/{topic_id}")
async def get_topic(topic_id: str):
    for t in TOPICS:
        if t["id"] == topic_id:
            return t
    raise HTTPException(404, "Topic not found")

# ---------- Legal / meta ----------
@api.get("/legal/terms")
async def get_terms():
    return {
        "version": TERMS_VERSION,
        "text": TERMS_AND_CONDITIONS,
        "disclaimer_short": DISCLAIMER_SHORT,
        "copyright": "© Callistus Moses",
        "company": "Msafe",
    }

@api.get("/billing/pricing")
async def pricing():
    return {
        "pro_price_inr_paise": PRO_PRICE_INR,
        "pro_price_label": PRO_PRICE_LABEL,
        "pro_price_usd_cents": PRO_PRICE_USD,
        "pro_price_usd_label": PRO_PRICE_USD_LABEL,
        "currency": "INR",
        "currency_intl": "USD",
        "billing_type": "one_time",
        "providers": {
            "stripe": {
                "enabled": bool(STRIPE_API_KEY),
                "currency": "USD",
                "amount_label": PRO_PRICE_USD_LABEL,
                "regions": ["Canada", "International"],
            },
            "razorpay": {
                "enabled": bool(razor_client),
                "currency": "INR",
                "amount_label": PRO_PRICE_LABEL,
                "regions": ["India"],
                "link_url": RAZORPAY_ME_URL,
                "handle": RAZORPAY_ME_HANDLE,
            },
        },
        "features": [
            "Lawyer-consultation-style deep answers",
            "Ready-to-use draft complaint / RTI / notice paragraphs",
            "Step-by-step action plans with jurisdiction & authority names",
            "Counter-arguments & pitfalls analysis",
            "Escalation paths (SP, DM, HRC, NALSA, Consumer Commission)",
            "Priority AI models",
        ],
    }

@api.get("/health")
async def health():
    return {
        "status": "ok",
        "app": "Dhara",
        "copyright": "© Callistus Moses",
        "company": "Msafe",
        "terms_version": TERMS_VERSION,
    }

# ---------- Admin CSV export ----------
# Key-protected read-only export for the app operator. The key MUST be sent in
# the X-Admin-Key header — it used to be a ?key= query parameter, which leaks the
# secret into access logs, proxy logs and browser history for an endpoint that
# dumps every user's PII and chat history.
#   curl -H "X-Admin-Key: $ADMIN_KEY" <API>/api/admin/export/users.csv
# Password hashes are NEVER exported. Rows are streamed so this handles large tables.

ADMIN_KEY = os.environ.get("ADMIN_KEY", "").strip()

def _check_admin_key(key: Optional[str]):
    if not ADMIN_KEY:
        raise HTTPException(503, "Admin export is not configured on this server.")
    if not key or not hmac.compare_digest(key, ADMIN_KEY):
        raise HTTPException(401, "Invalid admin key.")

@api.get("/admin/export/users.csv")
async def export_users_csv(x_admin_key: Optional[str] = Header(None)):
    _check_admin_key(x_admin_key)
    import csv, io
    from fastapi.responses import StreamingResponse

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "email", "name", "phone", "language", "is_pro", "pro_since",
        "pro_samples_used", "auto_speak", "terms_version", "terms_accepted_at",
        "created_at", "password_reset_at",
    ])
    async for u in db.users.find({}).sort("created_at", -1):
        writer.writerow([
            u.get("id", ""),
            u.get("email", ""),
            u.get("name", ""),
            u.get("phone", ""),
            u.get("language", ""),
            "yes" if u.get("is_pro") else "no",
            u.get("pro_since", ""),
            u.get("pro_samples_used", 0),
            "yes" if u.get("auto_speak") else "no",
            u.get("terms_version", ""),
            u.get("terms_accepted_at", ""),
            u.get("created_at", ""),
            u.get("password_reset_at", ""),
        ])
    buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(buffer.read().encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="dhara_users_{datetime.now(timezone.utc).strftime("%Y%m%d")}.csv"',
        },
    )

@api.get("/admin/export/messages.csv")
async def export_messages_csv(x_admin_key: Optional[str] = Header(None)):
    _check_admin_key(x_admin_key)
    import csv, io
    from fastapi.responses import StreamingResponse

    # Cache users for O(1) email lookups
    user_index: dict = {}
    async for u in db.users.find({}, projection={"id": 1, "email": 1, "name": 1, "phone": 1}):
        user_index[u["id"]] = u

    # Cache sessions for user linkage
    session_index: dict = {}
    async for s in db.sessions.find({}, projection={"id": 1, "user_id": 1}):
        session_index[s["id"]] = s.get("user_id", "")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "timestamp", "user_email", "user_name", "user_phone", "role",
        "status", "content", "citations", "session_id",
    ])
    async for m in db.messages.find({}).sort("created_at", -1):
        sid = m.get("session_id", "")
        uid = session_index.get(sid, "")
        u = user_index.get(uid, {})
        citations = m.get("citations") or []
        # Flatten citation labels for CSV
        cit_labels = " | ".join(
            (c.get("short_label", "") if isinstance(c, dict) else str(c)) for c in citations
        )
        # Derive status: prefer explicit field, else infer from error / content
        status = m.get("status")
        if not status:
            if m.get("error"):
                status = "error"
            elif m.get("role") == "assistant" and m.get("content", "").startswith(
                ("I don't have a verified source", "I only cover Indian law", "I can only help")
            ):
                status = "refused"
            else:
                status = "ok"
        writer.writerow([
            m.get("timestamp") or m.get("created_at", ""),
            u.get("email", ""),
            u.get("name", ""),
            u.get("phone", ""),
            m.get("role", ""),
            status,
            (m.get("content") or "").replace("\r", " ").replace("\n", " ")[:2000],
            cit_labels,
            sid,
        ])
    buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(buffer.read().encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="dhara_messages_{datetime.now(timezone.utc).strftime("%Y%m%d")}.csv"',
        },
    )

@api.get("/admin/stats")
async def admin_stats(x_admin_key: Optional[str] = Header(None)):
    """Quick JSON overview — total users, pro users, session/message counts."""
    _check_admin_key(x_admin_key)
    return {
        "users_total": await db.users.count_documents({}),
        "users_pro": await db.users.count_documents({"is_pro": True}),
        "sessions_total": await db.sessions.count_documents({}),
        "messages_total": await db.messages.count_documents({}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@api.get("/admin/refusal-stats")
async def admin_refusal_stats(
    days: int = 7,
    x_admin_key: Optional[str] = Header(None),
):
    """
    Refusal cause-code breakdown (A4 instrumentation) — aggregate-only,
    no user-identifying data is stored or returned. Answers exactly the
    four questions corpus-spend decisions depend on:
      1. no_candidate_scored — plausible true coverage gap (topic not in corpus)
      2. below_confidence_threshold — a candidate existed but scored under the
         bar; a retrieval-tuning question, NOT necessarily a missing law
      3. query_too_vague — too few content words to score anything
      4. non_indian_jurisdiction / not_legal_advice_request — out of scope,
         not a corpus gap at all
    `top_key` counts show WHICH existing entries keep almost-matching (useful
    for keyword tuning) and `category` counts show which real-world topics
    are being asked about, including topics with zero corpus coverage today.
    """
    _check_admin_key(x_admin_key)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cursor = db.refusal_events.find({"created_at": {"$gte": since}})
    events = await cursor.to_list(10000)

    total = len(events)
    by_cause: dict = {}
    by_sub_cause: dict = {}
    by_category: dict = {}
    by_language: dict = {}
    score_histogram = {"0": 0, "1-2": 0, "3-5": 0, "6-11": 0, "12+": 0, "n/a": 0}
    near_miss_top_keys: dict = {}  # top_key counts for sub_cause == below_confidence_threshold

    for e in events:
        cause = e.get("cause_code") or "unknown"
        by_cause[cause] = by_cause.get(cause, 0) + 1
        sub = e.get("sub_cause")
        if sub:
            by_sub_cause[sub] = by_sub_cause.get(sub, 0) + 1
        cat = e.get("category") or "other_uncategorized"
        by_category[cat] = by_category.get(cat, 0) + 1
        lang = e.get("language") or "unknown"
        by_language[lang] = by_language.get(lang, 0) + 1

        score = e.get("top_score")
        if score is None:
            score_histogram["n/a"] += 1
        elif score == 0:
            score_histogram["0"] += 1
        elif score <= 2:
            score_histogram["1-2"] += 1
        elif score <= 5:
            score_histogram["3-5"] += 1
        elif score <= 11:
            score_histogram["6-11"] += 1
        else:
            score_histogram["12+"] += 1

        if sub == "below_confidence_threshold" and e.get("top_key"):
            k = e["top_key"]
            near_miss_top_keys[k] = near_miss_top_keys.get(k, 0) + 1

    return {
        "window_days": days,
        "total_refusals": total,
        "by_cause_code": by_cause,
        "by_sub_cause": by_sub_cause,
        "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)),
        "by_language": by_language,
        "score_histogram": score_histogram,
        "near_miss_top_keys": dict(sorted(near_miss_top_keys.items(), key=lambda x: x[1], reverse=True)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@api.get("/")
async def root():
    return {
        "message": "Dhara API - Empowering every Indian citizen with knowledge of their rights.",
        "copyright": "© Callistus Moses",
        "company": "Msafe",
    }

# ---------- Static downloads (App summary docs) ----------
from fastapi.responses import FileResponse

DOWNLOADS_DIR = Path("/app/downloads")

@api.get("/downloads/{filename}")
async def get_download(filename: str):
    # Allow only .pdf/.docx from the downloads dir, no traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        raise HTTPException(400, "Only .pdf and .docx are downloadable")
    fp = DOWNLOADS_DIR / filename
    if not fp.exists():
        raise HTTPException(404, "File not found")
    media_type = (
        "application/pdf" if filename.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(str(fp), media_type=media_type, filename=filename)


# ─── eCourts Case Lookup (Dhara Lookup tab) ───────────────────────────────────
# Proxy all calls so ECOURTS_API_TOKEN never reaches the frontend.

CNR_RE = re.compile(r"^[A-Z]{4}\d{12}$")   # e.g. DLHC010001232024


async def _eci_get(path: str, params: dict | None = None) -> dict:
    if not ECOURTS_TOKEN:
        raise HTTPException(503, "eCourts API is not configured on this server.")
    headers = {"Authorization": f"Bearer {ECOURTS_TOKEN}", "Accept": "application/json"}
    for attempt in range(3):
        async with httpx.AsyncClient(base_url=ECOURTS_BASE, timeout=20) as client:
            r = await client.get(path, params=params, headers=headers)
        if r.status_code == 429 and attempt < 2:
            await asyncio.sleep(2 ** attempt)
            continue
        if r.status_code >= 400:
            try:
                msg = r.json().get("message") or r.json().get("error", {}).get("message", "")
            except Exception:
                msg = ""
            raise HTTPException(
                status_code=502 if r.status_code >= 500 else r.status_code,
                detail=msg or f"eCourts upstream returned {r.status_code}",
            )
        return r.json()
    raise HTTPException(429, "eCourts rate limit — please try again.")


def _nc(item: dict, cnr_hint: str | None = None) -> dict:
    d = item.get("courtCaseData", item)
    return {
        "cnr":               d.get("cnr")             or item.get("cnr")             or cnr_hint,
        "case_status":       d.get("caseStatus")      or item.get("caseStatus"),
        "next_hearing_date": d.get("nextHearingDate") or item.get("nextHearingDate"),
        "court_name":        d.get("courtName")       or item.get("courtName"),
        "district":          d.get("district")        or item.get("district"),
        "state":             d.get("state")           or item.get("state"),
        "case_type":         d.get("caseType")        or item.get("caseType"),
        "filing_date":       d.get("filingDate")      or item.get("filingDate"),
        "petitioners":       d.get("petitioners")     or item.get("petitioners") or [],
        "respondents":       d.get("respondents")     or item.get("respondents") or [],
    }


@api.get("/cases/cnr/{cnr}", summary="Look up a court case by CNR number")
async def case_by_cnr(cnr: str, user: dict = Depends(current_user)):
    cnr = cnr.strip().upper()
    if not CNR_RE.match(cnr):
        raise HTTPException(
            400,
            "CNR must be 4 capital letters followed by 12 digits "
            "(16 chars, e.g. DLHC010001232024).",
        )
    payload = await _eci_get(f"/api/partner/case/{cnr}")
    return _nc(payload.get("data", payload), cnr)


@api.get("/cases/search", summary="Search court cases by party name")
async def search_cases(name: str, page: int = 1, user: dict = Depends(current_user)):
    name = name.strip()
    if len(name) < 2:
        raise HTTPException(400, "Party name must be at least 2 characters.")
    payload = await _eci_get(
        "/api/partner/search",
        {"litigants": name, "nameMatchMode": "phrase", "page": page, "pageSize": 20},
    )
    rows = payload.get("data", {}).get("results", [])
    if isinstance(rows, dict):
        rows = rows.get("results", [])
    return {"results": [_nc(x) for x in (rows or [])], "page": page}

# ─────────────────────────────────────────────────────────────────────────────

# ── Advocate Door — Sprint 5 ─────────────────────────────────────────────────

async def _generate_intake_summary(client_name: str, situation: str, outcome: str) -> tuple[str, str]:
    """Generate a structured advocate brief from client intake transcript using LLM."""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"intake-summary-{uuid.uuid4()}",
            system_message=(
                "You are a legal case briefing assistant for an Indian advocate. "
                "Given a client intake, produce a structured brief with exactly two sections:\n"
                "SUMMARY: 2-3 concise sentences summarising the facts and what the client wants.\n"
                "DHARA ANALYSIS: identify the primary legal issue, the relevant area of law "
                "(e.g. family, property, criminal, consumer), and 2-3 recommended next actions "
                "for the advocate (office to visit, document to file, notice to send, etc.).\n"
                "Write in formal but accessible English. No markdown. No section numbers."
            ),
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        prompt = (
            f"Client name: {client_name}\n\n"
            f"Situation (client's own words):\n{situation}\n\n"
            f"Desired outcome:\n{outcome}\n\n"
            "Write the SUMMARY and DHARA ANALYSIS:"
        )
        result = await chat.send_message(UserMessage(text=prompt))
        full_text = str(result or "").strip()
        # Strip any markdown bold/italic artifacts the model may emit
        import re as _re
        full_text = _re.sub(r'\*{1,3}', '', full_text).strip()
        if "DHARA ANALYSIS" in full_text:
            parts = full_text.split("DHARA ANALYSIS", 1)
            summary = parts[0].replace("SUMMARY:", "").replace("SUMMARY", "").strip()
            analysis = parts[1].lstrip(":").lstrip("**").strip()
        else:
            summary = full_text[:400]
            analysis = full_text[400:].strip()
        return summary, analysis
    except Exception as e:
        logger.warning(f"[intake_summary] LLM call failed: {e}")
        return "", ""


@api.post("/advocate/register")
async def advocate_register(body: AdvocateRegisterIn, user: dict = Depends(current_user)):
    """Register a user as an advocate. Creates an advocate_profiles document."""
    if user["id"] != body.user_id:
        raise HTTPException(403, "user_id mismatch")
    existing = await db.advocate_profiles.find_one({"user_id": body.user_id})
    if existing:
        return {k: v for k, v in existing.items() if k != "_id"}
    # Validate bar council number
    if not body.bar_council_number or len(body.bar_council_number.strip()) < 4:
        raise HTTPException(400, "A valid Bar Council enrolment number is required (min 4 characters)")
    if not body.specializations:
        raise HTTPException(400, "Select at least one specialization")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": body.user_id,
        "bar_council_number": body.bar_council_number.strip().upper() if body.bar_council_number else "",
        "state_bar": body.state_bar,
        "specializations": body.specializations[:5],
        "verified": False,
        "created_at": now,
        "updated_at": now,
    }
    try:
        await db.advocate_profiles.insert_one(doc)
    except Exception as e:
        err_str = str(e)
        if "bar_council_number" in err_str:
            raise HTTPException(400, "This Bar Council enrolment number is already registered with another account")
        existing = await db.advocate_profiles.find_one({"user_id": body.user_id})
        if existing:
            return {k: v for k, v in existing.items() if k != "_id"}
        raise HTTPException(500, "Registration failed — please try again")
    await db.verification_log.insert_one({
        "id": str(uuid.uuid4()),
        "advocate_id": body.user_id,
        "bar_council_number": doc["bar_council_number"],
        "state_bar": body.state_bar,
        "action": "registration_submitted",
        "created_at": now,
    })
    return {k: v for k, v in doc.items() if k != "_id"}


@api.get("/advocate/profile/{user_id}")
async def advocate_profile(user_id: str, user: dict = Depends(current_user)):
    """Fetch the advocate profile for a user."""
    if user["id"] != user_id:
        raise HTTPException(403, "Forbidden")
    profile = await db.advocate_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if not profile:
        raise HTTPException(404, "Advocate profile not found")
    return profile


@api.post("/advocate/intake/create")
async def intake_create(request: Request, body: IntakeCreateIn, user: dict = Depends(current_user)):
    """Create a shareable intake link for a client. Returns intake_token and intake_url."""
    if user["id"] != body.advocate_id:
        raise HTTPException(403, "advocate_id mismatch")
    # Verify advocate is registered
    profile = await db.advocate_profiles.find_one({"user_id": body.advocate_id})
    if not profile:
        raise HTTPException(403, "Register as an advocate first")
    token = secrets.token_urlsafe(20)
    now = datetime.now(timezone.utc).isoformat()
    # Build absolute intake URL from the incoming request's origin
    origin = str(request.base_url).rstrip("/")
    intake_url = f"{origin}/intake/{token}"
    doc = {
        "id": str(uuid.uuid4()),
        "intake_token": token,
        "intake_url": intake_url,
        "advocate_id": body.advocate_id,
        "template_id": body.template_id,
        "template_title": body.template_title,
        "client_name": "",
        "status": "pending",
        "transcript": [],
        "answers": {},
        "summary": "",
        "dhara_analysis": "",
        "created_at": now,
        "completed_at": None,
    }
    await db.client_intakes.insert_one(doc)
    return {"intake_token": token, "intake_url": intake_url}


@api.get("/advocate/intake/{token}")
async def intake_get(token: str):
    """Public endpoint — fetch intake form metadata for a given token.
    Used both by the client-facing form and the advocate's intake-view screen."""
    intake = await db.client_intakes.find_one({"intake_token": token}, {"_id": 0})
    if not intake:
        raise HTTPException(404, "Intake not found")
    # For the public client form: only expose status + expiry info (no PII)
    return {
        "id": intake.get("id", ""),
        "intake_token": intake.get("intake_token", ""),
        "template_id": intake.get("template_id", "general"),
        "template_title": intake.get("template_title", "General Intake"),
        "status": intake.get("status", "pending"),
        "client_name": intake.get("client_name", ""),
        "summary": intake.get("summary", ""),
        "dhara_analysis": intake.get("dhara_analysis", ""),
        "transcript": intake.get("transcript", []),
        "answers": intake.get("answers", {}),
        "created_at": intake.get("created_at", ""),
        "completed_at": intake.get("completed_at"),
        "expired": intake.get("status") == "expired",
    }


@api.post("/advocate/intake/{token}/submit")
async def intake_submit(token: str, body: IntakeSubmitIn):
    """Public endpoint — client submits their intake data.
    Saves transcript, then generates an AI summary for the advocate."""
    intake = await db.client_intakes.find_one({"intake_token": token})
    if not intake:
        raise HTTPException(404, "Intake link not found")
    if intake.get("status") in ("complete", "expired"):
        raise HTTPException(400, "This intake link has already been used or has expired")
    now = datetime.now(timezone.utc).isoformat()
    transcript = [t.strip() for t in (body.transcript or []) if t.strip()]
    answers = body.answers or {}
    await db.client_intakes.update_one(
        {"intake_token": token},
        {"$set": {
            "client_name": body.client_name.strip()[:120],
            "transcript": transcript,
            "answers": answers,
            "status": "processing",
            "completed_at": now,
        }},
    )
    # Build context for AI brief from structured answers if available
    if answers:
        situation = "\n".join(f"{k}: {v}" for k, v in answers.items() if v)
        outcome = answers.get("relief", "")
    else:
        situation = transcript[0] if len(transcript) > 0 else ""
        outcome = transcript[1] if len(transcript) > 1 else ""
    summary, analysis = await _generate_intake_summary(body.client_name, situation, outcome)
    await db.client_intakes.update_one(
        {"intake_token": token},
        {"$set": {"summary": summary, "dhara_analysis": analysis, "status": "complete"}},
    )
    return {"ok": True, "message": "Your information has been sent to your advocate securely."}


@api.get("/advocate/intakes/{advocate_id}")
async def intakes_list(advocate_id: str, user: dict = Depends(current_user)):
    """Fetch all client intakes created by an advocate (most recent first)."""
    if user["id"] != advocate_id:
        raise HTTPException(403, "Forbidden")
    cursor = db.client_intakes.find({"advocate_id": advocate_id}, {"_id": 0}).sort("created_at", -1).limit(50)
    intakes = await cursor.to_list(length=50)
    return intakes

# ─────────────────────────────────────────────────────────────────────────────

# ── IPC → BNS Cross-Reference Engine ─────────────────────────────────────────

import json as _json_mod
from pathlib import Path as _Path

_XREF_PATH = _Path(__file__).parent / "ipc_bns_mapping.json"
_XREF_DATA: dict = {}

def _load_xref(force_reload: bool = False) -> dict:
    global _XREF_DATA
    if not _XREF_DATA or force_reload:
        if _XREF_PATH.exists():
            with open(_XREF_PATH, encoding="utf-8") as _f:
                _XREF_DATA = _json_mod.load(_f)
    return _XREF_DATA


def _xref_search(q: str = "", ipc: str = "", bns: str = "") -> list[dict]:
    """
    Search the IPC↔BNS cross-reference file.
    Matches on:
      - Exact/partial IPC section (ipc param or q starts with a digit)
      - Exact/partial BNS section (bns param)
      - Keyword search in offence + what_changed fields
    Returns a normalised list of result dicts, deduped, max 25.
    """
    data = _load_xref()
    q_lower = q.strip().lower()
    ipc_q  = (ipc or "").strip().upper()
    bns_q  = (bns or "").strip().upper()

    results: list[dict] = []

    def _matches(entry: dict) -> bool:
        # Normalise fields — guard against JSON null values
        def _s(v): return str(v).upper() if v is not None else ""
        e_ipc    = _s(entry.get("ipc_section"))
        e_bns    = _s(entry.get("bns_section"))
        e_crpc   = _s(entry.get("crpc_section"))
        e_bnss   = _s(entry.get("bnss_section"))
        e_ea     = _s(entry.get("evidence_act_section"))
        e_bsa    = _s(entry.get("bsa_section"))
        e_off    = str(entry.get("offence",  entry.get("procedure", entry.get("provision", "")))).lower()
        e_what   = str(entry.get("what_changed", "")).lower()
        e_pun    = str(entry.get("punishment_note", "")).lower()
        e_reason = str(entry.get("reason", "")).lower()
        e_note   = str(entry.get("note", "")).lower()

        if ipc_q and (ipc_q in e_ipc or ipc_q in e_crpc or ipc_q in e_ea):
            return True
        if bns_q and (bns_q in e_bns or bns_q in e_bnss or bns_q in e_bsa):
            return True
        if q_lower:
            combined = f"{e_ipc} {e_bns} {e_crpc} {e_bnss} {e_ea} {e_bsa} {e_off} {e_what} {e_pun} {e_reason} {e_note}".lower()
            return q_lower in combined
        return False

    def _normalise(entry: dict, source: str, is_dead_law_section: bool = False) -> dict:
        """Flatten heterogeneous entries into a single shape.

        A4 — classification tag is mandatory:
          • deleted_ipc_sections entries with dead_law=True → 'dead_law'
          • deleted_ipc_sections entries without dead_law   → 'deleted'
          • new_bns_offences entries                        → 'new'
          • all others must carry their own change_type from the file;
            entries missing a tag are skipped by the caller.
        """
        old_sec = (
            entry.get("ipc_section")  or
            entry.get("crpc_section") or
            entry.get("evidence_act_section") or ""
        )
        new_sec = (
            entry.get("bns_section")  or
            entry.get("bnss_section") or
            entry.get("bsa_section")  or "—"
        )

        # Determine change_type, respecting A4 mandatory-tag rule
        if is_dead_law_section:
            ct = "dead_law" if entry.get("dead_law") else "deleted"
        else:
            ct = entry.get("change_type", "")

        return {
            "source":             source,
            "old_section":        str(old_sec),
            "new_section":        str(new_sec),
            "offence":            entry.get("offence") or entry.get("procedure") or entry.get("provision") or "",
            "change_type":        ct,
            "what_changed":       entry.get("what_changed") or entry.get("note") or entry.get("reason") or entry.get("punishment_note") or "",
            "verified":           entry.get("verified", False),
            "source_link":        entry.get("source_link", ""),
            "judicial_citation":  entry.get("judicial_citation", ""),
            "dead_law":           bool(entry.get("dead_law", False)),
        }

    seen: set[str] = set()
    # (key, label, is_dead_law_section)
    sources = [
        ("ipc_complete_mapping",               "IPC → BNS",        False),
        ("bns_to_ipc_mapping",                 "IPC → BNS",        False),
        ("reverse_lookup_ipc_to_bns",          "IPC → BNS",        False),
        ("crpc_to_bnss_mapping",               "CrPC → BNSS",      False),
        ("evidence_act_to_bsa_mapping",        "Evidence Act → BSA", False),
        ("new_bns_offences_no_ipc_equivalent", "New BNS",          False),
        ("deleted_ipc_sections",               "Deleted IPC",      True),
    ]
    for key, src_label, is_dead_section in sources:
        for entry in data.get(key, []):
            if _matches(entry):
                norm = _normalise(entry, src_label, is_dead_section)
                # A4: skip entries that still have no classification tag
                if not norm.get("change_type"):
                    continue
                uid  = f"{norm['old_section']}|{norm['new_section']}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(norm)
                if len(results) >= 25:
                    break
        if len(results) >= 25:
            break

    return results


@api.get("/advocate/cross-reference")
async def cross_reference(
    q:   str = Query("", description="Keyword search"),
    ipc: str = Query("", description="IPC/CrPC/Evidence Act section number"),
    bns: str = Query("", description="BNS/BNSS/BSA section number"),
):
    """
    IPC → BNS cross-reference with Citation Guard.

    Citation Guard guarantees:
    1. ONLY the ipc_bns_mapping.json is the source of truth — no AI inference.
    2. Every result carries its verified/unverified status from the file.
    3. If a section is not in the file the response signals that explicitly;
       the caller MUST show the 'not in database' message — never infer a mapping.
    4. Results where bns_section is null are labelled 'deleted' — callers must
       NOT substitute a guessed BNS number.
    """
    if not q.strip() and not ipc.strip() and not bns.strip():
        raise HTTPException(400, "Supply at least one of: q, ipc, bns")

    data    = _load_xref()
    results = _xref_search(q=q, ipc=ipc, bns=bns)

    # ── Citation Guard metadata ───────────────────────────────────────────────
    is_section_search = bool(ipc.strip() or bns.strip())
    unverified_count  = sum(1 for r in results if not r.get("verified"))

    citation_guard = {
        # Always true — this endpoint never calls an LLM or infers missing data
        "database_only":      True,
        # False when a section-mode search returns 0 results → caller shows wall
        "query_found_in_db":  len(results) > 0,
        # True only when EVERY returned entry is marked verified in the file
        "all_entries_verified": unverified_count == 0 and len(results) > 0,
        "unverified_count":   unverified_count,
        "total_in_db":        sum(
            len(data.get(k, [])) for k in (
                "ipc_complete_mapping",
                "bns_to_ipc_mapping", "reverse_lookup_ipc_to_bns",
                "crpc_to_bnss_mapping", "evidence_act_to_bsa_mapping",
                "new_bns_offences_no_ipc_equivalent", "deleted_ipc_sections",
            )
        ),
        # Surface the audit trail for the caller
        "bare_act_audit_count": len(data.get("metadata", {}).get("bare_act_audit", [])),
        # What to show in the UI when query_found_in_db is False
        "not_in_db_message": (
            "Section mapping not yet verified in our database. "
            "Please consult a manual or the bare Act directly."
            if is_section_search and len(results) == 0 else ""
        ),
    }

    return {
        "results":            results,
        "total":              len(results),
        "citation_guard":     citation_guard,
        "which_code_applies": data.get("which_code_applies_rule", {}),
        "effective_date":     data.get("commencement_status", {}).get(
                                  "bns_bnss_bsa_effective_date", "2024-07-01"),
        "disclaimer":         data.get("metadata", {}).get("disclaimer", ""),
    }

# ─────────────────────────────────────────────────────────────────────────────

# ============================================================================
# ─── Voice FIR Drafting Assistant ────────────────────────────────────────────
# ============================================================================
from fir_engine import (
    create_session, process_turn,
    STAGE_COMPLETED, STAGE_SAFETY_GATE,
)
from fir_storage import init_storage, upload_evidence, download_evidence

class FirDraftIn(BaseModel):
    draft_id: Optional[str] = None          # None → create new
    user_id: str
    language: str = "en"
    answers: Optional[dict] = None          # {q_id: answer_text}
    status: str = "in_progress"             # in_progress | completed

class FirSessionIn(BaseModel):
    user_id: str
    language: str = "en"
    session_location_start: Optional[dict] = None   # {"lat": ..., "lng": ..., "address": "..."}


class FirTurnIn(BaseModel):
    user_message: Optional[str] = None
    gps: Optional[dict] = None              # {"lat": ..., "lng": ...}  for GPS probe
    action: Optional[str] = None            # "skip" | "upload_done" | "confirm" | "not_safe"


class FirGpsLogIn(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None
    log_type: str = "start"                 # "start" | "end"


class ChatFollowupIn(BaseModel):
    message: str          # original user question
    answer: str           # AI answer (first 500 chars used)
    language: str = "en"
    language_name: str = "English"


@api.post("/fir/draft")
async def fir_upsert_draft(body: FirDraftIn):
    """Create or update a FIR draft (upsert by draft_id).
    Intentionally NOT behind current_user — the Voice FIR Drafting
    Assistant is anonymous-first (a citizen must not be blocked by a
    login wall while reporting an incident). `user_id` may be a real
    logged-in user's id, or a locally-generated anonymous id supplied
    by the frontend for guests."""
    now = datetime.now(timezone.utc).isoformat()
    if body.draft_id:
        doc = await db.fir_drafts.find_one({"id": body.draft_id, "user_id": body.user_id})
        if doc:
            await db.fir_drafts.update_one(
                {"id": body.draft_id},
                {"$set": {"answers": body.answers or {}, "status": body.status,
                          "language": body.language, "updated_at": now}}
            )
            return {"draft_id": body.draft_id, "status": body.status}
    # Create new
    draft_id = str(uuid.uuid4())
    await db.fir_drafts.insert_one({
        "id": draft_id, "user_id": body.user_id, "language": body.language,
        "answers": body.answers or {}, "status": body.status,
        "draft_text": "", "document_checklist": [], "classification": {},
        "police_station": {}, "safety_flags": [], "created_at": now, "updated_at": now,
    })
    return {"draft_id": draft_id, "status": body.status}


@api.get("/fir/drafts/{user_id}")
async def fir_list_drafts(user_id: str, user: dict = Depends(current_user)):
    docs = await db.fir_drafts.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("updated_at", -1).to_list(50)
    return docs


@api.get("/fir/draft/{draft_id}")
async def fir_get_draft(draft_id: str, user: dict = Depends(current_user)):
    doc = await db.fir_drafts.find_one({"id": draft_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Draft not found")
    return doc


@api.post("/fir/classify")
async def fir_classify_gone():
    raise HTTPException(410, "Removed. Use POST /api/fir/session")


@api.post("/fir/generate")
async def fir_generate_gone():
    raise HTTPException(410, "Removed. Use POST /api/fir/session/{id}/turn")


@api.post("/fir/event")
async def fir_event_gone():
    raise HTTPException(410, "Removed.")


@api.post("/chat/followup")
async def chat_followup(body: ChatFollowupIn, user: dict = Depends(current_user)):
    """
    Generate 2-3 short follow-up question chips after an AI chat answer.
    These appear as tappable chips below the answer to guide the next question.
    Returns { questions: ["q1", "q2", "q3"] } or { questions: [] }.
    """
    if not body.answer or len(body.answer.strip()) < 20:
        return {"questions": []}

    lang_instruction = f"in {body.language_name}" if body.language_name.lower() != "english" else "in English"

    prompt = f"""A citizen asked a legal question.

Question: "{body.message[:200]}"
Answer summary: "{body.answer[:400]}"

Generate exactly 2-3 SHORT natural follow-up questions the citizen might ask next, {lang_instruction}.

Rules:
- Each question must be under 9 words
- Must be directly relevant to the topic
- Phrased as a brief question (not statements)
- No duplicates of the original question

Reply ONLY with a valid JSON array of strings, nothing else:
["question 1", "question 2", "question 3"]"""

    try:
        import json as _json
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"chat-followup-{id(body)}",
            system_message="Generate short follow-up questions as a JSON array only."
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        result = await chat.send_message(UserMessage(text=prompt))
        raw = (result or "[]").strip()

        # Find JSON array in response
        start = raw.find('[')
        end = raw.rfind(']') + 1
        if start >= 0 and end > start:
            questions = _json.loads(raw[start:end])
            if isinstance(questions, list):
                valid = [str(q).strip() for q in questions if isinstance(q, str) and q.strip()][:3]
                return {"questions": valid}
    except Exception as e:
        logger.error(f"[chat_followup] Error: {e}")

    return {"questions": []}


@api.post("/fir/followup")
async def fir_followup_gone():
    raise HTTPException(410, "Removed. Use POST /api/fir/session/{id}/turn")


# ─── NEW: FIR Session Interview Engine ─────────────────────────────────────────


@api.post("/fir/session")
async def fir_create_session(body: FirSessionIn):
    """Create a fresh, blank FIR session (Safety Gate stage)."""
    return await create_session(
        db,
        user_id=body.user_id,
        language=body.language,
        session_location_start=body.session_location_start,
    )


@api.post("/fir/session/{session_id}/turn")
async def fir_session_turn(session_id: str, body: FirTurnIn):
    """Process one conversation turn in the FIR interview engine."""
    return await process_turn(
        db=db,
        corpus_db=corpus_db,
        session_id=session_id,
        user_message=body.user_message,
        gps=body.gps,
        action=body.action,
        llm_key=EMERGENT_LLM_KEY,
    )


@api.post("/fir/session/{session_id}/gps")
async def fir_log_gps(session_id: str, body: FirGpsLogIn):
    """Silently log GPS at session start or end."""
    gps_data = {"lat": body.lat, "lng": body.lng, "address": body.address or "",
                "timestamp": datetime.now(timezone.utc).isoformat()}
    field = "session_location_start" if body.log_type == "start" else "session_location_end"
    await db.fir_sessions.update_one(
        {"session_id": session_id},
        {"$set": {field: gps_data, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True}


@api.post("/fir/session/{session_id}/evidence")
async def fir_upload_evidence(session_id: str, file: UploadFile = File(...)):
    """Upload one evidence file (max 20 MB). Stored via Emergent Object Storage."""
    MAX_SIZE = 20 * 1024 * 1024
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "File too large — maximum 20 MB per file")

    session = await db.fir_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(404, "Session not found")
    if len(session.get("evidence_files", [])) >= 10:
        raise HTTPException(400, "Maximum 10 files per session")

    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "evidence"

    meta = await upload_evidence(
        user_id=session.get("user_id", "anon"),
        session_id=session_id,
        filename=filename,
        data=data,
        content_type=content_type,
    )
    await db.fir_sessions.update_one(
        {"session_id": session_id},
        {"$push": {"evidence_files": meta},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "file": meta}


@api.get("/fir/session/{session_id}/evidence/{file_id}")
async def fir_download_evidence(session_id: str, file_id: str):
    """Download an evidence file by file_id."""
    from fastapi.responses import Response
    session = await db.fir_sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(404, "Session not found")
    ev = next((e for e in session.get("evidence_files", []) if e.get("file_id") == file_id), None)
    if not ev:
        raise HTTPException(404, "File not found")
    data, content_type = await download_evidence(ev["storage_path"])
    return Response(content=data, media_type=content_type)


@api.get("/fir/sessions/{user_id}")
async def fir_list_sessions(user_id: str):
    """List all FIR sessions for a user (for pause/resume)."""
    docs = await db.fir_sessions.find(
        {"user_id": user_id}, {"_id": 0, "narrative_turns": 0}
    ).sort("updated_at", -1).to_list(20)
    return docs


@api.get("/fir/session/{session_id}")
async def fir_get_session(session_id: str):
    """Get a FIR session by session_id."""
    doc = await db.fir_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Session not found")
    return doc


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def _startup():
    # Advocate Door — ensure indexes exist (idempotent)
    try:
        await db.advocate_profiles.create_index("user_id", unique=True)
        await db.advocate_profiles.create_index(
            "bar_council_number", unique=True,
            partialFilterExpression={"bar_council_number": {"$gt": ""}},
        )
        await db.client_intakes.create_index("intake_token", unique=True)
        await db.client_intakes.create_index("advocate_id")
        await db.verification_log.create_index("advocate_id")
    except Exception as e:
        logger.warning(f"[startup] advocate index creation warning: {e}")

    # Fire-and-forget: initialise Emergent Object Storage for evidence uploads
    asyncio.create_task(init_storage())

    # Fire-and-forget background task, NOT awaited: the corpus migration
    # (see corpus_migration.py) starts automatically the instant this
    # process boots, but must never delay the app from serving requests or
    # answering the platform's health check while it inserts tens of
    # thousands of documents on a cold/empty database. Every step logs
    # through the "[CORPUS_MIGRATION]" prefix regardless of how long it
    # takes; subsequent boots against an already-seeded database return
    # almost instantly (see run_corpus_migration's per-collection count
    # check) so this is never a startup cost after the first successful run.
    asyncio.create_task(run_corpus_migration(corpus_db, CORPUS_DB_NAME))

    # Fire-and-forget: the daily push-notification loop (re-engagement nudge
    # + dead-law bookmark sweep — see push_jobs.py). Sleeps until the next
    # scheduled run internally; costs nothing at boot.
    asyncio.create_task(run_push_jobs_loop(db, corpus_db))


@app.on_event("shutdown")
async def _shutdown():
    client.close()


# ============================================================================
# Serve the Expo web build from this same service.
#
# The EAS deploy template's nginx proxies EVERY path to this FastAPI app
# (location / -> 127.0.0.1:8001) and builds no web bundle of its own, so
# without this the deployment answers "/" with API JSON and there is no
# website for a custom domain to point at. Every API route lives under the
# /api prefix and /health is registered near the top of this file, so both
# are matched before the catch-all below ever runs.
#
# Regenerate the bundle from frontend/ with:
#   npx expo export --platform web --output-dir ../backend/webdist

# ─── Static web bundle (must stay the LAST route in the file) ────────────────
# ============================================================================
from fastapi.staticfiles import StaticFiles as _StaticFiles
from fastapi.responses import FileResponse as _FileResponse
from pathlib import Path as _WebPath

_WEB_DIR = _WebPath(__file__).parent / "webdist"

if _WEB_DIR.is_dir():
    _expo_assets = _WEB_DIR / "_expo"
    if _expo_assets.is_dir():
        app.mount("/_expo", _StaticFiles(directory=str(_expo_assets)), name="expo_assets")

    @app.get("/{web_path:path}", include_in_schema=False)
    async def _serve_expo_web(web_path: str):
        root = _WEB_DIR.resolve()
        candidate = (_WEB_DIR / web_path).resolve()
        if web_path and str(candidate).startswith(str(root)) and candidate.is_file():
            return _FileResponse(candidate)
        return _FileResponse(root / "index.html")
