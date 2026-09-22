"""
FIR Offence Classifier — DHARA BNS (v2)

Maps a free-text incident narrative to candidate BNS sections.

Design principles
-----------------
* UNDER-CLAIM, never over-claim.  Every result carries a confidence signal
  and is framed as "suggested — confirm with the officer."
* Dead-Law Guard: every candidate is checked against judicial_invalidations
  before being returned.  A struck-down section is NEVER shown.
* Safety branch: DV / sexual offence / POCSO triggers are detected and
  returned as a separate flag so the caller can surface helplines FIRST.
* 40 cognizable offences — LLM-assisted primary, keyword fallback.
* IPC → BNS, CrPC → BNSS, IEA → BSA throughout.
"""

from __future__ import annotations

import gzip
import json
import re
import uuid
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# Load the Dead-Law Guard at import time
# ---------------------------------------------------------------------------
_SEED = Path(__file__).parent / "corpus_seed"


# Only these statuses mean the section can no longer be relied upon.
# READ_DOWN / CONTESTED / UPHELD / RESTORED sections are still valid law
# (possibly with a narrower interpretation) and must NOT be hidden.
_DEAD_STATUSES = {"STRUCK_DOWN", "IN_ABEYANCE", "REPEALED"}


def _norm_act(act_name: str) -> str:
    """Normalise an act name for matching — lowercase, strip a leading
    'the ', collapse whitespace. Prevents 'The Indian Penal Code, 1860'
    and 'Indian Penal Code, 1860' from being treated as different acts."""
    n = re.sub(r"\s+", " ", act_name.strip().lower())
    if n.startswith("the "):
        n = n[4:]
    return n


def _load_invalidations() -> set[str]:
    """Return a set of normalised 'act|section' keys that are struck down,
    repealed, or in abeyance — i.e. genuinely dead law. Each key is scoped
    to its own act, so a bare section number is NEVER used on its own:
    otherwise unrelated acts that happen to share a section number (e.g.
    IPC S.303, struck down in Mithu v. State of Punjab, vs BNS S.303,
    the active Theft provision) would collide and wrongly block a live
    section."""
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
                if str(rec.get("status", "")).strip().upper() not in _DEAD_STATUSES:
                    continue
                act = _norm_act(str(rec.get("act_name", "")))
                section = str(rec.get("section_number", "")).strip()
                if act and section:
                    dead.add(f"{act}|{section}")
            except Exception:
                pass
    return dead


DEAD_SECTIONS: set[str] = _load_invalidations()


def is_dead_law(act_name: str, section: str) -> bool:
    bare = str(section).strip()
    full = f"{_norm_act(act_name)}|{bare}"
    return full in DEAD_SECTIONS


# ---------------------------------------------------------------------------
# Offence definitions — 40 cognizable offences
# ---------------------------------------------------------------------------

class OffenceDef(TypedDict):
    bns_section: str
    bns_heading: str
    legacy_ipc: str
    confidence_weight: int
    keywords_en: list[str]
    keywords_hi: list[str]
    doc_checklist: list[str]
    safety_flag: str | None


OFFENCES: list[OffenceDef] = [
    # ── 1. Theft ────────────────────────────────────────────────────────────
    {
        "bns_section": "303",
        "bns_heading": "Theft",
        "legacy_ipc": "IPC 379",
        "confidence_weight": 3,
        "keywords_en": [
            "stole", "stolen", "theft", "steal", "pickpocket",
            "burglar", "burglary", "missing phone", "missing wallet",
            "snatched", "snatch", "took my", "took away",
        ],
        "keywords_hi": ["chori", "chor", "churaya", "le gaya", "pocket maar", "ghadi chori"],
        "doc_checklist": [
            "List of stolen items with approximate value",
            "Photographs of the location / broken lock",
            "CCTV footage request (in writing)",
            "Bank statement if cash stolen",
            "IMEI numbers for electronics",
        ],
        "safety_flag": None,
    },
    # ── 2. Hurt ─────────────────────────────────────────────────────────────
    {
        "bns_section": "115",
        "bns_heading": "Voluntarily causing hurt",
        "legacy_ipc": "IPC 323",
        "confidence_weight": 3,
        "keywords_en": [
            "hit", "beat", "punch", "slap", "kick", "attack", "assault",
            "injured", "injury", "wounded", "hurt", "bruise", "broken bone",
            "fracture", "hospitalised", "physical violence",
        ],
        "keywords_hi": ["maara", "peeta", "chot lagi", "zakhmi", "hospital gaya", "thappad"],
        "doc_checklist": [
            "MLC (Medico-Legal Certificate) — get this FIRST",
            "Photographs of injuries (time-stamped)",
            "Witness names and contacts",
            "Clothes worn at time (preserve, don't wash)",
        ],
        "safety_flag": None,
    },
    # ── 3. Grievous Hurt ────────────────────────────────────────────────────
    {
        "bns_section": "117",
        "bns_heading": "Voluntarily causing grievous hurt",
        "legacy_ipc": "IPC 325",
        "confidence_weight": 3,
        "keywords_en": [
            "grievous", "serious injury", "broken", "fracture", "permanent",
            "disability", "disfigured", "severe beating", "knife", "stabbed",
            "gun", "shot", "bullet",
        ],
        "keywords_hi": ["ghav", "sangeen chot", "tooti haddi", "chaku", "goli"],
        "doc_checklist": [
            "MLC — mandatory, obtain from hospital",
            "X-ray / scan reports",
            "Photographs of injuries",
            "Clothes worn at time (preserve as evidence)",
        ],
        "safety_flag": None,
    },
    # ── 4. Acid Attack ──────────────────────────────────────────────────────
    {
        "bns_section": "124",
        "bns_heading": "Voluntarily causing grievous hurt by use of acid",
        "legacy_ipc": "IPC 326A",
        "confidence_weight": 5,
        "keywords_en": [
            "acid attack", "acid thrown", "corrosive substance", "acid burn",
            "chemical thrown", "tezaab",
        ],
        "keywords_hi": ["tezaab", "tezaab pheka", "acid pheka"],
        "doc_checklist": [
            "Emergency medical care FIRST — government hospital for free treatment",
            "MLC from hospital",
            "Photographs of injuries",
            "Call: 181 Women Helpline / 100 Police",
            "NALSA 15100 for free legal aid",
        ],
        "safety_flag": "SEXUAL",
    },
    # ── 5. Cheating / Fraud ─────────────────────────────────────────────────
    {
        "bns_section": "318",
        "bns_heading": "Cheating",
        "legacy_ipc": "IPC 420",
        "confidence_weight": 3,
        "keywords_en": [
            "cheated", "fraud", "fraudulent", "deceived", "deception", "fake",
            "false promise", "took money", "did not deliver", "scam",
            "misrepresentation", "bogus", "lied to get",
        ],
        "keywords_hi": ["dhoka", "fraud kiya", "thaga", "jhooth bola", "paisa le gaya", "nakli"],
        "doc_checklist": [
            "Agreement / contract copy",
            "Payment receipts / bank records",
            "Correspondence (messages, emails)",
            "Advertisement or prospectus relied upon",
        ],
        "safety_flag": None,
    },
    # ── 6. Online Fraud / IT Act 66D ────────────────────────────────────────
    {
        "bns_section": "IT_66D",
        "bns_heading": "Cheating by personation using computer (IT Act 66D)",
        "legacy_ipc": "IT Act 66D",
        "confidence_weight": 3,
        "keywords_en": [
            "online fraud", "cyber fraud", "fake website", "phishing", "otp fraud",
            "upi fraud", "online scam", "digital payment fraud", "fake app",
            "impersonated online", "social media fake account",
        ],
        "keywords_hi": ["online thagi", "cyber fraud", "otp diya aur paisa gaya"],
        "doc_checklist": [
            "Screenshots of fraudulent messages / website",
            "Bank / UPI transaction records",
            "Cyber Crime portal complaint: cybercrime.gov.in",
            "Call: 1930 (National Cybercrime Helpline)",
        ],
        "safety_flag": None,
    },
    # ── 7. Identity Theft / IT Act 66C ──────────────────────────────────────
    {
        "bns_section": "IT_66C",
        "bns_heading": "Identity theft using electronic signature (IT Act 66C)",
        "legacy_ipc": "IT Act 66C",
        "confidence_weight": 3,
        "keywords_en": [
            "identity theft", "stole my identity", "fake profile", "account hacked",
            "email hacked", "social media hacked", "password stolen",
            "used my documents", "impersonated me",
        ],
        "keywords_hi": ["identity chori", "account hack", "profile fake"],
        "doc_checklist": [
            "Screenshot of fake profile / hacked account",
            "Complaint to platform (Facebook, Google, etc.)",
            "cybercrime.gov.in complaint",
            "Call: 1930 Cybercrime Helpline",
        ],
        "safety_flag": None,
    },
    # ── 8. Criminal Intimidation ────────────────────────────────────────────
    {
        "bns_section": "351",
        "bns_heading": "Criminal intimidation",
        "legacy_ipc": "IPC 506",
        "confidence_weight": 3,
        "keywords_en": [
            "threatened", "threat", "intimidate", "blackmail",
            "will kill", "will harm", "life threat", "death threat",
            "threatening message", "threatening call",
        ],
        "keywords_hi": ["dhamki", "dara raha", "jaan se maarne ki dhamki", "blackmail", "daraya"],
        "doc_checklist": [
            "Screenshots of threatening messages / calls",
            "Call log / phone records",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── 9. Stalking ─────────────────────────────────────────────────────────
    {
        "bns_section": "77",
        "bns_heading": "Stalking",
        "legacy_ipc": "IPC 354D",
        "confidence_weight": 4,
        "keywords_en": [
            "stalking", "stalked", "following me", "keeps following",
            "watching my house", "monitoring me", "tracking me",
            "repeatedly contacting", "won't stop calling",
        ],
        "keywords_hi": ["peecha kar raha", "follow kar raha", "tippani kar raha"],
        "doc_checklist": [
            "Call logs showing repeated calls",
            "Screenshots of repeated messages",
            "Witness statements",
            "Contact: 181 Women Helpline",
        ],
        "safety_flag": "DV",
    },
    # ── 10. Cyberstalking ───────────────────────────────────────────────────
    {
        "bns_section": "78",
        "bns_heading": "Cyberstalking",
        "legacy_ipc": "BNS 78 (new)",
        "confidence_weight": 4,
        "keywords_en": [
            "cyberstalking", "online harassment", "harassment online",
            "trolling", "cyber bully", "cyberbully", "sending obscene messages",
            "morphed photos", "fake photos online", "defaming online",
        ],
        "keywords_hi": ["online pareshan", "cyber harassment", "morphed photo"],
        "doc_checklist": [
            "Screenshots of all harassing content",
            "Platform complaint reference number",
            "cybercrime.gov.in complaint",
            "Call: 1930 / 181",
        ],
        "safety_flag": "DV",
    },
    # ── 11. Sexual Harassment ───────────────────────────────────────────────
    {
        "bns_section": "75",
        "bns_heading": "Sexual harassment",
        "legacy_ipc": "IPC 354A",
        "confidence_weight": 4,
        "keywords_en": [
            "sexual harassment at work", "workplace harassment",
            "boss touched me", "colleague harassed", "posh act",
            "sexually harassed at office", "unwanted advances",
        ],
        "keywords_hi": ["kaam ki jagah pareshan", "office mein badtameezi"],
        "doc_checklist": [
            "Written complaint to Internal Complaints Committee (ICC)",
            "Emails / message evidence",
            "Witness statements (colleagues)",
            "Contact: SHe-Box portal (shebox.wcd.nic.in)",
        ],
        "safety_flag": "SEXUAL",
    },
    # ── 12. Outrage of Modesty / Sexual Assault ─────────────────────────────
    {
        "bns_section": "74",
        "bns_heading": "Assault or criminal force on woman to outrage modesty",
        "legacy_ipc": "IPC 354",
        "confidence_weight": 4,
        "keywords_en": [
            "molested", "molestation", "groped", "touched inappropriately",
            "outrage modesty", "eve teasing", "indecent act",
            "sexually assaulted", "raped", "rape", "gang raped",
        ],
        "keywords_hi": [
            "chhedan", "chhednaa", "badtameezi", "haath lagaya",
            "balaatkaar", "balatkaar", "bura touch",
        ],
        "doc_checklist": [
            "MLC at government hospital — seek medical exam IMMEDIATELY",
            "Do NOT wash clothes / body before examination",
            "Contact: 181 Women Helpline / One Stop Centre",
            "NALSA 15100 — free legal aid",
            "Zero FIR at any police station",
        ],
        "safety_flag": "SEXUAL",
    },
    # ── 13. POCSO ───────────────────────────────────────────────────────────
    {
        "bns_section": "POCSO_4",
        "bns_heading": "POCSO Act 2012 — Penetrative sexual assault on child",
        "legacy_ipc": "POCSO Act 2012",
        "confidence_weight": 5,
        "keywords_en": [
            "child abuse", "minor abused", "minor raped", "child raped",
            "boy abused", "girl abused", "POCSO", "sexually abused child",
            "child sexual abuse",
        ],
        "keywords_hi": ["bacche ke saath", "naabalig ke saath", "bacchon ka shoshan"],
        "doc_checklist": [
            "MLC at government hospital — IMMEDIATELY",
            "Contact: Childline 1098 (24×7 FREE)",
            "NALSA 15100 for free legal aid",
            "Do NOT delay — time is critical",
        ],
        "safety_flag": "POCSO",
    },
    # ── 14. Cruelty by Husband / DV ─────────────────────────────────────────
    {
        "bns_section": "85",
        "bns_heading": "Husband or relative of husband subjecting woman to cruelty",
        "legacy_ipc": "IPC 498A",
        "confidence_weight": 3,
        "keywords_en": [
            "husband beat", "husband hit", "dowry", "in-laws harassment",
            "domestic violence", "dowry demand", "husband cruelty",
            "mental torture by husband", "forced out of house",
        ],
        "keywords_hi": [
            "pati ne maara", "dahej", "sasural wale", "ghar se nikala",
            "gharelu hinsa", "dahej ke liye tang",
        ],
        "doc_checklist": [
            "MLC if physically injured",
            "Marriage certificate",
            "Dowry demand evidence (messages / letters)",
            "Contact: 181 Women Helpline / NALSA 15100",
        ],
        "safety_flag": "DV",
    },
    # ── 15. Dowry Death ─────────────────────────────────────────────────────
    {
        "bns_section": "80",
        "bns_heading": "Dowry death",
        "legacy_ipc": "IPC 304B",
        "confidence_weight": 5,
        "keywords_en": [
            "dowry death", "burnt by in-laws", "died due to dowry",
            "bride burning", "killed for dowry",
        ],
        "keywords_hi": ["dahej hatya", "dahej maut", "dahej mein jalaaya"],
        "doc_checklist": [
            "Post-mortem report",
            "Death certificate",
            "Marriage certificate",
            "Dowry demand / harassment evidence",
            "NALSA 15100 / Women Helpline 181",
        ],
        "safety_flag": "DV",
    },
    # ── 16. Human Trafficking ───────────────────────────────────────────────
    {
        "bns_section": "143",
        "bns_heading": "Trafficking of persons",
        "legacy_ipc": "IPC 370A",
        "confidence_weight": 5,
        "keywords_en": [
            "trafficking", "trafficked", "sold", "forced into prostitution",
            "forced labour", "bonded labour", "recruited and deceived",
        ],
        "keywords_hi": ["manav trafficking", "bechi", "jabardasti kaam", "dhandha"],
        "doc_checklist": [
            "Call: Childline 1098 / iNDIA anti-trafficking helpline 1800-419-8588",
            "Contact local NGO / One Stop Centre",
            "Rescue and medical examination first",
        ],
        "safety_flag": "SEXUAL",
    },
    # ── 17. Robbery ─────────────────────────────────────────────────────────
    {
        "bns_section": "309",
        "bns_heading": "Robbery",
        "legacy_ipc": "IPC 390",
        "confidence_weight": 3,
        "keywords_en": [
            "rob", "robbed", "robbery", "snatched at gunpoint",
            "loot", "looted", "mugged", "chain snatching", "forced to give",
        ],
        "keywords_hi": ["loot", "loota", "chain lunchi", "gunpoint pe", "chheen liya"],
        "doc_checklist": [
            "List of items taken with value",
            "MLC if injured during robbery",
            "CCTV footage request",
        ],
        "safety_flag": None,
    },
    # ── 18. Dacoity ─────────────────────────────────────────────────────────
    {
        "bns_section": "310",
        "bns_heading": "Dacoity",
        "legacy_ipc": "IPC 395",
        "confidence_weight": 4,
        "keywords_en": [
            "dacoity", "dacoit", "gang robbery", "five or more persons robbed",
            "gang looted",
        ],
        "keywords_hi": ["dakaiti", "daku", "gang ne loota"],
        "doc_checklist": [
            "List of all stolen property",
            "MLC if injured",
            "Eye-witness statements",
        ],
        "safety_flag": None,
    },
    # ── 19. Murder ──────────────────────────────────────────────────────────
    {
        "bns_section": "101",
        "bns_heading": "Culpable homicide amounting to murder",
        "legacy_ipc": "IPC 302",
        "confidence_weight": 4,
        "keywords_en": [
            "killed", "kill", "murder", "murdered", "dead", "died", "death",
            "lost their life", "culpable homicide",
        ],
        "keywords_hi": ["mara diya", "hatyaa", "qatl", "maut", "mar gaya"],
        "doc_checklist": [
            "Post-mortem report",
            "Death certificate",
            "Witness statements (eye-witnesses)",
        ],
        "safety_flag": None,
    },
    # ── 20. Attempt to Murder ───────────────────────────────────────────────
    {
        "bns_section": "109",
        "bns_heading": "Attempt to commit murder",
        "legacy_ipc": "IPC 307",
        "confidence_weight": 4,
        "keywords_en": [
            "tried to kill", "attempt to murder", "attempted murder",
            "tried to stab", "tried to shoot", "tried to poison",
        ],
        "keywords_hi": ["maarne ki koshish", "jaan lene ki koshish"],
        "doc_checklist": [
            "MLC",
            "X-ray / scan reports if injured",
            "Weapon photograph / actual (safe to preserve)",
        ],
        "safety_flag": None,
    },
    # ── 21. Death by Negligence ─────────────────────────────────────────────
    {
        "bns_section": "106",
        "bns_heading": "Causing death by negligence",
        "legacy_ipc": "IPC 304A",
        "confidence_weight": 3,
        "keywords_en": [
            "died in accident", "killed in accident", "road accident death",
            "medical negligence death", "negligently killed", "hit and run death",
        ],
        "keywords_hi": ["accident mein mara", "laparwahi se mara", "doctor ki laparwahi"],
        "doc_checklist": [
            "Post-mortem report",
            "FIR at nearest police station",
            "Vehicle details (accident)",
            "Hospital records (medical negligence)",
        ],
        "safety_flag": None,
    },
    # ── 22. Rash / Negligent Driving ────────────────────────────────────────
    {
        "bns_section": "281",
        "bns_heading": "Rash driving or riding on a public way",
        "legacy_ipc": "IPC 279",
        "confidence_weight": 3,
        "keywords_en": [
            "rash driving", "negligent driving", "road accident", "car accident",
            "bike accident", "knocked down", "hit and run", "drunk driving",
            "over-speed",
        ],
        "keywords_hi": [
            "sadak durghatna", "accident", "gaadi ne mara", "drunk drive",
            "tez gaadi",
        ],
        "doc_checklist": [
            "MLC if injured",
            "Vehicle registration and insurance of offending vehicle",
            "CCTV footage / dashcam",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── 23. Kidnapping / Abduction ──────────────────────────────────────────
    {
        "bns_section": "140",
        "bns_heading": "Kidnapping or abducting in order to murder",
        "legacy_ipc": "IPC 364",
        "confidence_weight": 4,
        "keywords_en": [
            "kidnap", "kidnapped", "abduct", "abducted",
            "taken away by force", "missing child", "child not returned",
        ],
        "keywords_hi": ["apaharan", "kidnap", "uthaake le gaye", "bacha gum hai"],
        "doc_checklist": [
            "Recent photograph of victim",
            "Last known location and time",
            "Contact: Childline 1098 if child involved",
        ],
        "safety_flag": None,
    },
    # ── 24. Wrongful Restraint ──────────────────────────────────────────────
    {
        "bns_section": "126",
        "bns_heading": "Wrongful restraint",
        "legacy_ipc": "IPC 341",
        "confidence_weight": 2,
        "keywords_en": [
            "blocked my way", "obstructed", "prevented me from leaving",
            "stopped me", "not allowed to go",
        ],
        "keywords_hi": ["rokha", "jaane nahi diya", "rasta band kiya"],
        "doc_checklist": ["Witness statements", "CCTV footage if available"],
        "safety_flag": None,
    },
    # ── 25. Wrongful Confinement ────────────────────────────────────────────
    {
        "bns_section": "127",
        "bns_heading": "Wrongful confinement",
        "legacy_ipc": "IPC 342",
        "confidence_weight": 3,
        "keywords_en": [
            "locked me in", "confined", "imprisoned illegally", "kept me captive",
            "not allowed to leave", "illegally detained",
        ],
        "keywords_hi": ["band kar diya", "qayd kiya", "nikalne nahi diya"],
        "doc_checklist": [
            "Medical examination if injured",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── 26. Extortion ───────────────────────────────────────────────────────
    {
        "bns_section": "308",
        "bns_heading": "Extortion",
        "legacy_ipc": "IPC 384",
        "confidence_weight": 3,
        "keywords_en": [
            "extortion", "extort", "demanded money with threat",
            "pay or else", "hafta", "protection money", "forced to pay",
        ],
        "keywords_hi": ["vasuli", "hafta", "ransom", "fidya"],
        "doc_checklist": [
            "Screenshots of extortion messages",
            "Bank records if payment made",
        ],
        "safety_flag": None,
    },
    # ── 27. Criminal Trespass ───────────────────────────────────────────────
    {
        "bns_section": "329",
        "bns_heading": "Criminal trespass",
        "legacy_ipc": "IPC 447",
        "confidence_weight": 2,
        "keywords_en": [
            "trespass", "trespassing", "entered without permission", "broke into",
            "forcibly entered", "illegal entry", "thrown out", "dispossessed",
        ],
        "keywords_hi": ["ghar mein ghus gaya", "zor se andar aaya", "kabza", "ghuspaith"],
        "doc_checklist": [
            "Ownership documents (sale deed / rent agreement)",
            "Photographs of illegal entry",
        ],
        "safety_flag": None,
    },
    # ── 28. Mischief / Property Damage ──────────────────────────────────────
    {
        "bns_section": "320",
        "bns_heading": "Mischief",
        "legacy_ipc": "IPC 425",
        "confidence_weight": 2,
        "keywords_en": [
            "damaged property", "destroyed property", "vandalism",
            "broke my vehicle", "smashed", "property damaged",
        ],
        "keywords_hi": ["sampatti barbad ki", "todaphod", "gaadi toodi"],
        "doc_checklist": [
            "Photographs of damage",
            "Estimate of repair cost",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── 29. Arson / Mischief by Fire ────────────────────────────────────────
    {
        "bns_section": "324",
        "bns_heading": "Mischief by fire or explosive substance",
        "legacy_ipc": "IPC 436",
        "confidence_weight": 4,
        "keywords_en": [
            "arson", "set fire", "burnt my property", "fire to house",
            "set fire to vehicle", "explosion",
        ],
        "keywords_hi": ["aag lagayi", "makan jalaya", "gaadi jalaya"],
        "doc_checklist": [
            "Fire brigade report",
            "Photographs of damage",
            "Insurance documents",
        ],
        "safety_flag": None,
    },
    # ── 30. Forgery ─────────────────────────────────────────────────────────
    {
        "bns_section": "334",
        "bns_heading": "Forgery",
        "legacy_ipc": "IPC 465",
        "confidence_weight": 2,
        "keywords_en": [
            "forged", "forgery", "fake document", "fake signature",
            "tampered document", "fake certificate", "counterfeit",
        ],
        "keywords_hi": ["nakli dastavez", "jali hastakshar", "nakli certificate"],
        "doc_checklist": [
            "Original document (if available)",
            "Forged document (photocopy)",
            "Expert opinion from document examiner",
        ],
        "safety_flag": None,
    },
    # ── 31. Forgery for Fraud ───────────────────────────────────────────────
    {
        "bns_section": "335",
        "bns_heading": "Forgery for purpose of cheating",
        "legacy_ipc": "IPC 468",
        "confidence_weight": 3,
        "keywords_en": [
            "forged to defraud", "forged documents for loan",
            "forged property papers", "fake registration",
        ],
        "keywords_hi": ["nakli kagaz se thaga", "nakli property papers"],
        "doc_checklist": [
            "Authentic originals for comparison",
            "Bank / registrar records",
        ],
        "safety_flag": None,
    },
    # ── 32. Cheque Bounce ───────────────────────────────────────────────────
    {
        "bns_section": "NI_138",
        "bns_heading": "Dishonour of cheque (NI Act Section 138)",
        "legacy_ipc": "NI Act 138",
        "confidence_weight": 3,
        "keywords_en": [
            "cheque bounce", "cheque bounced", "dishonoured cheque",
            "cheque not cleared", "returned cheque", "insufficient funds cheque",
        ],
        "keywords_hi": ["cheque bounce", "cheque wapas aaya", "paisa nahi aaya cheque se"],
        "doc_checklist": [
            "Original bounced cheque",
            "Bank return memo",
            "Legal demand notice (send within 30 days of bounce)",
            "Proof of debt (agreement / invoice)",
        ],
        "safety_flag": None,
    },
    # ── 33. Defamation ──────────────────────────────────────────────────────
    {
        "bns_section": "356",
        "bns_heading": "Defamation",
        "legacy_ipc": "IPC 499",
        "confidence_weight": 2,
        "keywords_en": [
            "defamation", "defamed", "false statements", "spreading lies",
            "ruined my reputation", "false rumours", "slandered",
        ],
        "keywords_hi": ["badnaam kiya", "jhooth failaya", "izzat kharab ki"],
        "doc_checklist": [
            "Screenshots of defamatory posts / statements",
            "Witnesses",
            "Evidence that statements are false",
        ],
        "safety_flag": None,
    },
    # ── 34. Intentional Insult ──────────────────────────────────────────────
    {
        "bns_section": "352",
        "bns_heading": "Intentional insult to provoke breach of peace",
        "legacy_ipc": "IPC 504",
        "confidence_weight": 2,
        "keywords_en": [
            "insult", "abused verbally", "provoked a fight", "public humiliation",
        ],
        "keywords_hi": ["gali di", "beizzat kiya", "ladte ke liye provoke kiya"],
        "doc_checklist": ["Witness statements", "Audio/video recording if available"],
        "safety_flag": None,
    },
    # ── 35. Rioting ─────────────────────────────────────────────────────────
    {
        "bns_section": "191",
        "bns_heading": "Being a member of unlawful assembly with rioting",
        "legacy_ipc": "IPC 147",
        "confidence_weight": 3,
        "keywords_en": [
            "riot", "rioting", "mob violence", "group attacked", "communal violence",
            "violent protest",
        ],
        "keywords_hi": ["danga", "bheed ne mara", "mob", "fasaad"],
        "doc_checklist": [
            "Photographs / video of incident",
            "MLC if injured",
            "Witness statements",
        ],
        "safety_flag": None,
    },
    # ── 36. Unlawful Assembly ───────────────────────────────────────────────
    {
        "bns_section": "190",
        "bns_heading": "Every member of unlawful assembly guilty",
        "legacy_ipc": "IPC 141",
        "confidence_weight": 2,
        "keywords_en": [
            "unlawful assembly", "gathered illegally", "refused to disperse",
            "section 144", "prohibitory orders violated",
        ],
        "keywords_hi": ["dhara 144", "gayr-qanooni julsoos"],
        "doc_checklist": ["Photographs", "Police order copy (if 144)"],
        "safety_flag": None,
    },
    # ── 37. Affray ──────────────────────────────────────────────────────────
    {
        "bns_section": "192",
        "bns_heading": "Affray",
        "legacy_ipc": "IPC 160",
        "confidence_weight": 2,
        "keywords_en": [
            "fight in public", "brawl", "public disturbance", "public fight",
        ],
        "keywords_hi": ["sarak par ladai", "public mein jhagda"],
        "doc_checklist": ["Witness statements", "CCTV footage"],
        "safety_flag": None,
    },
    # ── 38. Act Endangering Life ────────────────────────────────────────────
    {
        "bns_section": "125",
        "bns_heading": "Act endangering life or personal safety",
        "legacy_ipc": "IPC 336",
        "confidence_weight": 2,
        "keywords_en": [
            "endangered my life", "reckless act", "unsafe construction",
            "exposed to danger",
        ],
        "keywords_hi": ["jaan khatre mein daali", "laparwahi se nuqsaan"],
        "doc_checklist": ["Photographs of hazard", "Medical records if injured"],
        "safety_flag": None,
    },
    # ── 39. Public Nuisance ─────────────────────────────────────────────────
    {
        "bns_section": "290",
        "bns_heading": "Punishment for public nuisance",
        "legacy_ipc": "IPC 290",
        "confidence_weight": 1,
        "keywords_en": [
            "public nuisance", "blocking road", "garbage dumping",
            "illegal construction blocking", "noise pollution",
        ],
        "keywords_hi": ["sarak rokna", "gandagi failana", "najaiz construction"],
        "doc_checklist": ["Photographs", "Municipal complaint record"],
        "safety_flag": None,
    },
    # ── 40. Public Mischief / False Alarm ───────────────────────────────────
    {
        "bns_section": "353",
        "bns_heading": "Statements conducive to public mischief",
        "legacy_ipc": "IPC 505",
        "confidence_weight": 2,
        "keywords_en": [
            "false rumour", "inciting violence", "spreading panic",
            "communal hate speech", "religious incitement",
        ],
        "keywords_hi": ["jhooti aman ki", "fasaad failana", "danga bharkana"],
        "doc_checklist": [
            "Screenshots / recordings of statements",
            "Platform / media complaint",
        ],
        "safety_flag": None,
    },
]

# ---------------------------------------------------------------------------
# Safety-branch patterns (independent of classifier)
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
        r"\bbachch.{0,20}\bsexual\b", r"\b1098\b",
    ],
}


def detect_safety_flags(text: str) -> list[str]:
    low = text.lower()
    flags: list[str] = []
    for flag, patterns in _SAFETY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, low):
                flags.append(flag)
                break
    return flags


# ---------------------------------------------------------------------------
# Keyword-based classifier (sync, fast fallback)
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
    return "medium" if ratio >= 0.6 else "low"


def _build_candidate(off: OffenceDef, score: int, max_score: int) -> dict | None:
    """Build a candidate dict; returns None if section is dead law."""
    if is_dead_law("Bharatiya Nyaya Sanhita, 2023", off["bns_section"]):
        return None
    if is_dead_law("POCSO", off["bns_section"]):
        return None
    return {
        "bns_section": off["bns_section"],
        "bns_heading": off["bns_heading"],
        "legacy_ipc": off["legacy_ipc"],
        "confidence": _confidence_label(score, max_score),
        "doc_checklist": off["doc_checklist"],
        "safety_flag": off["safety_flag"],
        "dead_law": False,
    }


def classify_incident(narrative: str, top_n: int = 3) -> dict:
    """Keyword-only sync classification (fallback path).
    Only returns 'medium' confidence candidates — 'low' confidence sections
    are never surfaced on a document the user may hand to police.
    """
    text_lower = narrative.lower()
    scored = [(s, o) for o in OFFENCES if (s := _score(text_lower, o)) > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    max_score = scored[0][0] if scored else 1
    candidates = [
        c for s, o in scored[:top_n]
        if (c := _build_candidate(o, s, max_score)) is not None
        and c["confidence"] == "medium"   # Bug-fix: drop low-confidence from draft
    ]
    safety_flags = detect_safety_flags(narrative)
    for c in candidates:
        if c["safety_flag"] and c["safety_flag"] not in safety_flags:
            safety_flags.append(c["safety_flag"])
    return {
        "candidates": candidates,
        "safety_flags": safety_flags,
        "disclaimer": (
            "\u26a0\ufe0f SUGGESTED SECTIONS ONLY \u2014 These BNS sections are a starting point "
            "based on your description. The police officer will determine the applicable "
            "sections after investigation. This is NOT a registered FIR and NOT legal advice."
        ),
    }


# ---------------------------------------------------------------------------
# LLM-assisted classifier (async, primary path)
# ---------------------------------------------------------------------------

_OFFENCE_QUICK_REF = "\n".join(
    f"- {o['bns_section']}: {o['bns_heading']} (formerly {o['legacy_ipc']})"
    for o in OFFENCES
)

_LLM_SYSTEM = (
    "You are a legal section classifier for Indian criminal law (BNS 2023, BNSS 2023, BSA 2023).\n"
    "Given an incident narrative, identify up to 3 applicable BNS sections.\n"
    "Rules:\n"
    "1. UNDER-CLAIM \u2014 only include sections you are confident about.\n"
    "2. Max 3 sections, ordered by relevance (most likely first).\n"
    "3. Confidence: ONLY 'medium' or 'low'. Never 'high'.\n"
    "4. Safety flags: set 'DV' for domestic violence/dowry, 'SEXUAL' for sexual assault, "
    "'POCSO' for child sexual abuse.\n"
    "5. Return ONLY valid JSON \u2014 no markdown, no extra text.\n"
    "6. Never include repealed/struck-down IPC sections. Use BNS equivalents only.\n"
    "\nRESPONSE FORMAT (strict):\n"
    '{"sections":[{"bns":"303","reason":"one sentence","confidence":"medium"}],'
    '"safety_flags":[]}'
)


async def classify_incident_llm(narrative: str, llm_key: str) -> dict | None:
    """
    LLM-assisted classification using Claude Sonnet.
    Returns parsed result dict or None if LLM call fails.
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        session_id = f"fir-classify-{uuid.uuid4()}"
        chat = (
            LlmChat(
                api_key=llm_key,
                session_id=session_id,
                system_message=_LLM_SYSTEM,
            )
            .with_model("anthropic", "claude-sonnet-4-6")
            .with_params(max_tokens=512)
        )
        prompt = (
            f"NARRATIVE:\n{narrative}\n\n"
            f"AVAILABLE BNS SECTIONS:\n{_OFFENCE_QUICK_REF}\n\n"
            "Classify the narrative. Return JSON only."
        )
        response = await chat.send_message(UserMessage(text=prompt))
        raw = response.strip()
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```[^\n]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw.strip())
        parsed = json.loads(raw)
        return parsed
    except Exception:
        return None


async def classify_incident_hybrid(narrative: str, llm_key: str, top_n: int = 3) -> dict:
    """
    Hybrid classifier: LLM primary + keyword fallback/supplement.
    Always returns the same dict shape as classify_incident().
    """
    # 1. Run keyword classifier first (instant, always available)
    kw_result = classify_incident(narrative, top_n)

    # 2. Try LLM classifier
    llm_raw = await classify_incident_llm(narrative, llm_key)

    if not llm_raw:
        # LLM failed — return keyword result
        return kw_result

    # 3. Build candidates from LLM result
    llm_bns_set: set[str] = set()
    merged_candidates: list[dict] = []

    offence_map = {o["bns_section"]: o for o in OFFENCES}

    for item in (llm_raw.get("sections") or [])[:top_n]:
        bns = str(item.get("bns", "")).strip()
        if not bns:
            continue
        if is_dead_law("Bharatiya Nyaya Sanhita, 2023", bns):
            continue
        # Bug-fix: clamp to 'medium' or drop — 'low' confidence never on printed draft
        raw_conf = item.get("confidence", "low")
        confidence = raw_conf if raw_conf in ("medium", "low") else "low"
        if confidence == "low":
            continue  # suppress low-confidence LLM suggestions from the document
        off = offence_map.get(bns)
        candidate = {
            "bns_section": bns,
            "bns_heading": off["bns_heading"] if off else item.get("reason", "")[:60],
            "legacy_ipc": off["legacy_ipc"] if off else "",
            "confidence": confidence,
            "doc_checklist": off["doc_checklist"] if off else [],
            "safety_flag": off["safety_flag"] if off else None,
            "dead_law": False,
        }
        merged_candidates.append(candidate)
        llm_bns_set.add(bns)

    # 4. Supplement with keyword candidates not already in LLM result
    for c in kw_result["candidates"]:
        if c["bns_section"] not in llm_bns_set and len(merged_candidates) < top_n:
            merged_candidates.append(c)

    # 5. Merge safety flags from both sources
    llm_flags: list[str] = llm_raw.get("safety_flags") or []
    safety_flags = list(dict.fromkeys(kw_result["safety_flags"] + llm_flags))
    for c in merged_candidates:
        if c["safety_flag"] and c["safety_flag"] not in safety_flags:
            safety_flags.append(c["safety_flag"])

    return {
        "candidates": merged_candidates[:top_n],
        "safety_flags": safety_flags,
        "disclaimer": kw_result["disclaimer"],
    }
