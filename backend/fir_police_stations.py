"""
FIR Jurisdiction Finder — Maharashtra Pilot

Matches a voice/text described location to a police station.
Primary input: free text (e.g. "Dadar, Mumbai" / "Pune Shivajinagar")
GPS is NOT required — location text is the primary path.

If no confident match: degrade gracefully with district + Zero FIR note.
Zero FIR right: A citizen may file an FIR at ANY police station regardless
of jurisdiction under Section 173(1) BNSS. The station MUST accept it and
forward it to the jurisdictional station.

Data source: Maharashtra Police / BPR&D public directory (pilot subset).
"""

from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# Police Station data — (locality_keywords, station_name, district, address)
# ---------------------------------------------------------------------------
# Format: {"aliases": [...lowercase tokens], "station": str, "district": str,
#          "address": str, "phone": str}

_PS_DATA = [
    # ── Mumbai ──────────────────────────────────────────────────────────
    {"aliases": ["marine lines", "churchgate", "marine drive"],
     "station": "Marine Lines Police Station", "district": "Mumbai City",
     "address": "Marine Lines, Mumbai - 400020", "phone": "022-22088200"},
    {"aliases": ["colaba", "nariman point"],
     "station": "Colaba Police Station", "district": "Mumbai City",
     "address": "Colaba Causeway, Mumbai - 400005", "phone": "022-22151284"},
    {"aliases": ["dadar", "dadar west", "dadar east", "shivaji park"],
     "station": "Dadar Police Station", "district": "Mumbai City",
     "address": "Dr Ambedkar Road, Dadar, Mumbai - 400014", "phone": "022-24154780"},
    {"aliases": ["bandra", "bandra west", "bandra east", "band stand"],
     "station": "Bandra Police Station", "district": "Mumbai Suburban",
     "address": "Turner Road, Bandra West, Mumbai - 400050", "phone": "022-26401213"},
    {"aliases": ["andheri", "andheri west", "andheri east"],
     "station": "Andheri Police Station", "district": "Mumbai Suburban",
     "address": "S V Road, Andheri West, Mumbai - 400058", "phone": "022-26248400"},
    {"aliases": ["borivali", "borivali west", "borivali east", "dahisar"],
     "station": "Borivali Police Station", "district": "Mumbai Suburban",
     "address": "MG Road, Borivali West, Mumbai - 400092", "phone": "022-28983801"},
    {"aliases": ["ghatkopar", "ghatkopar west", "ghatkopar east"],
     "station": "Ghatkopar Police Station", "district": "Mumbai Suburban",
     "address": "LBS Marg, Ghatkopar West, Mumbai - 400086", "phone": "022-25012505"},
    {"aliases": ["kurla", "kurla west"],
     "station": "Kurla Police Station", "district": "Mumbai Suburban",
     "address": "LBS Marg, Kurla West, Mumbai - 400070", "phone": "022-26502502"},
    {"aliases": ["dharavi", "sion"],
     "station": "Dharavi Police Station", "district": "Mumbai City",
     "address": "90 Feet Road, Dharavi, Mumbai - 400017", "phone": "022-24054008"},
    {"aliases": ["goregaon", "goregaon west", "goregaon east", "malad"],
     "station": "Goregaon Police Station", "district": "Mumbai Suburban",
     "address": "SV Road, Goregaon West, Mumbai - 400062", "phone": "022-28722200"},
    {"aliases": ["mulund", "mulund west", "mulund east"],
     "station": "Mulund Police Station", "district": "Mumbai Suburban",
     "address": "MG Road, Mulund West, Mumbai - 400080", "phone": "022-25673200"},
    {"aliases": ["thane", "thane west", "thane city", "thane east"],
     "station": "Thane City Police Station", "district": "Thane",
     "address": "Naupada, Thane - 400602", "phone": "022-25393000"},
    {"aliases": ["navi mumbai", "vashi", "nerul", "belapur", "airoli"],
     "station": "Vashi Police Station", "district": "Navi Mumbai",
     "address": "Vashi, Navi Mumbai - 400703", "phone": "022-27844600"},
    # ── Pune ────────────────────────────────────────────────────────────
    {"aliases": ["pune", "pune city", "shivajinagar", "deccan"],
     "station": "Shivajinagar Police Station", "district": "Pune",
     "address": "Shivajinagar, Pune - 411005", "phone": "020-25531000"},
    {"aliases": ["hadapsar", "magarpatta", "mundhwa"],
     "station": "Hadapsar Police Station", "district": "Pune",
     "address": "Hadapsar, Pune - 411028", "phone": "020-26823200"},
    {"aliases": ["kothrud", "karve nagar"],
     "station": "Kothrud Police Station", "district": "Pune",
     "address": "Kothrud, Pune - 411038", "phone": "020-25384300"},
    {"aliases": ["pimpri", "pimpri chinchwad", "chinchwad", "pcmc"],
     "station": "Pimpri Police Station", "district": "Pimpri-Chinchwad",
     "address": "Old Mumbai-Pune Road, Pimpri - 411018", "phone": "020-27422200"},
    {"aliases": ["wakad", "hinjewadi", "baner"],
     "station": "Hinjewadi Police Station", "district": "Pune",
     "address": "Hinjewadi, Pune - 411057", "phone": "020-22950100"},
    # ── Nagpur ──────────────────────────────────────────────────────────
    {"aliases": ["nagpur", "nagpur city", "civil lines nagpur", "sitabuldi"],
     "station": "Sitabuldi Police Station", "district": "Nagpur",
     "address": "Sitabuldi, Nagpur - 440012", "phone": "0712-2520500"},
    {"aliases": ["wardha road", "nagpur airport", "somalwada"],
     "station": "Somalwada Police Station", "district": "Nagpur",
     "address": "Somalwada, Nagpur - 440015", "phone": "0712-2681100"},
    # ── Nashik ──────────────────────────────────────────────────────────
    {"aliases": ["nashik", "nashik road", "deolali"],
     "station": "Nashik Road Police Station", "district": "Nashik",
     "address": "Nashik Road, Nashik - 422101", "phone": "0253-2465300"},
    # ── Aurangabad / Chhatrapati Sambhajinagar ───────────────────────────
    {"aliases": ["aurangabad", "sambhajinagar", "chhatrapati sambhajinagar", "cidco"],
     "station": "Cidco Police Station", "district": "Chhatrapati Sambhajinagar",
     "address": "CIDCO N-5, Aurangabad - 431003", "phone": "0240-2474700"},
    # ── Kolhapur ────────────────────────────────────────────────────────
    {"aliases": ["kolhapur", "ichalkaranji"],
     "station": "Kolhapur City Police Station", "district": "Kolhapur",
     "address": "Shahupuri, Kolhapur - 416001", "phone": "0231-2650100"},
    # ── Solapur ─────────────────────────────────────────────────────────
    {"aliases": ["solapur", "sholapur"],
     "station": "Solapur City Police Station", "district": "Solapur",
     "address": "Budhwar Peth, Solapur - 413002", "phone": "0217-2727200"},
    # ── Raigad / Panvel ─────────────────────────────────────────────────
    {"aliases": ["raigad", "panvel", "khopoli", "pen"],
     "station": "Panvel Police Station", "district": "Raigad",
     "address": "Panvel, Raigad - 410206", "phone": "022-27460100"},
    # ── Amravati ────────────────────────────────────────────────────────
    {"aliases": ["amravati", "amrawati"],
     "station": "Amravati City Police Station", "district": "Amravati",
     "address": "Rajkamal Chowk, Amravati - 444601", "phone": "0721-2662100"},
]


def _tokenise(text: str) -> list[str]:
    """Lower-case, split on non-alpha, return tokens of length >= 3."""
    return [t for t in re.split(r"[^a-z]+", text.lower()) if len(t) >= 3]


def find_police_station(location_text: str) -> dict:
    """
    Match location text to a Maharashtra police station.

    Returns
    -------
    {
        "matched": bool,
        "station": str | None,
        "district": str | None,
        "address": str | None,
        "phone": str | None,
        "zero_fir_note": str,
        "confidence": "high" | "low" | "none",
    }
    """
    tokens = set(_tokenise(location_text))
    best_match = None
    best_score = 0

    for ps in _PS_DATA:
        score = 0
        for alias in ps["aliases"]:
            alias_tokens = set(_tokenise(alias))
            overlap = len(tokens & alias_tokens)
            # Full alias match
            if alias.lower() in location_text.lower():
                score += 10
            elif overlap >= len(alias_tokens):
                score += 6
            elif overlap > 0:
                score += overlap
        if score > best_score:
            best_score = score
            best_match = ps

    zero_fir = (
        "📌 Zero FIR Right: Under Section 173(1) BNSS, you can file an FIR at "
        "ANY police station regardless of jurisdiction. The station MUST accept "
        "it and forward it to the jurisdictional station. Do not let anyone turn you away."
    )

    if best_match and best_score >= 6:
        return {
            "matched": True,
            "station": best_match["station"],
            "district": best_match["district"],
            "address": best_match["address"],
            "phone": best_match["phone"],
            "confidence": "high" if best_score >= 10 else "low",
            "zero_fir_note": zero_fir,
            "pilot_note": "Maharashtra pilot — 25 stations indexed. Confirm exact jurisdiction at the station.",
        }

    # Graceful degradation — try to identify district
    dist = None
    for ps in _PS_DATA:
        if ps["district"].lower() in location_text.lower():
            dist = ps["district"]
            best_match = ps
            break

    return {
        "matched": False,
        "station": best_match["station"] if best_match else None,
        "district": dist or "Maharashtra",
        "address": best_match["address"] if best_match else None,
        "phone": best_match["phone"] if best_match else "100 (Police Control Room)",
        "confidence": "none",
        "zero_fir_note": zero_fir,
        "pilot_note": (
            "Location not precisely matched in pilot database. "
            "Please confirm the exact police station at your nearest police outpost, "
            "or call 100 for assistance."
        ),
    }
