"""Dhara - AI Legal Empowerment Bot Backend."""
import os
import io
import json
import uuid
import hmac
import hashlib
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

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Header, Request
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field
from openai import AsyncOpenAI

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from legal import TERMS_AND_CONDITIONS, TERMS_VERSION, DISCLAIMER_SHORT

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

class AuthOut(BaseModel):
    token: str
    user: dict

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: str = "en"
    language_name: str = "English"
    model_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-5-20250929"

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
        "is_pro": u.get("is_pro", False),
        "pro_since": u.get("pro_since"),
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
def build_system_prompt(language_name: str, is_pro: bool = False) -> str:
    disclaimer_line = ("\n\nAT THE END OF EVERY RESPONSE, append this exact disclaimer line on a new paragraph, in " + language_name + ":\n\"⚠️ This is legal information, not legal advice. For serious matters consult an advocate. © Callistus Moses · Msafe.\"")

    if is_pro:
        return f"""You are Dhara Pro — a senior-lawyer-style AI legal advisor to an Indian citizen. You give the depth and structure a paying client would receive in a consultation.

RESPONSE STYLE FOR PRO:
- Reply in {language_name}. Simple, dignified, plain language.
- Structure every substantive answer using ALL these sections (only skip a section if truly not applicable):
  1. ⚖️ **The exact law** — quote the operative clause verbatim in English AND translate to {language_name}. Cite chapter and verse: "Section 103 BNS, 2023", "Article 22(1) of the Constitution", "Sec 173 BNSS", relevant Supreme Court cases (D.K. Basu 1997, Arnesh Kumar 2014, Lalita Kumari 2013, Puttaswamy 2017, etc.).
  2. 🧭 **How this applies to your situation** — analyse the facts the user gave, note gaps, list assumptions.
  3. 🛡️ **Your rights, right now**  — a bullet checklist of what officials CAN and CANNOT do.
  4. ✅ **Step-by-step action plan** — numbered, immediately executable steps. Include exact document names, offices, portals (mParivahan, DigiLocker, cybercrime.gov.in, NALSA), and forms to file.
  5. 🧾 **Draft language** — if a written complaint, RTI, notice, application, or FIR body would help, draft a ready-to-use paragraph the user can copy verbatim.
  6. ⚠️ **Pitfalls & counter-arguments** — what the other side may claim, common police/officer tactics, and how the citizen should respond calmly.
  7. 📞 **Where to escalate** — specific authority names, numbers, and jurisdiction (SP, DM, State HRC, NHRC 14433, State Consumer Commission, District Legal Services Authority, etc.).
- If the user's question is genuinely simple ("What is Article 21?") give a full but shorter answer using the same structure.
- Be a wise, calm village elder plus a sharp litigator. Never fear-monger. Never break the law.
- If asked to help evade law, refuse gently and redirect.

LEGAL SCOPE:
- Bharatiya Nyaya Sanhita (BNS 2023), Bharatiya Nagarik Suraksha Sanhita (BNSS 2023), Bharatiya Sakshya Adhiniyam (BSA 2023).
- Constitution of India — Fundamental Rights, Directive Principles, all articles.
- Landmark judgments and current statutes.
- Motor Vehicles Act, Consumer Protection Act 2019, Domestic Violence Act 2005, RTI 2005, POCSO, Dowry Act, IT Act 2000, Bharatiya Sakshya.

TONE: सत्य • अहिंसा • अधिकार. Empower, never threaten.{disclaimer_line}"""

    return f"""You are Dhara — a free AI legal information tool for Indian citizens.

CORE MISSION: Make every Indian citizen aware of their rights. Empower — never threaten. "Dhara" (धारा) means a section of law in Hindi.

EXPERTISE: BNS 2023, BNSS 2023, BSA 2023, Constitution of India, Motor Vehicles Act, Consumer Protection Act, RTI, Domestic Violence Act, IT Act, and landmark judgments.

RESPONSE STYLE:
1. Answer in {language_name}. Simple, clear words a common person understands.
2. ALWAYS cite the exact provision — e.g., "Article 22(1) of the Constitution", "Section 35 BNSS", "Section 103 BNS".
3. Quote the relevant clause verbatim in English first, then translate/explain in {language_name}.
4. Structure longer answers with clear sections: ⚖️ What the law says · 🛡️ Your rights · ✅ What to do · ⚠️ What officials cannot do · 📞 Where to complain.
5. Empower, don't fearmonger. Dignified, calm, wise.
6. Refuse politely if asked to help evade law.
7. In emergencies (arrest, harassment, violence): give the fastest actionable rights first, in short bullets.

REMEMBER: You are a shield of knowledge. Truth, dignity, ahimsa.{disclaimer_line}"""

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

@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return public_user(user)

@api.patch("/auth/language")
async def update_language(payload: dict, user: dict = Depends(current_user)):
    lang = payload.get("language", "en")
    await db.users.update_one({"id": user["id"]}, {"$set": {"language": lang}})
    return {"ok": True, "language": lang}

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

# ---------- Chat ----------
@api.post("/chat/stream")
async def chat_stream(body: ChatIn, user: dict = Depends(current_user)):
    session_id = body.session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    session = await db.sessions.find_one({"id": session_id, "user_id": user["id"]})
    if not session:
        title = body.message[:60]
        await db.sessions.insert_one({
            "id": session_id,
            "user_id": user["id"],
            "title": title,
            "language": body.language,
            "tier": "pro" if user.get("is_pro") else "free",
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
        "created_at": now,
    })

    system_prompt = build_system_prompt(body.language_name, is_pro=bool(user.get("is_pro")))

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(body.model_provider, body.model_name)

    def sse(obj: dict) -> bytes:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")

    async def save_assistant(content: str, error: Optional[str] = None):
        doc = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user["id"],
            "role": "assistant",
            "content": content,
            "language": body.language,
            "model_provider": body.model_provider,
            "model_name": body.model_name,
            "tier": "pro" if user.get("is_pro") else "free",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if error:
            doc["error"] = error
        await db.messages.insert_one(doc)
        await db.sessions.update_one(
            {"id": session_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
        )

    async def event_gen() -> AsyncGenerator[bytes, None]:
        yield sse({"type": "session", "session_id": session_id, "tier": "pro" if user.get("is_pro") else "free"})
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
            await save_assistant(full, errored)
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

# ---------- Voice ----------
def openai_client() -> AsyncOpenAI:
    base_url = os.environ.get("EMERGENT_OPENAI_BASE_URL", "https://integrations.emergentagent.com/llm/openai/v1")
    return AsyncOpenAI(api_key=EMERGENT_LLM_KEY, base_url=base_url)

@api.post("/voice/transcribe")
async def transcribe(audio: UploadFile = File(...), user: dict = Depends(current_user)):
    try:
        data = await audio.read()
        oc = openai_client()
        result = await oc.audio.transcriptions.create(
            model="whisper-1",
            file=(audio.filename or "audio.m4a", data, audio.content_type or "audio/m4a"),
        )
        return {"text": result.text}
    except Exception as e:
        logger.exception("transcribe failed")
        raise HTTPException(500, f"Transcription failed: {e}")

@api.post("/voice/tts")
async def tts(body: TTSIn, user: dict = Depends(current_user)):
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
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload)  # dev fallback
    except Exception as e:
        raise HTTPException(400, f"Invalid webhook: {e}")

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
        "enabled": True,
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
    """User pastes the Razorpay Payment ID (pay_xxx) received from Razorpay after paying
    on the razorpay.me hosted page. If server credentials are configured we verify
    the payment status & amount via Razorpay API; otherwise we log & optimistically
    grant Pro (trust-based fallback for the razorpay.me link flow)."""
    if user.get("is_pro"):
        return {"is_pro": True, "already_pro": True}

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

    if razor_client:
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

    if verified or not razor_client:
        # Grant Pro (verified OR trust-based fallback when no server keys)
        intent_doc["status"] = "paid" if verified else "trust_paid"
        intent_doc["paid_at"] = now
        if verify_error:
            intent_doc["verify_error"] = verify_error
        await db.billing_intents.insert_one(intent_doc)
        await _mark_pro(user["id"], provider="razorpay", payment_ref=pid)
        return {"is_pro": True, "verified": verified, "trust_based": (not razor_client)}
    else:
        intent_doc["status"] = "verify_failed"
        intent_doc["verify_error"] = verify_error
        await db.billing_intents.insert_one(intent_doc)
        raise HTTPException(400, f"Could not verify payment: {verify_error}")

@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """Configure this URL in Razorpay Dashboard → Settings → Webhooks.
    Event: payment.captured. Set the webhook secret and put it in RAZORPAY_WEBHOOK_SECRET."""
    payload = await request.body()
    sig = request.headers.get("x-razorpay-signature", "")

    if RAZORPAY_WEBHOOK_SECRET:
        expected = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
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
                "enabled": True,
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

@api.get("/")
async def root():
    return {
        "message": "Dhara API - Empowering every Indian citizen with knowledge of their rights.",
        "copyright": "© Callistus Moses",
        "company": "Msafe",
    }

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
