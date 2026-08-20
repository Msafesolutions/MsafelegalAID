"""Dhara - AI Legal Empowerment Bot Backend."""
import os
import io
import json
import uuid
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

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Header, Request
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field
from openai import AsyncOpenAI

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from legal import TERMS_AND_CONDITIONS, TERMS_VERSION, DISCLAIMER_SHORT
from mailer import send_email, password_reset_otp_email, email_configured
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
from states import STATES, STATE_BY_CODE, is_valid_state, state_name

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_ME_HANDLE = os.environ.get("RAZORPAY_ME_HANDLE", "calviltech")
RAZORPAY_ME_URL = os.environ.get("RAZORPAY_ME_URL", "https://razorpay.me/@calviltech")
PRO_PRICE_INR = int(os.environ.get("PRO_PRICE_INR", "5000"))  # paise
PRO_PRICE_LABEL = os.environ.get("PRO_PRICE_LABEL", "₹50")
PRO_PRICE_USD = int(os.environ.get("PRO_PRICE_USD", "500"))  # cents
PRO_PRICE_USD_LABEL = os.environ.get("PRO_PRICE_USD_LABEL", "$5")
PRO_FREE_SAMPLES = int(os.environ.get("PRO_FREE_SAMPLES", "5"))
# Ready-to-send notice drafts: the first one is free, the rest are a Pro feature.
DRAFTS_FREE = int(os.environ.get("DRAFTS_FREE", "1"))

# ---------------------------------------------------------------------------
# LLM spend caps. Every chat answer, transcription and spoken reply costs money
# on the Emergent key, so usage is metered per user per day AND app-wide as a
# backstop. Refusals never reach the model, so they are not counted.
# ---------------------------------------------------------------------------
FREE_DAILY_QUESTIONS = int(os.environ.get("FREE_DAILY_QUESTIONS", "10"))
FREE_DAILY_VOICE = int(os.environ.get("FREE_DAILY_VOICE", "15"))
PRO_DAILY_QUESTIONS = int(os.environ.get("PRO_DAILY_QUESTIONS", "60"))
PRO_DAILY_VOICE = int(os.environ.get("PRO_DAILY_VOICE", "90"))
APP_DAILY_LLM_CALLS = int(os.environ.get("APP_DAILY_LLM_CALLS", "3000"))
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

app = FastAPI(title="Dhara API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gandhikar")

# ---------- Models ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)
    phone: str = Field(min_length=6, max_length=20)
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

class TTSIn(BaseModel):
    text: str
    language: str = "en"
    voice: str = "alloy"

class CheckoutIn(BaseModel):
    return_url: str

class AcceptTermsIn(BaseModel):
    terms_version: str = TERMS_VERSION

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
    return {
        "id": u["id"],
        "email": u["email"],
        "name": u["name"],
        "phone": u.get("phone", ""),
        "language": u.get("language", "en"),
        "state": u.get("state"),
        "state_name": state_name(u.get("state") or ""),
        "is_pro": u.get("is_pro", False),
        "pro_since": u.get("pro_since"),
        "pro_samples_used": int(u.get("pro_samples_used", 0)),
        "pro_samples_limit": PRO_FREE_SAMPLES,
        "pro_samples_remaining": max(0, PRO_FREE_SAMPLES - int(u.get("pro_samples_used", 0))),
        "drafts_used": int(u.get("drafts_used", 0)),
        "drafts_free_limit": DRAFTS_FREE,
        "drafts_remaining": max(0, DRAFTS_FREE - int(u.get("drafts_used", 0))),
        "is_grandfathered": u.get("is_grandfathered", True),
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
    if not user or not check_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    return {"token": make_token(user["id"]), "user": public_user(user)}

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

@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    out = public_user(user)
    # Today's LLM allowance, so the UI can show what is left instead of
    # surprising the user with a limit message.
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    is_pro = bool(user.get("is_pro"))
    q_cap = PRO_DAILY_QUESTIONS if is_pro else FREE_DAILY_QUESTIONS
    v_cap = PRO_DAILY_VOICE if is_pro else FREE_DAILY_VOICE
    q_doc = await db.usage_daily.find_one({"scope": "user", "user_id": user["id"], "day": day, "kind": "question"})
    v_doc = await db.usage_daily.find_one({"scope": "user", "user_id": user["id"], "day": day, "kind": "voice"})
    q_used = int((q_doc or {}).get("count", 0))
    v_used = int((v_doc or {}).get("count", 0))
    out["daily_questions_cap"] = q_cap
    out["daily_questions_left"] = max(0, q_cap - q_used)
    out["daily_voice_cap"] = v_cap
    out["daily_voice_left"] = max(0, v_cap - v_used)
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
    Raises HTTP 429 with a plain-language message when a cap is reached. Called
    ONLY on paths that actually hit the model, so refused questions and cached
    UI actions never eat a user's allowance.
    """
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    is_pro = bool(user.get("is_pro"))
    if kind == "question":
        cap = PRO_DAILY_QUESTIONS if is_pro else FREE_DAILY_QUESTIONS
        noun = "questions"
    else:
        cap = PRO_DAILY_VOICE if is_pro else FREE_DAILY_VOICE
        noun = "voice actions"

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

    doc = await db.usage_daily.find_one_and_update(
        {"scope": "user", "user_id": user["id"], "day": day, "kind": kind},
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
                "kind": kind,
                "used": used - 1,
                "cap": cap,
                "is_pro": is_pro,
                "message": (
                    f"You have used your {cap} {noun} for today. "
                    + ("Your allowance resets tomorrow." if is_pro else
                       "Upgrade to Pro for a much higher daily limit, or come back tomorrow.")
                ),
            },
        )

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

    if mode == "pro" and not is_pro_user:
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

    # -------- Retrieval + citation integrity (P1) --------
    # (a) Non-legal / non-Indian jurisdiction → hard refusal, no LLM call
    early_refusal: Optional[str] = None
    if is_non_indian_jurisdiction(body.message):
        early_refusal = REFUSAL_NON_INDIAN
    elif is_non_legal_advice(body.message):
        early_refusal = REFUSAL_NOT_LEGAL

    # (b) Corpus retrieval — deterministic keyword match against verified statutes
    retrieved = [] if early_refusal else corpus_retrieve(body.message, limit=3)

    # (b0) State / UT layer — rent, liquor, traffic compounding and stamp duty are
    # state subjects. If the user has told us their state we serve its verified
    # rules ALONGSIDE the central law; we never substitute another state's rule.
    user_state = (user.get("state") or "").upper()
    state_hits = [] if early_refusal else corpus_retrieve_state(body.message, user_state, limit=2)
    state_topic = None if early_refusal else state_sensitive_topic(body.message)

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
        for m in _re_id.finditer(r"\b[Aa]rticle\s+(\d+[A-Za-z]?)\b", body.message):
            query_ids.append(f"article {m.group(1).lower()}")
        # "BNS Section 999", "BNSS Section 43(5)", "Sec. 43 BNSS", "BNSS 43(5)",
        # "RTI Section 6", "CPA 34", "MV 185", "Motor Vehicles Section 185"
        for m in _re_id.finditer(
            r"\b(BNS|BNSS|BSA|IPC|CrPC|PWDVA|RTI|CPA|MV|MVA)\b[^\w]*(?:Sec(?:tion|\.)?\s*)?(\d+[A-Za-z]?(?:\(\d+\))?)\b",
            body.message, _re_id.IGNORECASE,
        ):
            query_ids.append(f"{m.group(1).lower()} {m.group(2).lower()}")
        if query_ids:
            hit_labels = { _norm_short(it["short_label"]) for it in retrieved }
            if not any(qid in hit_labels or any(qid in hl for hl in hit_labels) for qid in query_ids):
                # Query names an identifier we don't cover → void retrieval so user sees refusal only
                retrieved = []

    # (c) If no retrieval hit AND no early refusal, we still refuse (no verified source)
    if not early_refusal and not retrieved and not state_hits:
        early_refusal = REFUSAL_NO_CORPUS

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
        else:
            cause_code = "no_corpus_match"
            dbg = top_candidate_debug(body.message)
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
                "category": classify_topic(body.message),
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
        finally:
            # Citation-integrity post-processing: strip any leaked section/article/statute
            # names from the model's output. The verified citations are shown by the UI
            # from the `citation` frames — the model MUST NOT emit them itself.
            sanitized = sanitize_model_output(full) if full else full
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
            return {"text": result.text}
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
                return {"text": result.text}
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
    {"provider": "anthropic", "name": "claude-sonnet-4-5-20250929", "label": "Claude Sonnet 4.5", "recommended": True},
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
            "Priority AI models (Claude Sonnet 4.5)",
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

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def _shutdown():
    client.close()
