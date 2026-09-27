"""Central configuration — loaded once, imported everywhere.

All env-var reads live here. Feature modules import what they need.
Model identifiers are environment-driven; no hard-coded model strings
outside this file.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── Database ───────────────────────────────────────────────────────────────────
MONGO_URL         = os.environ["MONGO_URL"]
DB_NAME           = os.environ["DB_NAME"]
CORPUS_DB_NAME    = os.environ.get("CORPUS_DB_NAME", "bns-know-your-rights-gandhikar_db")

# ── LLM ───────────────────────────────────────────────────────────────────────
EMERGENT_LLM_KEY  = os.environ["EMERGENT_LLM_KEY"]

# Server-side model config — clients never choose these
SERVER_CHAT_PROVIDER      = os.getenv("CHAT_PROVIDER",         "anthropic")
SERVER_CHAT_MODEL         = os.getenv("CHAT_MODEL",            "claude-sonnet-4-5-20250929")
SERVER_CHAT_FALLBACK_MODEL = os.getenv("CHAT_FALLBACK_MODEL",  "claude-haiku-4-5")

# ── Auth / JWT ─────────────────────────────────────────────────────────────────
JWT_SECRET   = os.environ["JWT_SECRET"]
JWT_ALG      = "HS256"
JWT_EXP_DAYS = 30

# ── Billing ────────────────────────────────────────────────────────────────────
STRIPE_API_KEY           = os.environ.get("STRIPE_API_KEY",           "")
STRIPE_WEBHOOK_SECRET    = os.environ.get("STRIPE_WEBHOOK_SECRET",    "")
RAZORPAY_KEY_ID          = os.environ.get("RAZORPAY_KEY_ID",          "")
RAZORPAY_KEY_SECRET      = os.environ.get("RAZORPAY_KEY_SECRET",      "")
RAZORPAY_WEBHOOK_SECRET  = os.environ.get("RAZORPAY_WEBHOOK_SECRET",  "")
RAZORPAY_ME_HANDLE       = os.environ.get("RAZORPAY_ME_HANDLE",       "calviltech")
RAZORPAY_ME_URL          = os.environ.get("RAZORPAY_ME_URL",          "https://razorpay.me/@calviltech")

PRO_PRICE_INR       = int(os.environ.get("PRO_PRICE_INR",   "9900"))
PRO_PRICE_LABEL     = os.environ.get("PRO_PRICE_LABEL",     "₹99")
PRO_PRICE_USD       = int(os.environ.get("PRO_PRICE_USD",   "500"))
PRO_PRICE_USD_LABEL = os.environ.get("PRO_PRICE_USD_LABEL", "$5")
PRO_FREE_SAMPLES    = int(os.environ.get("PRO_FREE_SAMPLES","5"))
DRAFTS_FREE         = int(os.environ.get("DRAFTS_FREE",     "1"))

# ── Rate limits ────────────────────────────────────────────────────────────────
FREE_DAILY_QUERIES  = int(os.environ.get("FREE_DAILY_QUERIES",  "30"))
APP_DAILY_LLM_CALLS = int(os.environ.get("APP_DAILY_LLM_CALLS", "3000"))

# ── External APIs ──────────────────────────────────────────────────────────────
ECOURTS_TOKEN = os.getenv("ECOURTS_API_TOKEN", "")
ECOURTS_BASE  = os.getenv("ECOURTS_API_BASE",  "https://webapi.ecourtsindia.com")

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
