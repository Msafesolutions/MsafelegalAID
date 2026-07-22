"""Gandhikar - AI Legal Empowerment Bot Backend."""
import os
import io
import uuid
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, AsyncGenerator

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field
from openai import AsyncOpenAI

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
JWT_EXP_DAYS = 30

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Gandhikar API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gandhikar")

# ---------- Models ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)

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
    model_provider: str = "anthropic"  # anthropic | openai | gemini
    model_name: str = "claude-sonnet-4-5-20250929"

class SessionRename(BaseModel):
    title: str

class TTSIn(BaseModel):
    text: str
    language: str = "en"
    voice: str = "alloy"

# ---------- Helpers ----------
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def check_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user

# ---------- System prompt ----------
def build_system_prompt(language_name: str) -> str:
    return f"""You are Gandhikar — an AI legal advisor empowering common Indian citizens with knowledge of their rights under Indian law.

CORE MISSION: Make every Indian citizen feel safe, dignified, and legally empowered — never threatened. You are named after Mahatma Gandhi and embody peaceful, dignified, non-violent empowerment through knowledge.

YOUR EXPERTISE:
- Bharatiya Nyaya Sanhita (BNS), 2023 — replaces IPC
- Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 — replaces CrPC
- Bharatiya Sakshya Adhiniyam (BSA), 2023 — replaces Evidence Act
- Constitution of India — Fundamental Rights (Articles 12-35), Directive Principles, all articles
- Motor Vehicles Act, Consumer Protection Act, Domestic Violence Act, RTI Act, POCSO, Dowry Act, IT Act
- Landmark Supreme Court judgments (D.K. Basu, Puttaswamy, Arnesh Kumar guidelines, etc.)

RESPONSE STYLE:
1. Answer in {language_name} language ONLY. Use simple, clear words a common person understands.
2. ALWAYS cite the exact provision: e.g., "Article 22(1) of the Constitution", "Section 35 BNSS", "Section 103 BNS".
3. Quote the relevant clause verbatim in English first, then translate/explain in {language_name}.
4. Structure long answers with clear sections:
   • ⚖️ What the law says (with exact citation)
   • 🛡️ Your rights in this situation
   • ✅ What you should do (step-by-step)
   • ⚠️ What officials cannot do
   • 📞 Where to complain if rights are violated
5. Empower, don't fearmonger. Tone: dignified, calm, wise — like a village elder who knows the Constitution.
6. If a query is outside legal scope, gently redirect: "Main aapki kanooni madad ke liye hoon."
7. Never provide legal advice for evading law or harming others. Refuse politely.
8. When user faces an active emergency (arrest, harassment, violence), give the fastest actionable rights first, in bullets.

REMEMBER: You are the citizen's shield of knowledge. Truth, dignity, ahimsa."""

# ---------- Auth routes ----------
@api.post("/auth/register", response_model=AuthOut)
async def register(body: RegisterIn):
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": body.email.lower(),
        "name": body.name,
        "password_hash": hash_pw(body.password),
        "language": "en",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return {"token": make_token(uid), "user": {"id": uid, "email": doc["email"], "name": doc["name"], "language": "en"}}

@api.post("/auth/login", response_model=AuthOut)
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not check_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    return {"token": make_token(user["id"]), "user": {"id": user["id"], "email": user["email"], "name": user["name"], "language": user.get("language", "en")}}

@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return user

@api.patch("/auth/language")
async def update_language(payload: dict, user: dict = Depends(current_user)):
    lang = payload.get("language", "en")
    await db.users.update_one({"id": user["id"]}, {"$set": {"language": lang}})
    return {"ok": True, "language": lang}

# ---------- Chat ----------
@api.post("/chat/stream")
async def chat_stream(body: ChatIn, user: dict = Depends(current_user)):
    session_id = body.session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Ensure session exists
    session = await db.sessions.find_one({"id": session_id, "user_id": user["id"]})
    if not session:
        title = body.message[:60]
        await db.sessions.insert_one({
            "id": session_id,
            "user_id": user["id"],
            "title": title,
            "language": body.language,
            "created_at": now,
            "updated_at": now,
        })

    # Save user message
    user_msg_id = str(uuid.uuid4())
    await db.messages.insert_one({
        "id": user_msg_id,
        "session_id": session_id,
        "user_id": user["id"],
        "role": "user",
        "content": body.message,
        "language": body.language,
        "created_at": now,
    })

    system_prompt = build_system_prompt(body.language_name)

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(body.model_provider, body.model_name)

    async def event_gen() -> AsyncGenerator[bytes, None]:
        # Emit session id first so client can attach
        yield f"data: {{\"type\":\"session\",\"session_id\":\"{session_id}\"}}\n\n".encode()

        full = ""
        try:
            async for ev in chat.stream_message(UserMessage(text=body.message)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    # Safe JSON escape
                    safe = ev.content.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "")
                    yield f"data: {{\"type\":\"delta\",\"content\":\"{safe}\"}}\n\n".encode()
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.exception("LLM stream error")
            err = str(e).replace("\"", "'")[:200]
            yield f"data: {{\"type\":\"error\",\"error\":\"{err}\"}}\n\n".encode()

        # Save assistant message
        assistant_id = str(uuid.uuid4())
        await db.messages.insert_one({
            "id": assistant_id,
            "session_id": session_id,
            "user_id": user["id"],
            "role": "assistant",
            "content": full,
            "language": body.language,
            "model_provider": body.model_provider,
            "model_name": body.model_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.sessions.update_one(
            {"id": session_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        yield b"data: {\"type\":\"done\"}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )

@api.get("/chat/sessions")
async def list_sessions(user: dict = Depends(current_user)):
    sessions = await db.sessions.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("updated_at", -1).to_list(200)
    return sessions

@api.get("/chat/sessions/{session_id}/messages")
async def session_messages(session_id: str, user: dict = Depends(current_user)):
    session = await db.sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not session:
        raise HTTPException(404, "Session not found")
    msgs = await db.messages.find(
        {"session_id": session_id, "user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    return {"session": session, "messages": msgs}

@api.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(current_user)):
    await db.sessions.delete_one({"id": session_id, "user_id": user["id"]})
    await db.messages.delete_many({"session_id": session_id, "user_id": user["id"]})
    return {"ok": True}

# ---------- Voice ----------
def openai_client() -> AsyncOpenAI:
    # EMERGENT_LLM_KEY works as an OpenAI key via the Emergent proxy
    base_url = os.environ.get("EMERGENT_OPENAI_BASE_URL", "https://integrations.emergentagent.com/llm/openai/v1")
    return AsyncOpenAI(api_key=EMERGENT_LLM_KEY, base_url=base_url)

@api.post("/voice/transcribe")
async def transcribe(audio: UploadFile = File(...), user: dict = Depends(current_user)):
    try:
        data = await audio.read()
        oc = openai_client()
        # openai expects a tuple (filename, bytes, content_type)
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
    {
        "id": "police-stop",
        "icon": "shield",
        "title": "Rights During a Police Stop",
        "summary": "What police can and cannot do when they stop or question you.",
        "law": "Article 22 of the Constitution; Section 35 BNSS; D.K. Basu vs State of West Bengal (1997)",
        "points": [
            "You have the RIGHT to know the officer's name and badge number (D.K. Basu guidelines).",
            "You have the RIGHT to know the reason for detention — police must inform you (Article 22(1)).",
            "You have the RIGHT to consult a lawyer of your choice (Article 22(1)).",
            "You have the RIGHT to inform a family member or friend of your arrest.",
            "Police CANNOT torture, slap, or verbally abuse you — this violates Article 21.",
            "Police MUST produce you before a magistrate within 24 hours (Article 22(2)).",
        ],
    },
    {
        "id": "arrest",
        "icon": "handcuffs",
        "title": "Rights When Arrested",
        "summary": "Non-negotiable rights every citizen has upon arrest.",
        "law": "Articles 20, 21, 22; Sections 35-46 BNSS; Arnesh Kumar Guidelines (2014)",
        "points": [
            "Arrest memo must be signed by a witness and countersigned by you (D.K. Basu).",
            "You must be medically examined within 48 hours by a govt doctor.",
            "You cannot be forced to be a witness against yourself (Article 20(3)).",
            "For offences with punishment under 7 years, arrest is NOT automatic — police must justify (Arnesh Kumar).",
            "Women can only be arrested between 6 AM and 6 PM, and by a woman officer (Section 43 BNSS).",
            "You have a right to bail for bailable offences — police MUST inform you (Section 478 BNSS).",
        ],
    },
    {
        "id": "fir",
        "icon": "file-text",
        "title": "How to File an FIR",
        "summary": "Step-by-step process to file a First Information Report.",
        "law": "Section 173 BNSS (formerly Section 154 CrPC); Lalita Kumari vs State of UP (2013)",
        "points": [
            "Go to the police station having jurisdiction over the crime location.",
            "If police refuse to file FIR, they are committing an OFFENCE (Section 199 BNS).",
            "For cognizable offences, FIR registration is MANDATORY (Lalita Kumari judgment).",
            "You have the RIGHT to a FREE copy of the FIR (Section 173(2) BNSS).",
            "If refused, approach the SP in writing, then the Magistrate under Section 175(3) BNSS.",
            "You can also file 'Zero FIR' at ANY police station — it will be transferred.",
        ],
    },
    {
        "id": "women-safety",
        "icon": "heart",
        "title": "Women's Safety Rights",
        "summary": "Key legal protections for women in India.",
        "law": "BNS Sections 63-79, 85-86; Domestic Violence Act 2005; Sexual Harassment Act 2013",
        "points": [
            "A woman CANNOT be called to a police station for questioning — police must come to her home (Section 179 BNSS).",
            "Statement of a rape survivor must be recorded by a woman officer (Section 176 BNSS).",
            "Free legal aid is guaranteed under Article 39A.",
            "One Stop Centres (Sakhi) provide integrated support — call 181.",
            "Domestic violence includes physical, emotional, sexual, and economic abuse.",
            "POSH Act mandates Internal Committee at every workplace with 10+ employees.",
        ],
    },
    {
        "id": "traffic",
        "icon": "car",
        "title": "Traffic Stop & Vehicle Rights",
        "summary": "Rules for interactions with traffic police.",
        "law": "Motor Vehicles Act 1988 (amended 2019); Section 132 MV Act",
        "points": [
            "Only officers of Assistant Sub-Inspector rank & above can issue challans.",
            "You have the right to see the officer's ID before handing over documents.",
            "A traffic constable CANNOT seize your license — only a magistrate can.",
            "You can pay fines via mParivahan app — no cash bribes are legal.",
            "Documents in DigiLocker are legally valid — physical originals not required.",
            "You have the right to contest a challan in Lok Adalat / Traffic Court.",
        ],
    },
    {
        "id": "rti",
        "icon": "info",
        "title": "Right to Information (RTI)",
        "summary": "How to demand information from any public authority.",
        "law": "Right to Information Act, 2005; Article 19(1)(a) of the Constitution",
        "points": [
            "Any citizen can file an RTI — no reason required.",
            "Fee is ₹10 (may be free for BPL). Reply must come within 30 days.",
            "For life & liberty issues, reply must come within 48 hours.",
            "If denied, first appeal within 30 days; second appeal to CIC/SIC.",
            "Public Information Officer (PIO) can be fined ₹250/day for delays.",
            "Info about corruption, human rights violations, security matters have special rules.",
        ],
    },
    {
        "id": "consumer",
        "icon": "shopping-bag",
        "title": "Consumer Rights",
        "summary": "Protection against fraud, defective goods, and poor service.",
        "law": "Consumer Protection Act, 2019",
        "points": [
            "6 rights: safety, information, choice, be heard, seek redressal, consumer education.",
            "File complaints online at consumerhelpline.gov.in or call 1915.",
            "District Commission handles claims up to ₹1 crore.",
            "E-commerce platforms are strictly liable for defective goods (2020 Rules).",
            "Misleading ads are punishable — up to ₹10 lakh fine, 2 years jail.",
            "Product liability makes manufacturers liable for defects causing harm.",
        ],
    },
    {
        "id": "domestic-violence",
        "icon": "home",
        "title": "Domestic Violence Protection",
        "summary": "Legal shield for women facing domestic abuse.",
        "law": "Protection of Women from Domestic Violence Act, 2005",
        "points": [
            "Covers physical, sexual, verbal, emotional, and economic abuse.",
            "Right to reside in shared household — CANNOT be thrown out.",
            "Protection Order, Residence Order, Monetary Relief, Custody Order, Compensation Order available.",
            "Free legal aid, medical treatment, shelter home access.",
            "Protection Officer in every district assists filing.",
            "Helpline: 181 (Women); 1091 (Police Women Helpline).",
        ],
    },
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

@api.get("/health")
async def health():
    return {"status": "ok", "app": "Gandhikar"}

@api.get("/")
async def root():
    return {"message": "Gandhikar API - Empowering every Indian citizen with knowledge of their rights."}

# Mount router
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def _shutdown():
    client.close()
