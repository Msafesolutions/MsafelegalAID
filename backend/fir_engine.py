"""
DHARA FIR Interview Engine — v3.2 (GPS + Evidence + Quality Fixes)
Conversational, stage-based FIR drafting assistant.
Fresh session isolation: every session is 100% blank — no carryover.

v3.1 fixes (2026-09):
  1. Date contradiction detection: "today" vs explicit extracted date.
  2. Place validation: off-topic answers go to parked_questions, re-ask place.
  3. parked_questions: new field, populated on off-topic probe answers.
  4. Accused slot guard: witness-about-accused answers rerouted to witnesses.
  5. Witness follow-up: vague witness answers trigger name/detail probe.
  6. Phone validation: placeholder / non-numeric phone → one retry.
  7. Section mapping fix: BNS 77/78 removed from general harassment.
  8. Incident type fallback: keyword classifier when LLM returns only ["other"].

v3.2 fixes (2026-09):
  5b. Vague witness detection: now catches answers with no names/numbers regardless of length.
  9.  Citation Guard: dropped_sections written to DB with reason_dropped field.
      suggest_sections() now returns (confirmed, dropped) tuple.
"""
from __future__ import annotations

import uuid
import json
import re
import asyncio
from datetime import datetime, timezone, date
from typing import Optional
import httpx
import logging

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger("fir_engine")

# ─── Stage constants ───────────────────────────────────────────────────────────
STAGE_SAFETY_GATE     = "safety_gate"
STAGE_FREE_NARRATIVE  = "free_narrative"
STAGE_PROBE           = "probe"
STAGE_GPS_CONFIRM     = "gps_confirm"
STAGE_SECTION_SUGGEST = "section_suggest"
STAGE_READ_BACK       = "read_back"
STAGE_DRAFT           = "draft"
STAGE_COMPLETED       = "completed"

# ─── Input type hints (controls frontend rendering) ───────────────────────────
INPUT_TEXT        = "text"
INPUT_VOICE_TEXT  = "voice_or_text"
INPUT_QUICK_REPLY = "quick_reply"
INPUT_GPS         = "gps"
INPUT_EVIDENCE    = "evidence"
INPUT_CONFIRM     = "confirm"
INPUT_DONE        = "done"

# ─── Safety flag detection ────────────────────────────────────────────────────
_SAFETY_KW: dict[str, list[str]] = {
    "DV":     ["domestic violence", "husband beat", "dahej", "gharelu hinsa",
               "pati ne", "dowry", "marital violence", "wife beating"],
    "SEXUAL": ["rape", "sexual assault", "molest", "balaatkaar", "sexual harassment",
               "groped", "eve teas", "outrage modesty"],
    "POCSO":  ["child abuse", "minor abused", "pocso", "child rape", "childline"],
}

# Keywords indicating the user is in IMMEDIATE danger right now
_EMERGENCY_NARRATIVE_KW = [
    # Direct calls for help
    "help me now", "please help me", "please come help", "need help now",
    "need help right now", "right now please", "please come",
    # Attacker presence
    "he is here", "he's here", "she is here", "she's here",
    "they are here", "he has come", "she has come",
    # Being attacked RIGHT NOW
    "being attacked", "attacking me", "beating me now", "is beating me",
    "hurting me right now", "harming me now",
    # Lethal threat NOW
    "will kill me", "kill me now", "kill me right now", "trying to kill me",
    "going to kill me", "wants to kill me", "killing me",
    # Danger / confinement
    "in danger now", "in danger right now", "right now in danger",
    "save me", "can't escape", "trapped here", "cannot escape",
    # Following/stalking NOW
    "someone following me", "following me right now", "being followed now",
    # Distress phrases
    "please call police", "running away", "he is outside",
]


def _detect_safety_flags(text: str) -> list[str]:
    t = text.lower()
    return [f for f, kws in _SAFETY_KW.items() if any(k in t for k in kws)]


def _detect_immediate_danger(text: str) -> bool:
    """Return True if narrative suggests user is in danger RIGHT NOW."""
    t = text.lower()
    return any(kw in t for kw in _EMERGENCY_NARRATIVE_KW)


# Keywords for relative date detection
_RELATIVE_DATE_KW = {
    "today": ["today", "aaj", "this morning", "this evening", "this afternoon",
              "just now", "a few hours ago", "tonight"],
    "yesterday": ["yesterday", "kal", "last night", "last evening"],
    "last_week": ["last week", "pichle hafte", "a week ago"],
}


# ─── Helper validators ────────────────────────────────────────────────────────

# Location-type words that suggest a valid place answer
_PLACE_KW = [
    "road", "street", "nagar", "colony", "area", "sector", "phase", "block",
    "city", "town", "village", "district", "state", "tehsil", "taluk",
    "park", "market", "market", "station", "chowk", "bazaar", "marg", "lane",
    "near", "beside", "opposite", "behind", "in front", "next to",
    "at", "in the", "on the", "under", "inside", "outside", "between",
    "mall", "hospital", "school", "college", "office", "building", "flat",
    "house", "floor", "floor", "delhi", "mumbai", "bangalore", "bengaluru",
    "chennai", "hyderabad", "kolkata", "pune", "ahmedabad", "surat",
    "jaipur", "lucknow", "kanpur", "nagpur", "patna", "indore", "bhopal",
    "pin", "pincode", "zip", "highway", "nh-", "sh-", "bridge",
]

# Patterns that clearly indicate a non-place answer
_NON_PLACE_PATTERNS = [
    r"^how (do|can|will|should|would|to)",
    r"^what (is|are|was|were|should|would|can)",
    r"^why (is|are|was|did|should|would)",
    r"^(can|could|will|would|should|shall) (you|i|we|he|she|they)",
    r"^please (tell|explain|help|advise|suggest|let)",
    r"^i (want|need|don't|dont|wish|am|was|have|had)",
    r"^(not|na|none|nil|skip)",
]


def _is_valid_place_response(text: str) -> bool:
    """Return True if text looks like a place description."""
    if not text or len(text.strip()) < 3:
        return True  # accept very short answers (abbreviations etc.)
    t = text.lower().strip()
    # Reject clear non-place patterns (questions, requests, denials)
    for pat in _NON_PLACE_PATTERNS:
        if re.match(pat, t):
            return False
    # Accept if it contains any place keyword
    if any(kw in t for kw in _PLACE_KW):
        return True
    # Accept short answers (could be neighbourhood name, place abbreviation)
    if len(t.split()) <= 4:
        return True
    # Long sentence with no location keywords = likely off-topic
    return False


_WITNESS_KW = ["witness", "saw", "they were", "my friend", "present", "there"]
_VAGUE_WITNESS = ["yes", "yeah", "yep", "sure", "there were", "yes there",
                  "they were witnesses", "they are witnesses", "they were present",
                  "my friends were", "few people"]

# Common sentence-starter or generic words that are capitalised but are NOT person names
_COMMON_CAPS: set[str] = {
    "Yes", "No", "There", "They", "The", "This", "That", "Some", "My",
    "His", "Her", "Our", "We", "He", "She", "It", "But", "And", "Or",
    "Few", "Many", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "People", "Person", "Witnesses", "Witness", "Friends", "Neighbours",
    "Neighbors", "Bystanders", "Someone", "Anyone", "Everyone",
    "About", "Around", "Nearby", "Present",
}


def _is_witness_answer_in_accused_probe(text: str) -> bool:
    """Return True if an answer to 'who did this' is actually about witnesses."""
    t = text.lower().strip()
    return any(kw in t for kw in ["witness", "witnesses", "they were there",
                                   "they witnessed", "saw it", "they saw"])


def _is_vague_witness_response(text: str) -> bool:
    """Return True if witness answer is too vague (no names/numbers given).

    A witness answer is considered specific if it contains:
    - at least one digit run that looks like a phone number, OR
    - at least one capitalized word that is NOT a common English word
      (i.e., a real person name such as 'Ramesh', 'Priya', 'Suresh')
    """
    if not text:
        return True
    t = text.lower().strip()
    # Very short or just "yes / yeah / sure"
    if len(t) < 30 and any(t.startswith(v) for v in _VAGUE_WITNESS):
        return True
    # Check for any digit sequence (phone numbers)
    has_digit = any(c.isdigit() for c in text)
    if has_digit:
        return False
    # Check for a real person name: capitalised word NOT in our common-caps exclusion list
    cap_words = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    has_person_name = any(w not in _COMMON_CAPS for w in cap_words)
    if has_person_name:
        return False
    # No phone number, no person name → vague
    return True


_PLACEHOLDER_PHONE = [
    r"^0+$",          # 000, 00000, 0000000000
    r"^1+$",          # 111...
    r"^9+$",
    r"^\d{1,4}$",     # too short (1–4 digits)
    r"^(n/?a|na|none|no|not available|unknown|skip)$",
    r"put as",        # "put as 00000"
    r"xxx+",
]


def _is_valid_phone(text: str) -> bool:
    """Return True if text looks like a real contact number."""
    if not text:
        return False
    t = text.strip().lower()
    # Match placeholder patterns
    for pat in _PLACEHOLDER_PHONE:
        if re.search(pat, t):
            return False
    # Extract digits only
    digits = re.sub(r"\D", "", text)
    # Indian mobile: 10 digits, starts with 6-9
    if len(digits) == 10 and digits[0] in "6789":
        return True
    # Landline with STD (8-11 digits including STD code)
    if 8 <= len(digits) <= 11:
        return True
    return False


# ─── Date contradiction helpers ───────────────────────────────────────────────

_TODAY_KW = ["today", "aaj", "this evening", "this morning", "this afternoon",
             "just now", "a few hours", "tonight", "aaj raat", "aaj subah"]
_YESTERDAY_KW = ["yesterday", "kal", "last night", "last evening"]


def _narrative_mentions_today(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _TODAY_KW)


def _narrative_mentions_yesterday(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _YESTERDAY_KW)


def _has_date_conflict(narrative: str, extracted_date: Optional[str]) -> Optional[str]:
    """
    Returns the conflict message if there's a date contradiction, else None.
    Checks:
    - Narrative says "today" but extracted date != today
    - Narrative says "yesterday" but extracted date != yesterday
    - Extracted year differs significantly from current year
    """
    if not extracted_date:
        return None
    today = date.today()
    today_str = today.isoformat()  # YYYY-MM-DD
    today_fmt = today.strftime("%d %B %Y")

    # Try to parse the extracted date
    parsed = None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(extracted_date.strip(), fmt).date()
            break
        except ValueError:
            continue

    if parsed is None:
        return None

    # Check 1: narrative says "today" but extracted date is not today
    if _narrative_mentions_today(narrative) and parsed != today:
        # Format the extracted date nicely
        parsed_fmt = parsed.strftime("%d %B %Y")
        return (
            f"You mentioned 'today' — did this happen on **{today_fmt}** (today) "
            f"or was it **{parsed_fmt}** as mentioned?"
        )

    # Check 2: narrative says "yesterday" but extracted date is not yesterday
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    if _narrative_mentions_yesterday(narrative) and parsed != yesterday:
        parsed_fmt = parsed.strftime("%d %B %Y")
        yesterday_fmt = yesterday.strftime("%d %B %Y")
        return (
            f"You mentioned 'yesterday' — did this happen on **{yesterday_fmt}** "
            f"or was it **{parsed_fmt}** as mentioned?"
        )

    # Check 3: extracted year is more than 1 year before today (likely LLM default)
    if abs(parsed.year - today.year) > 1:
        parsed_fmt = parsed.strftime("%d %B %Y")
        return (
            f"I noted the date as {parsed_fmt} — could you confirm the year? "
            f"(The current year is {today.year})"
        )

    return None


# ─── Incident type keyword fallback classifier ────────────────────────────────

_INCIDENT_KW_MAP: dict[str, list[str]] = {
    "theft":     ["stolen", "steal", "stole", "theft", "chori", "pickpocket",
                  "missing phone", "missing wallet", "missing purse",
                  "grabbed my", "grabbed the", "snatched my", "took my phone",
                  "took my wallet", "took my bag", "took my laptop", "took my car",
                  "my phone was taken", "mobile stolen", "bike stolen", "car stolen"],
    "robbery":   ["robbery", "looted", "loot", "robbed", "dakaiti",
                  "snatched at", "knife", "knifepoint", "gunpoint", "at gunpoint",
                  "at knifepoint", "threatened with", "threatened at"],
    "assault":   ["beat", "beaten", "hit me", "hit us", "punch", "kick", "slap",
                  "physical", "attacked", "attack", "assault", "maara", "pita",
                  "injury", "hospital", "fracture", "wound"],
    "harassment": ["harass", "bully", "bullied", "making fun", "mock",
                   "teas", "taunt", "verbal abuse", "insulted",
                   "humiliate", "intimidat", "menac", "mischief", "nuisance",
                   "eve teas", "ragging"],
    "cyber_fraud":["online", "fraud", "cyber", "upi", "payment", "bank",
                   "account", "otp", "phishing", "scam", "cheated online",
                   "fake website", "fake call", "whatsapp"],
    "domestic_violence": ["husband", "wife", "spouse", "domestic", "dowry",
                          "marital", "in-law", "inlaw", "gharelu"],
    "sexual_harassment": ["molest", "grope", "voyeur", "stalk", "follow me",
                          "sexual", "inappropriate touch", "eve teas"],
    "murder":    ["killed", "death", "murder", "dead", "die", "hataaya"],
}


def _keyword_classify(narrative: str) -> list[str]:
    """Fast keyword-based incident type classification as a fallback."""
    t = narrative.lower()
    found: list[str] = []
    for itype, kws in _INCIDENT_KW_MAP.items():
        if any(kw in t for kw in kws):
            found.append(itype)
    return found if found else ["other"]


# ─── Probe question definitions ───────────────────────────────────────────────
PROBE_Q: dict[str, dict] = {
    "probe_date": {
        "message": "When did this happen? (date and year if possible)",
        "slot": "incident_date", "input_type": INPUT_TEXT, "skip_label": "Skip",
    },
    "probe_date_confirm": {
        # message is set dynamically; placeholder here
        "message": "Could you confirm the date of the incident?",
        "slot": "incident_date", "input_type": INPUT_TEXT, "skip_label": "Skip — keep as extracted",
    },
    "probe_time": {
        "message": "At approximately what time did this happen?",
        "slot": "incident_time", "input_type": INPUT_TEXT, "skip_label": "Skip",
    },
    "probe_place_text": {
        "message": "Where did this happen? (area / street / city / state)",
        "slot": "incident_place_text", "input_type": INPUT_VOICE_TEXT,
    },
    "probe_place_gps": {
        "message": "Would you like to pinpoint the exact incident location using GPS?\n(Helps the police identify the exact spot — optional)",
        "slot": "incident_gps", "input_type": INPUT_GPS,
        "skip_label": "No, text description is enough",
    },
    # ── Incident-specific ─────────────────────────────────────────────────────
    "probe_theft_items": {
        "message": "What exactly was stolen? List each item with approximate value.\nE.g., \"iPhone 14 — ₹80,000, wallet with ₹3,000 cash\"",
        "slot": "theft_items", "input_type": INPUT_TEXT, "skip_label": "Skip",
    },
    "probe_injury": {
        "message": "Was anyone physically injured? Did anyone need medical attention?",
        "slot": "injury", "input_type": INPUT_QUICK_REPLY,
        "quick_replies": ["Yes — injuries occurred", "No — no injuries"],
    },
    "probe_assault_mlc": {
        "message": "Did you go to a hospital or doctor? Do you have a Medico-Legal Certificate (MLC)?",
        "slot": "assault_mlc", "input_type": INPUT_TEXT, "skip_label": "Skip",
    },
    "probe_cyber_amount": {
        "message": "How much money was lost? (₹ amount)\nWhat platform was used? (UPI / bank transfer / website / app)",
        "slot": "cyber_amount", "input_type": INPUT_TEXT, "skip_label": "Skip",
    },
    "probe_harassment_online": {
        "message": "Did this harassment happen online, in person, or both?",
        "slot": "harassment_mode", "input_type": INPUT_QUICK_REPLY,
        "quick_replies": ["Online only", "In person only", "Both online and in person"],
    },
    # ── Common optional slots ─────────────────────────────────────────────────
    "probe_accused": {
        "message": "Do you know who did this?\nName, age, appearance, or relationship — or say \"Not known\".",
        "slot": "accused", "input_type": INPUT_TEXT, "skip_label": "Not known",
    },
    "probe_witnesses": {
        "message": "Were there any witnesses?\nNames and contact numbers if available.",
        "slot": "witnesses", "input_type": INPUT_TEXT, "skip_label": "No witnesses",
    },
    "probe_witnesses_detail": {
        "message": "You mentioned witnesses were present — could you share their names or contact numbers so the police can reach them?",
        "slot": "witnesses_detail", "input_type": INPUT_TEXT,
        "skip_label": "Not available right now",
    },
    "probe_evidence": {
        "message": "Do you have evidence to attach?\n(Photos, videos, screenshots, medical reports, receipts — up to 10 files)",
        "slot": None, "input_type": INPUT_EVIDENCE,
        "skip_label": "No evidence to upload",
    },
    # ── Informant details (always required for the final draft) ───────────────
    "probe_informant_name": {
        "message": "Almost done! I need your personal details for the FIR.\n\nYour full name (as it will appear on the complaint):",
        "slot": "informant_name", "input_type": INPUT_TEXT,
    },
    "probe_informant_address": {
        "message": "Your full address (house/flat number, street, area, city, PIN code):",
        "slot": "informant_address", "input_type": INPUT_TEXT,
    },
    "probe_informant_phone": {
        "message": "Your mobile number (the police can reach you on this):",
        "slot": "informant_phone", "input_type": INPUT_TEXT,
    },
    "probe_informant_phone_retry": {
        "message": "That doesn't look like a valid mobile number — the police will need to reach you.\nPlease enter a 10-digit Indian mobile number:",
        "slot": "informant_phone", "input_type": INPUT_TEXT, "skip_label": "Skip — I'll share it at the station",
    },
    # ── New incident-specific probes ──────────────────────────────────────────
    "probe_force_used": {
        "message": "Was any force, threat, or weapon used?\n(e.g., pushed, threatened, shown a weapon, snatched by force)",
        "slot": "force_used", "input_type": INPUT_QUICK_REPLY,
        "quick_replies": ["Yes, force was used", "No, no force"],
    },
    "probe_stolen_phone_imei": {
        "message": "Was a phone stolen? If yes, do you know the IMEI number?\n(Dial *#06# or check Settings → About. Helps police trace and block the device)",
        "slot": "stolen_phone_imei", "input_type": INPUT_TEXT,
        "skip_label": "No phone stolen / Don't know IMEI",
    },
    "probe_sim_blocked": {
        "message": "If a SIM card was stolen with the phone, have you blocked it yet?\n(Call your telecom operator's helpline to block: Airtel 121 / Jio 198 / BSNL 1500)",
        "slot": "sim_blocked", "input_type": INPUT_QUICK_REPLY,
        "quick_replies": ["Yes, SIM blocked", "Not yet — I'll do it now", "No SIM was stolen"],
    },
    "probe_incident_place_detail": {
        "message": "Any additional location details?\n(e.g., bus number/route, train compartment, exact seat, vehicle registration)",
        "slot": "incident_place_detail", "input_type": INPUT_TEXT,
        "skip_label": "No additional details",
    },
    "probe_transaction_ids": {
        "message": "Please share the transaction ID(s) or UTR/reference number(s) from your bank or UPI app.\n(Check your SMS, email, or app history — helps police trace the fraud)",
        "slot": "transaction_ids", "input_type": INPUT_TEXT,
        "skip_label": "Don't have them right now",
    },
    "probe_scammer_contact": {
        "message": "Do you have any contact details of the scammer?\n(Phone number, email, UPI ID, website URL, bank account number — share whatever you have)",
        "slot": "scammer_contact", "input_type": INPUT_TEXT,
        "skip_label": "Don't have any contact details",
    },
    "probe_date_confirm": {
        # message is set dynamically when this probe is served
        "message": "Could you confirm the date of the incident?",
        "slot": "incident_date", "input_type": INPUT_QUICK_REPLY,
        "quick_replies": ["Yes, that's correct", "No, let me correct the date"],
        "skip_label": "Keep as is",
    },
}

# ─── Incident type → BNS section mapping (Citation Guard source-of-truth) ─────
# FIX v3.1: BNS 77 (Voyeurism) and 78 (Stalking) removed from general "harassment".
# They are now in dedicated subtypes only.
INCIDENT_SECTIONS: dict[str, list[str]] = {
    "theft":              ["303"],
    "robbery":            ["309", "310"],
    "assault":            ["115", "117"],
    "harassment":         ["351", "352"],          # Criminal intimidation + Intentional insult
    "sexual_harassment":  ["74", "75", "77", "78", "351"],  # Sexual offences
    "stalking":           ["78"],
    "cyber_fraud":        ["318"],
    "domestic_violence":  ["85"],
    "murder":             ["101", "109"],
    "other":              [],
}
# Sections dropped when user confirmed NO injury
_INJURY_REQUIRED: set[str] = {"115", "117", "124"}
# Sections dropped when user confirmed NO property loss
_PROPERTY_REQUIRED: set[str] = {"303", "309", "310"}


def _build_probe_queue(
    slots: dict, incident_types: list[str],
    date_conflict_msg: Optional[str] = None,
    relative_date_display: Optional[str] = None,
) -> list[str]:
    """Build ordered probe queue from missing slots + incident types."""
    q: list[str] = []
    # Date: conflict, relative confirmation, or ask fresh
    if date_conflict_msg and not slots.get("incident_date"):
        q.append("probe_date")
    elif relative_date_display and slots.get("incident_date") and not slots.get("date_confirmed"):
        q.append("probe_date_confirm")
    elif not slots.get("incident_date"):
        q.append("probe_date")
    if not slots.get("incident_time"):
        q.append("probe_time")
    if not slots.get("incident_place_text"):
        q.append("probe_place_text")
    q.append("probe_place_gps")  # always offered
    # ── Incident-specific ────────────────────────────────────────────────────
    if "theft" in incident_types and not slots.get("theft_items"):
        q.append("probe_theft_items")
    if "theft" in incident_types and slots.get("force_used") is None:
        q.append("probe_force_used")
    if "theft" in incident_types and slots.get("stolen_phone_imei") is None:
        q.append("probe_stolen_phone_imei")
    if "theft" in incident_types and slots.get("sim_blocked") is None:
        q.append("probe_sim_blocked")
    if "theft" in incident_types and slots.get("incident_place_detail") is None:
        q.append("probe_incident_place_detail")
    if any(t in incident_types for t in ("assault", "robbery")):
        if slots.get("injury") is None:
            q.append("probe_injury")
        q.append("probe_assault_mlc")
    if "cyber_fraud" in incident_types and not slots.get("cyber_amount"):
        q.append("probe_cyber_amount")
    if "cyber_fraud" in incident_types and not slots.get("transaction_ids"):
        q.append("probe_transaction_ids")
    if "cyber_fraud" in incident_types and not slots.get("scammer_contact"):
        q.append("probe_scammer_contact")
    if "harassment" in incident_types and slots.get("harassment_mode") is None:
        q.append("probe_harassment_online")
    if "sexual_harassment" in incident_types and slots.get("harassment_mode") is None:
        q.append("probe_harassment_online")
    # Common optional
    if not slots.get("accused"):
        q.append("probe_accused")
    if not slots.get("witnesses"):
        q.append("probe_witnesses")
    # Evidence (always offered)
    q.append("probe_evidence")
    # Informant details (always required)
    q.extend(["probe_informant_name", "probe_informant_address", "probe_informant_phone"])
    return q


# ─── Nominatim reverse geocoding ─────────────────────────────────────────────
async def reverse_geocode(lat: float, lng: float) -> Optional[str]:
    """Convert GPS coordinates → human-readable address via OpenStreetMap Nominatim."""
    try:
        async with httpx.AsyncClient(timeout=7.0) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"format": "json", "lat": lat, "lon": lng},
                headers={"User-Agent": "DHARA-Legal-Aid/1.0 (contact@dhara.app)"},
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("display_name")
    except Exception as e:
        logger.warning(f"[reverse_geocode] failed: {e}")
    return None


# ─── LLM slot extraction ──────────────────────────────────────────────────────
def _make_extract_sys() -> str:
    today_str = date.today().strftime("%d %B %Y")
    return f"""You are a legal intake assistant for Indian FIR complaints.
Extract structured information from an incident narrative.
Return ONLY valid JSON (no markdown, no explanation) with these exact fields:
{{
  "incident_date": null,
  "incident_time": null,
  "incident_place": null,
  "accused": null,
  "witnesses": null,
  "injury": null,
  "property_loss": null,
  "words_or_threats": null,
  "incident_types": [],
  "description": ""
}}
For incident_types use ONLY these exact strings (choose all that apply):
["theft","robbery","assault","harassment","sexual_harassment","stalking","cyber_fraud","domestic_violence","murder","other"]
For injury/property_loss: "yes" / "no" / null (null = not clearly mentioned)
DATES: Today's date is {today_str}. When no year is specified in the narrative, assume the current year {date.today().year}.
If the narrative says 'today', set incident_date to today's date: {date.today().isoformat()}.
If the narrative says 'yesterday', set incident_date to {(date.today() - timedelta(days=1)).isoformat()} (yesterday).
"""  # noqa: E501


async def extract_slots_llm(narrative: str, llm_key: str) -> dict:
    """Extract slots from free narrative using Claude Haiku (cost-efficient)."""
    try:
        chat = (
            LlmChat(
                api_key=llm_key,
                session_id=f"fir-extract-{uuid.uuid4()}",
                system_message=_make_extract_sys(),
            )
            .with_model("anthropic", "claude-haiku-4-5")
            .with_params(max_tokens=600)
        )
        result = await chat.send_message(UserMessage(text=f"NARRATIVE:\n{narrative[:2000]}"))
        raw = (result or "").strip()
        # Strip possible markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```[^\n]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw.strip())
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"[extract_slots_llm] failed: {e}")
        return {
            "incident_date": None, "incident_time": None, "incident_place": None,
            "accused": None, "witnesses": None, "injury": None,
            "property_loss": None, "words_or_threats": None,
            "incident_types": [],  # empty so keyword classifier kicks in
            "description": narrative[:400],
        }


# ─── Section suggestion with Citation Guard ───────────────────────────────────
async def suggest_sections(
    corpus_db, incident_types: list[str], slots: dict
) -> tuple[list[dict], list[dict]]:
    """
    Look up BNS sections from DB based on incident types (Citation Guard).
    Apply consistency check — drop sections that contradict user input.
    Returns (confirmed_sections, dropped_sections) where each dropped entry
    has {section_number, reason_dropped}.
    """
    from corpus_db import lookup_section as db_lookup

    # Gather candidate section IDs
    candidates: set[str] = set()
    for t in incident_types:
        candidates.update(INCIDENT_SECTIONS.get(t, []))

    # ── Consistency check with reason tracking ────────────────────────────
    dropped_ids: list[dict] = []
    if str(slots.get("injury", "")).lower().startswith("no"):
        for sec_id in _INJURY_REQUIRED & candidates:
            dropped_ids.append({"section_number": sec_id, "reason_dropped": "contradicts injury=none"})
        candidates -= _INJURY_REQUIRED
    if str(slots.get("property_loss", "")).lower().startswith("no"):
        for sec_id in _PROPERTY_REQUIRED & candidates:
            dropped_ids.append({"section_number": sec_id, "reason_dropped": "contradicts property_loss=none"})
        candidates -= _PROPERTY_REQUIRED

    confirmed: list[dict] = []
    for sec_id in sorted(candidates):
        try:
            doc = await db_lookup(corpus_db, sec_id, act_hint="Bharatiya Nyaya Sanhita")
            if doc and not doc.get("is_dead_law") and not doc.get("dead_warning"):
                confirmed.append({
                    "section_number": doc.get("section_number", sec_id),
                    "section_heading": doc.get("section_heading", ""),
                    "act_name": doc.get("act_name", "Bharatiya Nyaya Sanhita, 2023"),
                    "judicial_flag": doc.get("judicial_flag"),
                })
        except Exception as exc:
            logger.warning(f"[suggest_sections] lookup {sec_id} failed: {exc}")

    return confirmed, dropped_ids


# ─── Draft generation ─────────────────────────────────────────────────────────
_DRAFT_SYS = """You are a legal draft writer for Indian citizens.
Generate a first-person FIR complaint letter as required for Section 173(1) BNSS filing.
Be factual. Use exactly the information provided. Output ONLY the letter text, no markdown."""


async def generate_draft(
    slots: dict,
    sections: list[dict],
    evidence_files: list[dict],
    language: str,
    language_name: str,
    llm_key: str,
) -> str:
    """Generate bilingual FIR complaint letter using Claude Sonnet."""
    sec_text = "\n".join(
        f"• BNS Section {s['section_number']}: {s['section_heading']}" for s in sections
    ) or "• To be determined by the investigating officer"
    ev_text = "\n".join(
        f"• Exhibit {i+1}: {e.get('filename', 'File')}" +
        (f" — {e.get('caption')}" if e.get('caption') else f" ({e.get('file_type', 'document')})")
        for i, e in enumerate(evidence_files)
    ) or "None attached at this stage"
    loc = (slots.get("incident_gps_address") or slots.get("incident_place_text") or "[Not provided]")
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")

    # Build witness text (combine witnesses + witnesses_detail)
    witnesses_val = slots.get("witnesses", "None mentioned")
    witnesses_detail = slots.get("witnesses_detail")
    if witnesses_detail and witnesses_detail.lower() not in ["not available right now", "skip", "n/a"]:
        witnesses_val = f"{witnesses_val}; {witnesses_detail}"

    lang_line = (
        f"Then repeat the ENTIRE letter in {language_name}, "
        f"preceded by: --- {language_name.upper()} TRANSLATION ---"
        if language not in ("en", "english") else ""
    )

    # IMPORTANT: Only include incident_place_text if it actually looks like a place.
    # Off-topic answers stored in the field are filtered here as a final safety net.
    place_display = loc
    if loc and not _is_valid_place_response(loc):
        place_display = "[To be provided at the time of statement recording]"

    prompt = f"""Generate a formal FIR complaint letter with the following details:

Complainant name: {slots.get('informant_name') or 'Not provided'}
Complainant address: {slots.get('informant_address') or 'Not provided'}
Contact number: {slots.get('informant_phone') or 'Not provided'}
Date of incident: {slots.get('incident_date') or 'Not specified'}
Time of incident: {slots.get('incident_time') or 'Not specified'}
Place of incident: {place_display}
Incident description: {slots.get('description') or 'Not provided'}
Accused: {slots.get('accused') or 'Not identified'}
Injury: {slots.get('injury') or 'Not reported'}
Property loss / stolen items: {slots.get('property_loss') or 'Not reported'}{' | ' + str(slots.get('theft_items','')) if slots.get('theft_items') else ''}
Force used: {slots.get('force_used') or 'Not reported'}
IMEI (if phone stolen): {slots.get('stolen_phone_imei') or ''}
Transaction IDs: {slots.get('transaction_ids') or ''}
Scammer contact: {slots.get('scammer_contact') or ''}
Additional details: {slots.get('cyber_amount', '')} {slots.get('assault_mlc', '')} {slots.get('harassment_mode', '')}
Witnesses: {witnesses_val}

Applicable BNS sections (suggested):
{sec_text}

Evidence attached:
{ev_text}

Date of report: {date_str}

Write the letter in English, addressed to "The Station House Officer".
Write in first person throughout.
IMPORTANT: NEVER use [bracket placeholders] in the letter. If a detail is missing or not provided, write "Not provided" or omit the sentence entirely. Do not leave any square bracket text in the output.
{lang_line}

End the letter (after both languages if bilingual) with EXACTLY this disclaimer block:
---
\u26a0\ufe0f CITIZEN DRAFT \u2014 NOT A REGISTERED FIR
Present this document at the nearest police station for official registration under Section 173(1) BNSS.
Suggested BNS sections are indicative only \u2014 the investigating officer determines final sections.
FREE LEGAL AID: NALSA 15100 | Women Helpline 181 | Cybercrime 1930 | Police 100"""

    try:
        chat = (
            LlmChat(
                api_key=llm_key,
                session_id=f"fir-draft-{uuid.uuid4()}",
                system_message=_DRAFT_SYS,
            )
            .with_model("anthropic", "claude-sonnet-4-6")
            .with_params(max_tokens=2500)
        )
        return (await chat.send_message(UserMessage(text=prompt)) or "").strip()
    except Exception as e:
        logger.error(f"[generate_draft] LLM failed: {e}")
        return _fallback_draft(slots, sec_text, ev_text, date_str, place_display)


def _fallback_draft(slots: dict, sec_text: str, ev_text: str, date_str: str, loc: str) -> str:
    name = slots.get('informant_name') or 'Complainant'
    address = slots.get('informant_address') or 'Address not provided'
    phone = slots.get('informant_phone') or 'Not provided'
    inc_date = slots.get('incident_date') or 'Date not provided'
    inc_time = slots.get('incident_time') or 'Time not provided'
    desc = slots.get('description') or 'Details to be provided at the time of statement'
    accused = slots.get('accused') or 'Not identified'
    injury = slots.get('injury') or 'Not reported'
    witnesses = slots.get('witnesses') or 'None mentioned'
    return f"""To,
The Station House Officer,
(Police Station to be filled)

Subject: Complaint regarding {desc[:80]}

Sir/Madam,

I, {name}, residing at {address},
contact: {phone}, wish to register the following complaint:

On {inc_date} at {inc_time},
at {loc}, the following occurred:

{desc}

Accused: {accused}
Injury: {injury}
Witnesses: {witnesses}

Evidence attached:
{ev_text}

Applicable BNS sections (suggested):
{sec_text}

I request you to register this FIR and take appropriate legal action.

Yours faithfully,
{name}
Date: {date_str}

---
\u26a0\ufe0f CITIZEN DRAFT \u2014 NOT A REGISTERED FIR
Present at the police station for registration under Section 173(1) BNSS.
FREE LEGAL AID: NALSA 15100 | Women Helpline 181 | Cybercrime 1930 | Police 100"""


# ─── Summary builder ──────────────────────────────────────────────────────────
def _build_summary(slots: dict, sections: list[dict], incident_types: list[str]) -> str:
    lines: list[str] = []
    dt = (slots.get("incident_date") or "") + (" " + slots.get("incident_time", "") if slots.get("incident_time") else "")
    if dt.strip():
        lines.append(f"\U0001f4c5 When: {dt.strip()}")
    loc = slots.get("incident_gps_address") or slots.get("incident_place_text")
    if loc and _is_valid_place_response(str(loc)):
        lines.append(f"\U0001f4cd Where: {str(loc)[:120]}")
    elif loc:
        lines.append("\U0001f4cd Where: To be confirmed at the time of statement")
    if incident_types:
        lines.append(f"\u2696\ufe0f Type: {', '.join(t.replace('_', ' ').title() for t in incident_types)}")
    if slots.get("accused"):
        lines.append(f"\U0001f464 Accused: {str(slots.get('accused', ''))[:100]}")
    if slots.get("injury"):
        lines.append(f"\U0001f3e5 Injury: {slots.get('injury')}")
    if slots.get("informant_name"):
        lines.append(f"\U0001f4dd Complainant: {slots.get('informant_name')}")
    if sections:
        sec_list = ", ".join(f"BNS {s['section_number']}" for s in sections[:4])
        lines.append(f"\U0001f4cb Suggested sections: {sec_list}")
    return "\n".join(lines) or "Summary not available"


# ─── Session creation ─────────────────────────────────────────────────────────
async def create_session(
    db,
    user_id: str,
    language: str,
    session_location_start: Optional[dict] = None,
) -> dict:
    """Create a fresh, blank FIR session. No carryover from any previous session."""
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    blank_slots = {
        "incident_date": None, "incident_time": None,
        "incident_place_text": None, "incident_gps": None, "incident_gps_address": None,
        "description": None, "accused": None, "witnesses": None, "witnesses_detail": None,
        "injury": None, "property_loss": None, "words_or_threats": None,
        "theft_items": None, "cyber_amount": None, "assault_mlc": None, "harassment_mode": None,
        "force_used": None, "stolen_phone_imei": None, "sim_blocked": None,
        "incident_place_detail": None, "transaction_ids": None, "scammer_contact": None,
        "date_confirmed": None,
        "informant_name": None, "informant_address": None, "informant_phone": None,
    }
    doc = {
        "session_id": sid,
        "user_id": user_id,
        "language": language,
        "status": "active",
        "stage": STAGE_SAFETY_GATE,
        "pending_probes": [],
        "current_probe": None,
        "session_location_start": session_location_start,
        "session_location_end": None,
        "incident_types": [],
        "narrative_turns": [],
        "slots": blank_slots,
        "evidence_files": [],
        "suggested_sections": [],
        "dropped_sections": [],
        "safety_flags": [],
        "parked_questions": [],        # v3.1: off-topic user responses parked here
        "date_conflict_msg": None,     # v3.1: set when contradiction detected
        "relative_date_display": None, # v3.3: absolute date computed from relative ("yesterday" → "14 June 2026")
        "phone_retry_done": False,     # v3.1: one phone retry flag
        "probe_history": [],           # v3.3: [{probe, slot, value}] for back navigation
        "draft": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.fir_sessions.insert_one(doc)
    return {
        "session_id": sid,
        "stage": STAGE_SAFETY_GATE,
        "bot_message": (
            "Hello! I'm DHARA, your legal assistant.\n"
            "I'll help you prepare a formal FIR draft step by step.\n\n"
            "Before we begin: are you safe right now?"
        ),
        "input_type": INPUT_QUICK_REPLY,
        "quick_replies": ["Yes, I'm safe", "No, I need help"],
        "safety_flags": [],
        "completed": False,
    }


# ─── Main turn processor ──────────────────────────────────────────────────────
async def process_turn(
    db,
    corpus_db,
    session_id: str,
    user_message: Optional[str],
    gps: Optional[dict],
    action: Optional[str],
    llm_key: str,
) -> dict:
    """Process one conversation turn. Returns the next bot response dict."""
    now = datetime.now(timezone.utc).isoformat()
    session = await db.fir_sessions.find_one({"session_id": session_id})
    if not session:
        return {"error": "Session not found"}

    language: str = session.get("language", "en")
    lang_map = {
        "en": "English", "hi": "Hindi", "ta": "Tamil",
        "mr": "Marathi", "te": "Telugu", "kn": "Kannada",
    }
    language_name = lang_map.get(language, "English")

    stage: str = session.get("stage", STAGE_SAFETY_GATE)
    slots: dict = dict(session.get("slots", {}))
    pending_probes: list[str] = list(session.get("pending_probes", []))
    current_probe: Optional[str] = session.get("current_probe")
    incident_types: list[str] = list(session.get("incident_types", []))

    # Log user turn to conversation history
    if user_message or gps or action:
        msg_log = user_message or (f"[GPS:{gps}]" if gps else f"[{action}]")
        await db.fir_sessions.update_one(
            {"session_id": session_id},
            {"$push": {"narrative_turns": {"role": "user", "message": msg_log, "timestamp": now}},
             "$set": {"updated_at": now}},
        )

    resp = await _dispatch(
        db, corpus_db, session, stage, slots, pending_probes, current_probe,
        incident_types, user_message, gps, action, llm_key, language, language_name, now,
    )

    # Log bot response to conversation history
    if resp.get("bot_message"):
        await db.fir_sessions.update_one(
            {"session_id": session_id},
            {"$push": {"narrative_turns": {
                "role": "bot", "message": resp["bot_message"], "timestamp": now,
            }}},
        )
    return resp


async def _dispatch(
    db, corpus_db, session, stage, slots, pending_probes, current_probe,
    incident_types, user_message, gps, action, llm_key, language, language_name, now,
) -> dict:
    sid: str = session["session_id"]

    # ── Safety Gate ───────────────────────────────────────────────────────────
    if stage == STAGE_SAFETY_GATE:
        sf = _detect_safety_flags(user_message or "")
        # Use boolean flag: action=="not_safe" is the authoritative signal
        # (frontend sends this when "No, I need help" button is tapped)
        not_safe = (
            action == "not_safe"
            or (user_message or "").lower().strip() in [
                "no", "not safe", "in danger", "help me",
                "no i need help", "no, i need help",
            ]
        )
        if not_safe:
            # Pause session so it appears in "Continue your reports"
            await db.fir_sessions.update_one(
                {"session_id": sid},
                {"$set": {"status": "paused", "safety_flags": sf, "updated_at": now}},
            )
            return {
                "session_id": sid, "stage": STAGE_SAFETY_GATE,
                "bot_message": (
                    "\u26a0\ufe0f Please stay safe first.\n\n"
                    "\U0001f4de Emergency: 112\n"
                    "\U0001f4de Women Helpline: 181\n"
                    "\U0001f4de Ambulance: 108\n"
                    "\U0001f4de NALSA Legal Aid: 15100 (free)\n\n"
                    "Call for help now if you are in immediate danger.\n\n"
                    "When you are safe, tap the button below to continue filing your complaint."
                ),
                "input_type": INPUT_QUICK_REPLY,
                "quick_replies": ["I'm safe now \u2014 continue filing", "Exit for now"],
                "show_emergency": True,
                "emergency_numbers": [
                    {"label": "Police / Emergency", "number": "112"},
                    {"label": "Women Helpline", "number": "181"},
                    {"label": "Ambulance", "number": "108"},
                    {"label": "NALSA Legal Aid", "number": "15100"},
                ],
                "safety_flags": sf, "completed": False,
            }

        lines = ["Thank you for trusting DHARA with your complaint."]
        if "POCSO" in sf:
            lines.append("\n\U0001f198 This may involve a child — Childline: 1098 (24×7 FREE)")
        elif sf:
            lines.append("\n\U0001f198 Women / DV Helpline: 181 (24×7 FREE)")
        lines.append("\nPlease tell me in your own words: what happened?\nTake your time — speak or type freely.")
        await db.fir_sessions.update_one(
            {"session_id": sid},
            {"$set": {"stage": STAGE_FREE_NARRATIVE, "safety_flags": sf, "updated_at": now}},
        )
        return {
            "session_id": sid, "stage": STAGE_FREE_NARRATIVE,
            "bot_message": "\n".join(lines),
            "input_type": INPUT_VOICE_TEXT, "quick_replies": [],
            "safety_flags": sf, "completed": False,
        }

    # ── Free Narrative ────────────────────────────────────────────────────────
    elif stage == STAGE_FREE_NARRATIVE:
        narrative = (user_message or "").strip()

        # ── v3.3: Handle safety gate "I'm safe now" continuation ───────────
        if action == "continue_safe":
            await db.fir_sessions.update_one(
                {"session_id": sid},
                {"$set": {"stage": STAGE_FREE_NARRATIVE, "status": "active", "updated_at": now}},
            )
            return {
                "session_id": sid, "stage": STAGE_FREE_NARRATIVE,
                "bot_message": "I'm glad you're safe. Please tell me in your own words: what happened?\nTake your time — speak or type freely.",
                "input_type": INPUT_VOICE_TEXT, "quick_replies": [], "completed": False,
            }

        if len(narrative) < 20:
            return {
                "session_id": sid, "stage": STAGE_FREE_NARRATIVE,
                "bot_message": "Could you share a bit more detail about what happened?",
                "input_type": INPUT_VOICE_TEXT, "quick_replies": [], "completed": False,
            }

        # ── v3.3: Immediate danger detection (EMERGENCY) ────────────────────
        if _detect_immediate_danger(narrative):
            await db.fir_sessions.update_one(
                {"session_id": sid},
                {"$set": {"status": "paused", "updated_at": now}},
            )
            return {
                "session_id": sid, "stage": STAGE_FREE_NARRATIVE,
                "bot_message": (
                    "\u26a0\ufe0f You seem to be describing an ongoing emergency.\n\n"
                    "Please call for help FIRST:\n"
                    "\U0001f4de Emergency: 112\n"
                    "\U0001f4de Women Helpline: 181\n"
                    "\U0001f4de Ambulance: 108\n\n"
                    "Your session is saved. Come back to complete your complaint when you are safe."
                ),
                "input_type": INPUT_QUICK_REPLY,
                "quick_replies": ["I'm safe \u2014 continue filing"],
                "show_emergency": True,
                "action": "EMERGENCY",
                "emergency_numbers": [
                    {"label": "Emergency", "number": "112"},
                    {"label": "Women Helpline", "number": "181"},
                    {"label": "Ambulance", "number": "108"},
                ],
                "completed": False,
            }

        extracted = await extract_slots_llm(narrative, llm_key)

        # ── FIX 8: Keyword fallback + merge for incident_types ──────────────
        raw_types = extracted.get("incident_types") or []
        kw_types = _keyword_classify(narrative)
        if not raw_types or raw_types == ["other"]:
            # LLM gave nothing useful — use keyword results
            raw_types = kw_types
        else:
            # LLM gave results — merge with keyword to catch what LLM missed
            merged = list(set(raw_types) | (set(kw_types) - {"other"}))
            raw_types = merged if merged else raw_types
        new_types = raw_types if raw_types else ["other"]

        # Merge extracted slots (never overwrite existing)
        for key in ["incident_date", "incident_time", "accused", "witnesses",
                    "injury", "property_loss", "words_or_threats", "description"]:
            if extracted.get(key) is not None and not slots.get(key):
                slots[key] = extracted[key]
        if extracted.get("incident_place") and not slots.get("incident_place_text"):
            slots["incident_place_text"] = extracted["incident_place"]

        # ── FIX 1: Date contradiction detection ─────────────────────────────
        date_conflict_msg = _has_date_conflict(narrative, extracted.get("incident_date"))
        if date_conflict_msg:
            slots["incident_date"] = None

        # ── v3.3: Relative date tracking — build confirm message ─────────────
        relative_date_display: Optional[str] = None
        t_low = narrative.lower()
        if extracted.get("incident_date") and not date_conflict_msg:
            if any(kw in t_low for kw in _RELATIVE_DATE_KW.get("today", [])):
                relative_date_display = f"today, {extracted['incident_date']}"
            elif any(kw in t_low for kw in _RELATIVE_DATE_KW.get("yesterday", [])):
                relative_date_display = f"yesterday, {extracted['incident_date']}"

        sf_all = list(set(list(session.get("safety_flags", [])) + _detect_safety_flags(narrative)))
        probe_queue = _build_probe_queue(
            slots, new_types, date_conflict_msg, relative_date_display
        )
        first_probe = probe_queue[0] if probe_queue else None
        remaining = probe_queue[1:] if probe_queue else []

        # ── v3.3: Cybercrime alert for first probe ───────────────────────────
        show_cyber_alert = "cyber_fraud" in new_types

        await db.fir_sessions.update_one(
            {"session_id": sid},
            {"$set": {
                "stage": STAGE_PROBE if first_probe else STAGE_SECTION_SUGGEST,
                "incident_types": new_types, "slots": slots,
                "pending_probes": remaining, "current_probe": first_probe,
                "safety_flags": sf_all,
                "date_conflict_msg": date_conflict_msg,
                "relative_date_display": relative_date_display,
                "updated_at": now,
            }},
        )
        if first_probe:
            types_str = " and ".join(t.replace("_", " ") for t in new_types[:2])
            pdef = PROBE_Q[first_probe]

            # Dynamic message for probe_date_confirm
            if first_probe == "probe_date_confirm" and relative_date_display:
                bot_msg_suffix = (
                    f"I calculated the incident happened on **{relative_date_display}**.\n"
                    "Is that correct?"
                )
            elif first_probe == "probe_date" and date_conflict_msg:
                bot_msg_suffix = date_conflict_msg
            else:
                bot_msg_suffix = pdef["message"]

            # Cybercrime helpline header
            cyber_header = ""
            if show_cyber_alert:
                cyber_header = (
                    "\U0001f6a8 IMPORTANT — CYBERCRIME GOLDEN HOUR ALERT:\n"
                    "Call 1930 (National Cybercrime Helpline) IMMEDIATELY if you lost money.\n"
                    "The sooner you report, the better your chances of recovering funds.\n"
                    "You can also file at cybercrime.gov.in\n\n"
                )

            intro = (
                f"{cyber_header}"
                f"Thank you for sharing that. I can see this involves {types_str}.\n\n"
                f"I have a few clarifying questions to complete your complaint.\n\n"
                f"{bot_msg_suffix}"
            )
            return {
                "session_id": sid, "stage": STAGE_PROBE, "probe_key": first_probe,
                "bot_message": intro,
                "input_type": pdef["input_type"],
                "quick_replies": pdef.get("quick_replies", []),
                "skip_label": pdef.get("skip_label"),
                "safety_flags": sf_all,
                "show_cybercrime_alert": show_cyber_alert,
                "completed": False,
            }
        return await _enter_section_suggest(db, corpus_db, sid, slots, new_types, now)

    # ── Probe ─────────────────────────────────────────────────────────────────
    elif stage == STAGE_PROBE:
        cp = current_probe
        if not cp:
            return await _enter_section_suggest(db, corpus_db, sid, slots, incident_types, now)
        pdef = PROBE_Q.get(cp, {})
        slot_key = pdef.get("slot")

        # ── v3.3: Resume action — re-ask current probe without advancing ──────
        if action == "resume":
            session_fresh = await db.fir_sessions.find_one({"session_id": sid}, {"relative_date_display": 1})
            rdd = (session_fresh or {}).get("relative_date_display")
            if cp == "probe_date_confirm" and rdd:
                bot_msg = (
                    f"Welcome back! Continuing from where you left off.\n\n"
                    f"I calculated the incident happened on **{rdd}**.\nIs that correct?"
                )
            else:
                bot_msg = (
                    f"Welcome back! Continuing from where you left off.\n\n"
                    f"{pdef.get('message', 'Please continue.')}"
                )
            # v3.4: Probe progress for "Q X/Y" UI counter
            done_count = len(session.get("probe_history", []))
            total_probes = done_count + 1 + len(pending_probes)
            return {
                "session_id": sid, "stage": STAGE_PROBE, "probe_key": cp,
                "bot_message": bot_msg,
                "input_type": pdef.get("input_type", INPUT_TEXT),
                "quick_replies": pdef.get("quick_replies", []),
                "skip_label": pdef.get("skip_label"),
                "completed": False,
                "probe_progress_done": done_count,
                "probe_progress_total": total_probes,
            }

        if cp == "probe_place_gps":
            if gps and action != "skip":
                address = await reverse_geocode(gps["lat"], gps["lng"])
                addr = address or f"{gps['lat']:.4f}, {gps['lng']:.4f}"
                slots["incident_gps"] = gps
                slots["incident_gps_address"] = addr
                await db.fir_sessions.update_one(
                    {"session_id": sid},
                    {"$set": {"stage": STAGE_GPS_CONFIRM, "slots": slots, "updated_at": now}},
                )
                return {
                    "session_id": sid, "stage": STAGE_GPS_CONFIRM,
                    "bot_message": f"I found this address:\n\n\U0001f4cd {addr}\n\nIs this correct?",
                    "input_type": INPUT_QUICK_REPLY,
                    "quick_replies": ["Yes, that's correct", "No, use text description"],
                    "confirmed_address": addr, "completed": False,
                }
            else:
                # ── v3.3: GPS declined/skipped — record source ───────────────
                slots["incident_gps"] = {"source": "skipped"}
                await db.fir_sessions.update_one(
                    {"session_id": sid},
                    {"$set": {"slots": slots, "updated_at": now}},
                )
            return await _advance_probe(db, corpus_db, sid, slots, pending_probes, incident_types, now, completed_probe=cp)

        elif cp == "probe_evidence":
            if action in ("skip", "upload_done"):
                return await _advance_probe(db, corpus_db, sid, slots, pending_probes, incident_types, now)
            return {
                "session_id": sid, "stage": STAGE_PROBE, "probe_key": cp,
                "bot_message": pdef["message"], "input_type": INPUT_EVIDENCE,
                "skip_label": pdef.get("skip_label"), "quick_replies": [], "completed": False,
            }

        elif slot_key:
            if action == "skip":
                pass  # advance to next probe

            elif user_message:
                # ── FIX 2 & 3: Place validation + parked_questions ───────────
                if cp == "probe_place_text":
                    if _is_valid_place_response(user_message):
                        slots["incident_place_text"] = user_message
                        await db.fir_sessions.update_one(
                            {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                        )
                    else:
                        # Park the off-topic response and RE-ASK the same probe
                        await db.fir_sessions.update_one(
                            {"session_id": sid},
                            {
                                "$push": {"parked_questions": {
                                    "probe": cp,
                                    "user_response": user_message,
                                    "reason": "off_topic",
                                    "timestamp": now,
                                }},
                                "$set": {"updated_at": now},
                            },
                        )
                        # Return the same probe question again with a note
                        return {
                            "session_id": sid, "stage": STAGE_PROBE, "probe_key": cp,
                            "bot_message": (
                                f"I've noted your question and will come back to it.\n\n"
                                f"For the complaint, I need the **location** of the incident.\n"
                                f"{pdef['message']}"
                            ),
                            "input_type": pdef["input_type"],
                            "quick_replies": pdef.get("quick_replies", []),
                            "skip_label": pdef.get("skip_label"),
                            "completed": False,
                        }

                # ── FIX 4: Accused slot guard ────────────────────────────────
                elif cp == "probe_accused":
                    if _is_witness_answer_in_accused_probe(user_message):
                        # User is answering about witnesses, not accused
                        # Route to witnesses slot if not already set
                        if not slots.get("witnesses"):
                            slots["witnesses"] = user_message
                        slots["accused"] = "Not identified by complainant"
                        await db.fir_sessions.update_one(
                            {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                        )
                    else:
                        slots["accused"] = user_message
                        await db.fir_sessions.update_one(
                            {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                        )

                # ── FIX 5: Witness vague answer → follow-up probe ─────────────
                elif cp == "probe_witnesses":
                    slots["witnesses"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                    if _is_vague_witness_response(user_message):
                        # Insert detail follow-up NEXT in the queue
                        new_pending = ["probe_witnesses_detail"] + pending_probes
                        await db.fir_sessions.update_one(
                            {"session_id": sid},
                            {"$set": {"pending_probes": new_pending, "updated_at": now}}
                        )
                        return await _advance_probe(
                            db, corpus_db, sid, slots, new_pending, incident_types, now
                        )

                elif cp == "probe_witnesses_detail":
                    # Append detail to existing witnesses string
                    existing = slots.get("witnesses", "")
                    slots["witnesses_detail"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )

                # ── FIX 6: Phone validation + one retry ──────────────────────
                elif cp == "probe_informant_phone":
                    if not _is_valid_phone(user_message):
                        phone_retry_done = session.get("phone_retry_done", False)
                        if not phone_retry_done:
                            # One retry
                            await db.fir_sessions.update_one(
                                {"session_id": sid},
                                {"$set": {
                                    "phone_retry_done": True,
                                    "pending_probes": ["probe_informant_phone_retry"] + pending_probes,
                                    "updated_at": now,
                                }},
                            )
                            return {
                                "session_id": sid, "stage": STAGE_PROBE,
                                "probe_key": "probe_informant_phone_retry",
                                "bot_message": PROBE_Q["probe_informant_phone_retry"]["message"],
                                "input_type": INPUT_TEXT,
                                "skip_label": PROBE_Q["probe_informant_phone_retry"]["skip_label"],
                                "quick_replies": [], "completed": False,
                            }
                        else:
                            # Second attempt — accept whatever they give (maybe they have a reason)
                            slots["informant_phone"] = user_message
                            await db.fir_sessions.update_one(
                                {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                            )
                    else:
                        slots["informant_phone"] = user_message
                        await db.fir_sessions.update_one(
                            {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                        )

                elif cp == "probe_informant_phone_retry":
                    # Accept whatever is given at this point
                    slots["informant_phone"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )

                elif cp == "probe_injury":
                    ml = user_message.lower()
                    slots["injury"] = "yes" if ("yes" in ml or "injur" in ml) else "no"
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                elif cp == "probe_harassment_online":
                    slots["harassment_mode"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                # ── v3.3: New probe handlers ─────────────────────────────────
                elif cp == "probe_force_used":
                    m_lower = user_message.lower()
                    force = "yes" in m_lower or "force" in m_lower or "weapon" in m_lower
                    slots["force_used"] = "yes" if force else "no"
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                    # Robbery upgrade: if force confirmed AND theft, add robbery
                    if force and "theft" in incident_types and "robbery" not in incident_types:
                        new_types = list(incident_types) + ["robbery"]
                        # Re-run section retrieval
                        new_sections, _ = await suggest_sections(corpus_db, new_types, slots)
                        # Insert injury + mlc probes if not already in queue
                        extra = []
                        if "probe_injury" not in pending_probes and not slots.get("injury"):
                            extra.append("probe_injury")
                        if "probe_assault_mlc" not in pending_probes:
                            extra.append("probe_assault_mlc")
                        new_pending = extra + pending_probes
                        await db.fir_sessions.update_one(
                            {"session_id": sid},
                            {"$set": {
                                "incident_types": new_types,
                                "suggested_sections": new_sections,
                                "pending_probes": new_pending,
                                "updated_at": now,
                            }}
                        )
                        pending_probes = new_pending
                        incident_types = new_types

                elif cp == "probe_stolen_phone_imei":
                    slots["stolen_phone_imei"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                elif cp == "probe_sim_blocked":
                    slots["sim_blocked"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                elif cp == "probe_incident_place_detail":
                    slots["incident_place_detail"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                elif cp == "probe_transaction_ids":
                    slots["transaction_ids"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                elif cp == "probe_scammer_contact":
                    slots["scammer_contact"] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )
                else:
                    slots[slot_key] = user_message
                    await db.fir_sessions.update_one(
                        {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                    )

        # ── v3.3: Handle probe_date_confirm (quick-reply probe, not text) ───
        if cp == "probe_date_confirm":
            m_lower = (user_message or "").lower()
            if "no" in m_lower or "correct" in m_lower and "yes" not in m_lower:
                # User wants to correct — clear date and prepend probe_date
                slots["incident_date"] = None
                slots["date_confirmed"] = None
                new_pending = ["probe_date"] + pending_probes
                await db.fir_sessions.update_one(
                    {"session_id": sid},
                    {"$set": {"slots": slots, "pending_probes": new_pending, "updated_at": now}}
                )
                return await _advance_probe(db, corpus_db, sid, slots, new_pending, incident_types, now, completed_probe=cp)
            else:
                # User confirmed — mark as confirmed
                slots["date_confirmed"] = True
                await db.fir_sessions.update_one(
                    {"session_id": sid}, {"$set": {"slots": slots, "updated_at": now}}
                )

        return await _advance_probe(db, corpus_db, sid, slots, pending_probes, incident_types, now, completed_probe=cp)

    # ── GPS Confirm ───────────────────────────────────────────────────────────
    elif stage == STAGE_GPS_CONFIRM:
        msg_lower = (user_message or "").lower()
        yes = "yes" in msg_lower or action == "confirm"
        if not yes:
            # User rejected GPS address — clear it, keep text description
            slots["incident_gps"] = None
            slots["incident_gps_address"] = None
            await db.fir_sessions.update_one(
                {"session_id": sid},
                {"$set": {"slots": slots, "updated_at": now}},
            )
        # pending_probes in DB still holds remaining probes (those after probe_place_gps)
        session_fresh = await db.fir_sessions.find_one({"session_id": sid})
        pp = list(session_fresh.get("pending_probes", []))
        slots_fresh = dict(session_fresh.get("slots", {}))
        await db.fir_sessions.update_one(
            {"session_id": sid},
            {"$set": {"stage": STAGE_PROBE, "updated_at": now}},
        )
        return await _advance_probe(db, corpus_db, sid, slots_fresh, pp, incident_types, now)

    # ── Section Suggest ───────────────────────────────────────────────────────
    elif stage == STAGE_SECTION_SUGGEST:
        sections = session.get("suggested_sections", [])
        summary = _build_summary(slots, sections, incident_types)
        await db.fir_sessions.update_one(
            {"session_id": sid}, {"$set": {"stage": STAGE_READ_BACK, "updated_at": now}},
        )
        return {
            "session_id": sid, "stage": STAGE_READ_BACK,
            "bot_message": (
                f"Here is a summary of your complaint:\n\n{summary}\n\n"
                "Is everything correct? Shall I generate your FIR draft?"
            ),
            "input_type": INPUT_CONFIRM,
            "quick_replies": ["Yes, generate my draft", "Edit something"],
            "slots_preview": slots, "suggested_sections": sections, "completed": False,
        }

    # ── Read Back ─────────────────────────────────────────────────────────────
    elif stage == STAGE_READ_BACK:
        msg_lower = (user_message or action or "").lower()
        if "edit" in msg_lower or ("no" in msg_lower and "no, i" not in msg_lower):
            return {
                "session_id": sid, "stage": STAGE_READ_BACK,
                "bot_message": "What would you like to change? Please type the correction and I'll update your complaint.",
                "input_type": INPUT_TEXT, "quick_replies": [], "completed": False,
            }
        # Generate draft
        sections = session.get("suggested_sections", [])
        evidence_files = list(session.get("evidence_files", []))
        await db.fir_sessions.update_one(
            {"session_id": sid}, {"$set": {"stage": STAGE_DRAFT, "updated_at": now}},
        )
        draft_text = await generate_draft(
            slots, sections, evidence_files, language, language_name, llm_key
        )
        await db.fir_sessions.update_one(
            {"session_id": sid},
            {"$set": {"draft": draft_text, "stage": STAGE_COMPLETED, "status": "completed", "updated_at": now}},
        )
        return {
            "session_id": sid, "stage": STAGE_COMPLETED,
            "bot_message": "\u2705 Your FIR draft is ready!\n\nTap \"View Draft\" to see, save, or export it.",
            "input_type": INPUT_DONE, "quick_replies": [],
            "draft": draft_text, "completed": True,
        }

    elif stage == STAGE_COMPLETED:
        return {
            "session_id": sid, "stage": STAGE_COMPLETED,
            "bot_message": "Your draft is ready. Tap \"View Draft\" to see it.",
            "input_type": INPUT_DONE, "draft": session.get("draft", ""),
            "quick_replies": [], "completed": True,
        }

    return {"error": f"Unknown stage: {stage}", "session_id": sid}


async def _advance_probe(
    db, corpus_db, sid: str, slots: dict,
    pending_probes: list[str], incident_types: list[str], now: str,
    completed_probe: Optional[str] = None,
) -> dict:
    """Advance to next probe in queue, or enter section_suggest if none left."""
    # ── v3.3: Track answered probe for back navigation ──────────────────────
    if completed_probe and completed_probe in PROBE_Q:
        pdef_done = PROBE_Q[completed_probe]
        slot_key = pdef_done.get("slot")
        # Store None as "restore value" — going back should clear the slot
        # so the user can re-answer with a fresh prompt
        await db.fir_sessions.update_one(
            {"session_id": sid},
            {"$push": {"probe_history": {"probe": completed_probe, "slot": slot_key, "value": None}}},
        )
    if pending_probes:
        next_probe = pending_probes[0]
        remaining = pending_probes[1:]
        await db.fir_sessions.update_one(
            {"session_id": sid},
            {"$set": {"pending_probes": remaining, "current_probe": next_probe, "updated_at": now}},
        )
        pdef = PROBE_Q[next_probe]
        # Dynamic message for probe_date_confirm; also fetch probe_history for progress counter
        session_fresh = await db.fir_sessions.find_one({"session_id": sid}, {"relative_date_display": 1, "probe_history": 1})
        rdd = session_fresh.get("relative_date_display") if session_fresh else None
        if next_probe == "probe_date_confirm" and rdd:
            bot_msg = f"I calculated the incident happened on **{rdd}**.\nIs that correct?"
        else:
            bot_msg = pdef["message"]
        # v3.4: Compute probe progress for "Q X/Y" frontend counter
        done_count = len((session_fresh or {}).get("probe_history", []))
        total_probes = done_count + 1 + len(remaining)
        return {
            "session_id": sid, "stage": STAGE_PROBE, "probe_key": next_probe,
            "bot_message": bot_msg,
            "input_type": pdef["input_type"],
            "quick_replies": pdef.get("quick_replies", []),
            "skip_label": pdef.get("skip_label"), "completed": False,
            "probe_progress_done": done_count,
            "probe_progress_total": total_probes,
        }
    return await _enter_section_suggest(db, corpus_db, sid, slots, incident_types, now)


async def _enter_section_suggest(
    db, corpus_db, sid: str, slots: dict, incident_types: list[str], now: str,
) -> dict:
    """Run Citation Guard and enter section_suggest stage."""
    confirmed, dropped = await suggest_sections(corpus_db, incident_types, slots)
    await db.fir_sessions.update_one(
        {"session_id": sid},
        {"$set": {
            "stage": STAGE_SECTION_SUGGEST,
            "suggested_sections": confirmed,
            "dropped_sections": dropped,
            "updated_at": now,
        }},
    )
    if confirmed:
        sec_lines = "\n".join(
            f"• BNS {s['section_number']} \u2014 {s['section_heading']}" for s in confirmed[:6]
        )
        msg = (
            f"Based on your description, the following BNS sections appear to apply:\n\n"
            f"{sec_lines}\n\n"
            "\u26a0\ufe0f These are suggestions only \u2014 the investigating officer determines final sections.\n\n"
            "Shall I proceed with generating your draft?"
        )
    else:
        msg = (
            "I've gathered all the details for your complaint.\n\n"
            "The applicable BNS sections will be noted by the investigating officer.\n\n"
            "Ready to generate your FIR draft?"
        )
    return {
        "session_id": sid, "stage": STAGE_SECTION_SUGGEST,
        "bot_message": msg, "input_type": INPUT_CONFIRM,
        "quick_replies": ["Yes, proceed", "Go back"],
        "suggested_sections": confirmed,
        "dropped_sections": dropped,  # Issue 9: expose dropped sections for drawer
        "completed": False,
    }
