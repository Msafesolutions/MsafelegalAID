"""
FIR Offence Classifier — DHARA BNS

Maps a free-text incident narrative to candidate BNS sections.

Design principles
-----------------
* UNDER-CLAIM, never over-claim.  Every result carries a confidence signal
  and is framed as "suggested — confirm with the officer."
* Dead-Law Guard: every candidate is checked against judicial_invalidations
  before being returned.  A struck-down section is NEVER shown.
* Safety branch: DV / sexual offence / POCSO triggers are detected and
  returned as a separate flag so the caller can surface helplines FIRST.
* 15 cognizable offences for MVP — expandable to 40 by adding to OFFENCES.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# Load the Dead-Law Guard at import time
# ---------------------------------------------------------------------------
_SEED = Path(__file__).parent / "corpus_seed"


def _load_invalidations() -> set[str]:
    """Return a set of 'ACT|SECTION' strings that are struck down / repealed."""
    dead: set[str] = set()
    gz = _SEED / "judicial_invalidations.jsonl.gz"
    if not gz.exists():
        return dead
    with gzip.open(gz) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                key = f"{rec.get('act_name','').strip()}|{rec.get('section_number','').strip()}"
                dead.add(key)
                dead.add(rec.get("section_number", "").strip())  # bare number fallback
            except Exception:
                pass
    return dead


DEAD_SECTIONS: set[str] = _load_invalidations()


def is_dead_law(act_name: str, section: str) -> bool:
    """Return True if this section is struck down or repealed."""
    bare = str(section).strip()
    full = f"{act_name.strip()}|{bare}"
    return bare in DEAD_SECTIONS or full in DEAD_SECTIONS


# ---------------------------------------------------------------------------
# Offence definitions — 15 most common cognizable offences
# ---------------------------------------------------------------------------

class OffenceDef(TypedDict):
    bns_section: str
    bns_heading: str
    legacy_ipc: str
    confidence_weight: int           # keyword hit multiplier
    keywords_en: list[str]
    keywords_hi: list[str]           # romanised Hindi / common usage
    doc_checklist: list[str]
    safety_flag: str | None          # "DV" | "SEXUAL" | "POCSO" | None


OFFENCES: list[OffenceDef] = [
    # ── Theft ────────────────────────────────────────────────────────────
    {
        "bns_section": "303",
        "bns_heading": "Theft",
        "legacy_ipc": "IPC 379",
        "confidence_weight": 3,
        "keywords_en": [
            "stole", "stolen", "theft", "steal", "stole", "pickpocket",
            "burglar", "burglary", "missing phone", "missing wallet", "missing money",
            "snatched", "snatch", "robbed my phone", "took my", "took away",
        ],
        "keywords_hi": [
            "chori", "chor", "churaya", "le gaya", "pocket maar",
            "gum ho gaya", "ghadi chori",
        ],
        "doc_checklist": [
            "List of stolen items with approximate value",
            "Photographs of the location / broken lock if applicable",
            "CCTV footage (request in writing from establishment)",
            "Bank statement if cash/cheque stolen",
            "Photo of unique serial/IMEI numbers for electronics",
        ],
        "safety_flag": None,
    },
    # ── Hurt / Assault ───────────────────────────────────────────────────
    {
        "bns_section": "115",
        "bns_heading": "Voluntarily causing hurt",
        "legacy_ipc": "IPC 323",
        "confidence_weight": 3,
        "keywords_en": [
            "hit", "beat", "punch", "slap", "kick", "attack", "assault",
            "injured", "injury", "wounded", "hurt", "bruise", "broken bone",
            "fracture", "hospitalised", "hospital", "physical violence",
        ],
        "keywords_hi": [
            "maara", "peeta", "dhoond mara", "chot lagi", "zakhmi", "hospital gaya",
            "haddi tooti", "maar diya", "thappad",
        ],
        "doc_checklist": [
            "Medical certificate / MLC (Medico-Legal Certificate) — get this FIRST",
            "Photographs of injuries (time-stamped)",
            "Witness names and contact numbers",
            "Clothes worn at time of incident (preserve, don't wash)",
        ],
        "safety_flag": None,
    },
    # ── Grievous Hurt ────────────────────────────────────────────────────
    {
        "bns_section": "117",
        "bns_heading": "Voluntarily causing grievous hurt",
        "legacy_ipc": "IPC 325",
        "confidence_weight": 3,
        "keywords_en": [
            "grievous", "serious injury", "broken", "fracture", "permanent", "disability",
            "disfigured", "acid attack", "severe beating", "knife", "stabbed",
            "gun", "shot", "bullet",
        ],
        "keywords_hi": [
            "ghav", "sangeen chot", "tooti haddi", "tezaab", "chaku", "goli",
        ],
        "doc_checklist": [
            "MLC (Medico-Legal Certificate) — mandatory, obtain from hospital",
            "X-ray / scan reports",
            "Photographs of injuries (time-stamped)",
            "Doctor's statement if possible",
            "Clothes worn at time (preserve as evidence)",
        ],
        "safety_flag": None,
    },
    # ── Cheating ─────────────────────────────────────────────────────────
    {
        "bns_section": "318",
        "bns_heading": "Cheating",
        "legacy_ipc": "IPC 420",
        "confidence_weight": 3,
        "keywords_en": [
            "cheated", "fraud", "fraudulent", "deceived", "deception", "fake",
            "false promise", "took money", "did not deliver", "scam", "misrepresentation",
            "forged", "bogus", "impersonated", "lied to get",
        ],
        "keywords_hi": [
            "dhoka", "fraud kiya", "thaga", "jhooth bola", "paisa le gaya",
            "paise wapas nahi", "nakli", "jali",
        ],
        "doc_checklist": [
            "Agreement / contract copy",
            "Payment receipts / bank transaction records",
            "Correspondence (messages, emails, letters)",
            "Any advertisement or prospectus relied upon",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── Criminal Intimidation ────────────────────────────────────────────
    {
        "bns_section": "351",
        "bns_heading": "Criminal intimidation",
        "legacy_ipc": "IPC 506",
        "confidence_weight": 3,
        "keywords_en": [
            "threatened", "threat", "intimidate", "intimidation", "blackmail",
            "will kill", "will harm", "life threat", "death threat", "scared",
            "fear", "sending threats", "threatening message", "threatening call",
        ],
        "keywords_hi": [
            "dhamki", "dara raha", "jaan se maarne ki dhamki", "blackmail",
            "daraya", "khauf",
        ],
        "doc_checklist": [
            "Screenshots / recordings of threatening messages or calls",
            "Call log / phone records",
            "Witness statements",
            "Any written threat letter",
        ],
        "safety_flag": None,
    },
    # ── Robbery ──────────────────────────────────────────────────────────
    {
        "bns_section": "309",
        "bns_heading": "Robbery",
        "legacy_ipc": "IPC 390",
        "confidence_weight": 3,
        "keywords_en": [
            "rob", "robbed", "robbery", "snatched at gunpoint", "snatched at knifepoint",
            "loot", "looted", "mugged", "mugging", "forced to give", "chain snatching",
        ],
        "keywords_hi": [
            "loot", "loota", "chain lunchi", "gunpoint pe", "chheen liya",
            "zameen par gira ke",
        ],
        "doc_checklist": [
            "List of items taken with approximate value",
            "MLC if injured during robbery",
            "CCTV footage (request in writing)",
            "Witness names",
        ],
        "safety_flag": None,
    },
    # ── Murder / Culpable Homicide ───────────────────────────────────────
    {
        "bns_section": "101",
        "bns_heading": "Culpable homicide amounting to murder",
        "legacy_ipc": "IPC 302",
        "confidence_weight": 4,
        "keywords_en": [
            "killed", "kill", "murder", "murdered", "dead", "died", "death",
            "lost their life", "culpable homicide", "manslaughter",
        ],
        "keywords_hi": [
            "mara diya", "hatyaa", "qatl", "maut", "mar gaya", "jaan le li",
        ],
        "doc_checklist": [
            "Post-mortem report",
            "Death certificate",
            "Medical records",
            "Witness statements (eye-witnesses)",
            "CCTV / video evidence if available",
        ],
        "safety_flag": None,
    },
    # ── Attempt to Murder ────────────────────────────────────────────────
    {
        "bns_section": "109",
        "bns_heading": "Attempt to commit murder",
        "legacy_ipc": "IPC 307",
        "confidence_weight": 4,
        "keywords_en": [
            "tried to kill", "attempt to murder", "attempted murder", "tried to stab",
            "tried to shoot", "tried to poison", "almost killed",
        ],
        "keywords_hi": [
            "maarne ki koshish", "jaan lene ki koshish", "attack kiya",
        ],
        "doc_checklist": [
            "MLC (Medico-Legal Certificate)",
            "X-ray / scan reports if injured",
            "Weapon used (photograph / actual if safe to preserve)",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── Trespass ─────────────────────────────────────────────────────────
    {
        "bns_section": "329",
        "bns_heading": "Criminal trespass",
        "legacy_ipc": "IPC 447",
        "confidence_weight": 2,
        "keywords_en": [
            "trespass", "trespassing", "entered without permission", "broke into",
            "breaking into", "forcibly entered", "illegal entry", "locked out",
            "thrown out", "dispossessed",
        ],
        "keywords_hi": [
            "ghar mein ghus gaya", "zor se andar aaya", "land par kabja",
            "makan se nikala", "ghuspaith",
        ],
        "doc_checklist": [
            "Ownership documents (sale deed / khata / rent agreement)",
            "Photographs of illegal entry / damage",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── Kidnapping / Abduction ───────────────────────────────────────────
    {
        "bns_section": "140",
        "bns_heading": "Kidnapping or abducting in order to murder",
        "legacy_ipc": "IPC 364",
        "confidence_weight": 4,
        "keywords_en": [
            "kidnap", "kidnapped", "abduct", "abducted", "taken away by force",
            "missing child", "child not returned", "forcibly taken",
        ],
        "keywords_hi": [
            "apaharan", "kidnap", "uthaake le gaye", "bacha gum hai", "le gaye",
        ],
        "doc_checklist": [
            "Recent photograph of victim",
            "Last known location and time",
            "Suspected vehicle details (if any)",
            "Contact details of known associates of suspect",
        ],
        "safety_flag": None,
    },
    # ── Extortion ────────────────────────────────────────────────────────
    {
        "bns_section": "308",
        "bns_heading": "Extortion",
        "legacy_ipc": "IPC 384",
        "confidence_weight": 3,
        "keywords_en": [
            "extortion", "extort", "demanded money with threat",
            "pay or else", "hafta", "protection money", "forced to pay",
        ],
        "keywords_hi": [
            "vasuli", "hafta", "paisa mango nahi toh", "ransom", "fidya",
        ],
        "doc_checklist": [
            "Screenshots of extortion messages",
            "Bank transaction records (if payment made)",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── Forgery ──────────────────────────────────────────────────────────
    {
        "bns_section": "334",
        "bns_heading": "Forgery",
        "legacy_ipc": "IPC 465",
        "confidence_weight": 2,
        "keywords_en": [
            "forged", "forgery", "fake document", "fake signature",
            "forged signature", "tampered document", "fake certificate",
            "counterfeit", "fraudulent document",
        ],
        "keywords_hi": [
            "nakli dastavez", "jali hastakshar", "nakli certificate", "nakli seal",
        ],
        "doc_checklist": [
            "Original document (if available)",
            "Forged document (photocopy / photograph)",
            "Expert opinion if possible (document examiner)",
            "Correspondence showing forgery",
        ],
        "safety_flag": None,
    },
    # ── Cruelty by Husband / DV ──────────────────────────────────────────
    {
        "bns_section": "85",
        "bns_heading": "Husband or relative of husband of a woman subjecting her to cruelty",
        "legacy_ipc": "IPC 498A",
        "confidence_weight": 3,
        "keywords_en": [
            "husband beat", "husband hit", "dowry", "in-laws harassment",
            "domestic violence", "dowry demand", "husband cruelty",
            "mental torture by husband", "harassed by in-laws",
            "forced out of house", "thrown out by husband",
        ],
        "keywords_hi": [
            "pati ne maara", "dahej", "sasural wale", "ghar se nikala",
            "dv", "gharelu hinsa", "dahej ke liye tang kar raha hai",
        ],
        "doc_checklist": [
            "MLC if physically injured",
            "Photographs of injuries",
            "Marriage certificate",
            "Dowry demand evidence (messages / letters)",
            "Contact: iCall / 181 Women Helpline / NALSA",
        ],
        "safety_flag": "DV",
    },
    # ── Sexual Harassment / Outrage of Modesty ───────────────────────────
    {
        "bns_section": "74",
        "bns_heading": "Assault or use of criminal force on woman with intent to outrage her modesty",
        "legacy_ipc": "IPC 354",
        "confidence_weight": 4,
        "keywords_en": [
            "molested", "molestation", "groped", "touched inappropriately",
            "outrage modesty", "sexual harassment", "eve teasing",
            "indecent act", "sexually assaulted", "raped", "rape",
            "gang raped", "gang rape",
        ],
        "keywords_hi": [
            "chhedan", "chhednaa", "badtameezi", "haath lagaya", "balaatkaar",
            "balatkaar", "sexual harassment", "bura touch",
        ],
        "doc_checklist": [
            "MLC at government hospital — seek medical examination IMMEDIATELY",
            "Do NOT wash clothes / body before examination if safe to do so",
            "Contact: 181 Women Helpline / One Stop Centre",
            "NALSA toll-free 15100 for free legal aid",
            "You can file Zero FIR at any police station",
        ],
        "safety_flag": "SEXUAL",
    },
    # ── POCSO ────────────────────────────────────────────────────────────
    {
        "bns_section": "POCSO_4",
        "bns_heading": "POCSO Act 2012 — Penetrative sexual assault on child",
        "legacy_ipc": "POCSO Act 2012",
        "confidence_weight": 5,
        "keywords_en": [
            "child abuse", "minor abused", "minor raped", "child raped",
            "boy abused", "girl abused", "POCSO", "sexually abused child",
            "child sexual abuse", "abuse of minor",
        ],
        "keywords_hi": [
            "bacche ke saath", "naabalig ke saath", "bachchi ke saath",
            "bacchon ka shoshan",
        ],
        "doc_checklist": [
            "MLC at government hospital — seek medical examination IMMEDIATELY",
            "Contact: Childline 1098 (24×7 FREE)",
            "NALSA toll-free 15100 for free legal aid",
            "Do NOT delay — time is critical in POCSO matters",
            "Zero FIR must be accepted at ANY police station",
        ],
        "safety_flag": "POCSO",
    },
]

# ---------------------------------------------------------------------------
# Safety-branch keywords (adversarial-robust — checked INDEPENDENTLY of
# the classifier so the branch fires even when the main classifier misses)
# ---------------------------------------------------------------------------
_SAFETY_PATTERNS: dict[str, list[str]] = {
    "DV": [
        r"\bdomestic.?violenc\b", r"\bpati\b.{0,40}\bmaara?\b",
        r"\bdahej\b", r"\bdownry\b", r"\bhusband.{0,30}\bbeat\b",
        r"\bhusband.{0,30}\bhit\b", r"\bcruelty.{0,30}\bhusband\b",
        r"\bgharel[uo]\b", r"\bdv\b", r"\bgharelu\s+hinsa\b",
        r"\bin.?laws.{0,40}\bharass\b", r"\bsasural\b",
    ],
    "SEXUAL": [
        r"\brap(e|ed|ing)\b", r"\bsexual\s+assault\b", r"\bmolest\b",
        r"\boutrage.{0,20}modesty\b", r"\bgrope\b", r"\beve.?teas\b",
        r"\bbalatkaar\b", r"\bbalaatkaar\b", r"\bchhedan\b",
        r"\bindecent.{0,20}act\b",
    ],
    "POCSO": [
        r"\bchild.{0,30}\bsexual\b", r"\bminor.{0,30}\babuse\b",
        r"\bpocso\b", r"\bchild.{0,30}\brap\b", r"\bminor.{0,30}\brap\b",
        r"\bbackche\b.{0,30}\bshoshan\b", r"\bnaabalig\b.{0,30}",
        r"\bbachch.{0,20}\bsexual\b", r"\b1098\b",
    ],
}


def detect_safety_flags(text: str) -> list[str]:
    """Return list of safety flags (DV/SEXUAL/POCSO) fired by the narrative."""
    low = text.lower()
    flags: list[str] = []
    for flag, patterns in _SAFETY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, low):
                flags.append(flag)
                break
    return flags


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def _score(text_lower: str, offence: OffenceDef) -> int:
    score = 0
    for kw in offence["keywords_en"] + offence["keywords_hi"]:
        if kw.lower() in text_lower:
            score += offence["confidence_weight"]
    return score


def _confidence_label(score: int, max_score: int) -> str:
    if max_score == 0:
        return "low"
    ratio = score / max_score
    if ratio >= 0.6:
        return "medium"      # never "high" — we always under-claim
    if ratio >= 0.3:
        return "low"
    return "low"


def classify_incident(narrative: str, top_n: int = 3) -> dict:
    """
    Classify a free-text incident narrative.

    Returns
    -------
    {
        "candidates": [
            {
                "bns_section": str,
                "bns_heading": str,
                "legacy_ipc": str,
                "confidence": "medium" | "low",
                "doc_checklist": [...],
                "safety_flag": str | None,
                "dead_law": False,   # always False — dead sections filtered out
            },
            ...
        ],
        "safety_flags": ["DV", "SEXUAL", "POCSO"],  # independent check
        "disclaimer": str,
    }
    """
    text_lower = narrative.lower()

    scored: list[tuple[int, OffenceDef]] = []
    for offence in OFFENCES:
        s = _score(text_lower, offence)
        if s > 0:
            scored.append((s, offence))

    scored.sort(key=lambda x: x[0], reverse=True)

    max_score = scored[0][0] if scored else 1
    candidates = []
    for score, off in scored[:top_n]:
        # Dead-Law Guard
        if is_dead_law("Bharatiya Nyaya Sanhita, 2023", off["bns_section"]):
            continue
        if is_dead_law("POCSO", off["bns_section"]):
            continue
        candidates.append({
            "bns_section": off["bns_section"],
            "bns_heading": off["bns_heading"],
            "legacy_ipc": off["legacy_ipc"],
            "confidence": _confidence_label(score, max_score),
            "doc_checklist": off["doc_checklist"],
            "safety_flag": off["safety_flag"],
            "dead_law": False,
        })

    # Independent safety check (fires even if classifier returns nothing)
    safety_flags = detect_safety_flags(narrative)
    # Also collect from candidates
    for c in candidates:
        if c["safety_flag"] and c["safety_flag"] not in safety_flags:
            safety_flags.append(c["safety_flag"])

    return {
        "candidates": candidates,
        "safety_flags": safety_flags,
        "disclaimer": (
            "⚠️ SUGGESTED SECTIONS ONLY — These BNS sections are a starting point "
            "based on your description. The police officer will determine the applicable "
            "sections after investigation. This is NOT a registered FIR and NOT legal advice. "
            "[DISCLAIMER TEXT FLAGGED FOR COUNSEL REVIEW — DO NOT PUBLISH WITHOUT APPROVAL]"
        ),
    }
