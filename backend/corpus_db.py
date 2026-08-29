"""
corpus_db.py  —  MongoDB-backed legal-section retrieval for DHARA.

Architecture
------------
Two retrieval paths:

1. Exact section lookup (preferred when the user cites a specific section/article
   number).  Uses the act_name + section_number compound index — sub-millisecond.

2. Situational full-text search (when the user describes a problem).
   Uses the Atlas-compatible $text index on section_heading (w=10) + act_name
   (w=5) + section_text (w=1).  Optionally boosts results from the user's
   state jurisdiction to the top of the list.

Safety guards  (code, not prompts — non-negotiable per spec)
-------------------------------------------------------------
G1  Dead-law guard — if is_dead_law is True, prepend serve_warning *in the
    user's language* before any statutory text.  Dead sections are EXCLUDED
    from situational search but CAN appear in exact lookups so the app can
    explain that the section has been struck/omitted.

G2  Judicial-invalidation join — after retrieving any section, look it up in
    the judicial_invalidations collection.  If a record exists AND
    status != "UPHELD", prepend flag.user_warning to the answer.
    Records with status "UPHELD" are negative entries — suppress the warning.

G3  Badge logic —
      verify_tier == 1  AND  verified_by is not None/empty
          → badge = "Advocate Verified"  (gold)
      everything else
          → badge = "Sourced from Government of India"  (standard)

Integration note
----------------
This module is *additive*.  The caller should:
  1. Try corpus_db first.
  2. If it returns zero results, fall back to the Python corpus (corpus.py).
  3. If it returns results, use them — they carry live government-source text.

Returned dict shape (per result)
---------------------------------
{
  "act_name": str,
  "section_number": str,
  "section_heading": str,
  "section_text": str,        # verbatim government text
  "jurisdiction": str,        # "CENTRAL" | state full name
  "source_url": str,
  "verify_tier": int,         # 1 or 2
  "badge": str,               # human-readable badge label
  "is_dead_law": bool,
  "dead_warning": str|None,   # serve_warning value or None
  "judicial_flag": str|None,  # user_warning from judicial_invalidations or None
  "_score": float,            # text-search relevance score (0 for exact lookups)
}
"""

from __future__ import annotations

import re
from motor.motor_asyncio import AsyncIOMotorDatabase

# ── State code → corpus jurisdiction string ──────────────────────────────────
# The corpus `jurisdiction` field uses full English state names (as harvested
# from indiacode.gov.in).  User profiles store the 2-letter ISO-like state
# code (same as states.py).  This mapping bridges the two.
#
# States that ARE in the corpus (have section text):
#   MH, UP, RJ, JK, ML, TG, TN, JH, UK, MP, AN, KL
# All other state codes map to their official full name — even if no corpus
# sections exist yet, the mapping lets the API return a proper "not available"
# response instead of a silent failure.
STATE_CODE_TO_JURISDICTION: dict[str, str] = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DH": "Dadra and Nagar Haveli and Daman and Diu",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TG": "Telangana",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
}

# ── Section-number extraction ─────────────────────────────────────────────────
# Matches patterns like "Section 138", "s.138", "Art. 21", "Article 21A",
# "s 66A", "sec 9", etc.  Returns the bare number string ("138", "21A", "66A").
_SEC_RE = re.compile(
    r"(?:section|sections|sec|s\.|art(?:icle)?\.?)\s*(\d+[A-Za-z]{0,3})",
    re.IGNORECASE,
)
# Act-name hints extracted from the query to improve exact lookup accuracy.
_ACT_HINTS: dict[str, re.Pattern] = {
    "Bharatiya Nyaya Sanhita": re.compile(r"bns|nyaya\s+sanhita", re.I),
    "Bharatiya Nagarik Suraksha Sanhita": re.compile(r"bnss|nagarik\s+suraksha", re.I),
    "Bharatiya Sakshya Adhiniyam": re.compile(r"bsa|sakshya", re.I),
    "Information Technology": re.compile(r"\bit\s+act\b|information\s+technology", re.I),
    "Negotiable Instruments": re.compile(r"\bni\s+act\b|negotiable\s+instruments", re.I),
    "Indian Penal Code": re.compile(r"\bipc\b|indian\s+penal\s+code", re.I),
    "Code of Criminal Procedure": re.compile(r"\bcrpc\b|criminal\s+procedure", re.I),
    "Constitution of India": re.compile(r"constitution|article\s+\d", re.I),
    "Motor Vehicles": re.compile(r"motor\s+vehicles|mvact|mva\b", re.I),
    "Consumer Protection": re.compile(r"consumer\s+protection|consumer\s+court", re.I),
    "Protection of Women from Domestic Violence": re.compile(r"domestic\s+violence", re.I),
    "Right to Information": re.compile(r"\brti\b|right\s+to\s+information", re.I),
    "Labour Code|Code on Wages": re.compile(r"wages\s+code|code\s+on\s+wages", re.I),
    "Insolvency and Bankruptcy": re.compile(r"\bibc\b|insolvency.*bankruptcy", re.I),
}


def _badge(doc: dict) -> str:
    """G3 — Badge logic (code, not prompts)."""
    if doc.get("verify_tier") == 1 and doc.get("verified_by"):
        return "Advocate Verified"
    return "Sourced from Government of India"


def _dead_warning(doc: dict) -> str | None:
    """G1 — Return the serve_warning text if section is dead law, else None."""
    if not doc.get("is_dead_law"):
        return None
    return doc.get(
        "serve_warning",
        "⚠️ This section has been omitted or repealed. "
        "The text below is retained for historical reference and is NOT current law.",
    )


async def _judicial_flag(db: AsyncIOMotorDatabase, act_name: str, section_number: str) -> str | None:
    """G2 — Look up judicial_invalidations.  Return user_warning if flagged, else None."""
    rec = await db.judicial_invalidations.find_one(
        {"act_name": act_name, "section_number": section_number}
    )
    if not rec:
        return None
    # UPHELD entries are negative entries — they exist to *prevent* false warnings.
    if (rec.get("status") or "").upper() == "UPHELD":
        return None
    return rec.get("user_warning") or f"⚠️ This provision has been subject to judicial proceedings. Please verify current status with an advocate."


def _shape(doc: dict, score: float, jflag: str | None) -> dict:
    """Convert a raw MongoDB document to the standard result dict."""
    return {
        "act_name": doc.get("act_name", ""),
        "section_number": doc.get("section_number", ""),
        "section_heading": doc.get("section_heading", ""),
        "section_text": doc.get("section_text", ""),
        "jurisdiction": doc.get("jurisdiction", "CENTRAL"),
        "source_url": doc.get("source_url", ""),
        "verify_tier": doc.get("verify_tier", 2),
        "badge": _badge(doc),
        "is_dead_law": bool(doc.get("is_dead_law", False)),
        "dead_warning": _dead_warning(doc),
        "judicial_flag": jflag,
        "_score": score,
        # Extra fields useful for display
        "ministry": doc.get("ministry", ""),
        "act_year": doc.get("act_year"),
        "act_id": doc.get("act_id", ""),
        "dead_law_reason": doc.get("dead_law_reason"),
    }


async def lookup_section(
    db: AsyncIOMotorDatabase,
    section_number: str,
    act_hint: str | None = None,
) -> dict | None:
    """Exact section lookup by section_number + optional act name hint.

    Uses the ix_actname_section compound index for O(log n) lookup.
    Includes dead sections (so the pipeline can display the dead-law warning).

    Returns None if no match found.
    """
    query: dict = {"section_number": section_number}
    if act_hint:
        query["act_name"] = re.compile(re.escape(act_hint[:60]), re.IGNORECASE)

    doc = await db.legal_sections.find_one(query)
    if not doc:
        return None

    jflag = await _judicial_flag(db, doc.get("act_name", ""), section_number)
    return _shape(doc, 0.0, jflag)


async def retrieve_db(
    db: AsyncIOMotorDatabase,
    question: str,
    state_code: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Situational full-text search against the legal_sections corpus.

    Priority ordering:
      1. Exact section lookup (if question cites a section number + act hint).
      2. Full-text search scoped to user's state jurisdiction (if set).
      3. Full-text search on CENTRAL jurisdiction.

    Dead sections are EXCLUDED from situational search results (G1).
    Results from step 2 are prepended to results from step 3, deduped by _id.

    Returns up to `limit` result dicts (may be fewer if corpus is sparse).
    """
    results: list[dict] = []
    seen_ids: set[str] = set()

    # ── 0. Derive jurisdiction string from state code ─────────────────────────
    state_jurisdiction: str | None = None
    if state_code:
        state_jurisdiction = STATE_CODE_TO_JURISDICTION.get(state_code.upper())

    # ── 1. Attempt exact section lookup first ─────────────────────────────────
    sec_match = _SEC_RE.search(question)
    if sec_match:
        sec_num = sec_match.group(1).upper()
        act_hint: str | None = None
        for hint_name, pattern in _ACT_HINTS.items():
            if pattern.search(question):
                act_hint = hint_name
                break

        exact = await lookup_section(db, sec_num, act_hint)
        if exact:
            seen_ids.add(exact["act_id"] + "|" + exact["section_number"])
            results.append(exact)

    # ── 2. Full-text search — state jurisdiction (if set) ────────────────────
    if state_jurisdiction:
        try:
            cursor = db.legal_sections.find(
                {
                    "$text": {"$search": question},
                    "jurisdiction": state_jurisdiction,
                    "is_dead_law": False,
                },
                {
                    "score": {"$meta": "textScore"},
                    "act_name": 1, "section_number": 1, "section_heading": 1,
                    "section_text": 1, "source_url": 1, "verify_tier": 1,
                    "verified_by": 1, "is_dead_law": 1, "dead_law_reason": 1,
                    "serve_warning": 1, "jurisdiction": 1, "ministry": 1,
                    "act_year": 1, "act_id": 1,
                },
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)

            async for doc in cursor:
                key = doc.get("act_id", "") + "|" + doc.get("section_number", "")
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                score = doc.get("score", 0.0)
                jflag = await _judicial_flag(
                    db, doc.get("act_name", ""), doc.get("section_number", "")
                )
                results.append(_shape(doc, float(score), jflag))
        except Exception:
            pass  # Corpus may not have this jurisdiction yet — fall through

    # ── 3. Full-text search — CENTRAL jurisdiction ────────────────────────────
    remaining = limit - len(results)
    if remaining > 0:
        try:
            cursor = db.legal_sections.find(
                {
                    "$text": {"$search": question},
                    "jurisdiction": "CENTRAL",
                    "is_dead_law": False,
                },
                {
                    "score": {"$meta": "textScore"},
                    "act_name": 1, "section_number": 1, "section_heading": 1,
                    "section_text": 1, "source_url": 1, "verify_tier": 1,
                    "verified_by": 1, "is_dead_law": 1, "dead_law_reason": 1,
                    "serve_warning": 1, "jurisdiction": 1, "ministry": 1,
                    "act_year": 1, "act_id": 1,
                },
            ).sort([("score", {"$meta": "textScore"})]).limit(remaining * 2)

            async for doc in cursor:
                if len(results) >= limit:
                    break
                key = doc.get("act_id", "") + "|" + doc.get("section_number", "")
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                score = doc.get("score", 0.0)
                jflag = await _judicial_flag(
                    db, doc.get("act_name", ""), doc.get("section_number", "")
                )
                results.append(_shape(doc, float(score), jflag))
        except Exception:
            pass

    return results


async def lookup_act_sections(
    db: AsyncIOMotorDatabase,
    act_id: str,
    limit: int = 50,
) -> list[dict]:
    """Browse all sections of an Act in statutory order (Task 4 pattern 3)."""
    cursor = db.legal_sections.find(
        {"act_id": act_id},
    ).sort([("section_num_int", 1), ("section_num_suffix", 1)]).limit(limit)

    results = []
    async for doc in cursor:
        jflag = await _judicial_flag(
            db, doc.get("act_name", ""), doc.get("section_number", "")
        )
        results.append(_shape(doc, 0.0, jflag))
    return results
