"""
FIR Jurisdiction Finder — Multi-State (v2)

Covered states: Maharashtra, Delhi, Karnataka, Tamil Nadu, West Bengal.
GPS is NOT required — location text is the primary path.

Zero FIR right: A citizen may file an FIR at ANY police station regardless
of jurisdiction under Section 173(1) BNSS. The station MUST accept it and
forward it to the jurisdictional station.

Data source: State Police / BPR&D public directory (pilot subset).
"""

from __future__ import annotations
import re

# Format: {"aliases": [...lowercase tokens], "station": str, "district": str,
#          "address": str, "phone": str, "state": str}

_PS_DATA = [
    # ════════════════════════════════════════════════════════════════════════
    # MAHARASHTRA
    # ════════════════════════════════════════════════════════════════════════
    # ── Mumbai ──────────────────────────────────────────────────────────────
    {"aliases": ["marine lines", "churchgate", "marine drive"],
     "station": "Marine Lines Police Station", "district": "Mumbai City", "state": "Maharashtra",
     "address": "Marine Lines, Mumbai - 400020", "phone": "022-22088200"},
    {"aliases": ["colaba", "nariman point"],
     "station": "Colaba Police Station", "district": "Mumbai City", "state": "Maharashtra",
     "address": "Colaba Causeway, Mumbai - 400005", "phone": "022-22151284"},
    {"aliases": ["dadar", "dadar west", "dadar east", "shivaji park"],
     "station": "Dadar Police Station", "district": "Mumbai City", "state": "Maharashtra",
     "address": "Dr Ambedkar Road, Dadar, Mumbai - 400014", "phone": "022-24154780"},
    {"aliases": ["bandra", "bandra west", "bandra east", "band stand"],
     "station": "Bandra Police Station", "district": "Mumbai Suburban", "state": "Maharashtra",
     "address": "Turner Road, Bandra West, Mumbai - 400050", "phone": "022-26401213"},
    {"aliases": ["andheri", "andheri west", "andheri east"],
     "station": "Andheri Police Station", "district": "Mumbai Suburban", "state": "Maharashtra",
     "address": "S V Road, Andheri West, Mumbai - 400058", "phone": "022-26248400"},
    {"aliases": ["borivali", "borivali west", "borivali east", "dahisar"],
     "station": "Borivali Police Station", "district": "Mumbai Suburban", "state": "Maharashtra",
     "address": "MG Road, Borivali West, Mumbai - 400092", "phone": "022-28983801"},
    {"aliases": ["ghatkopar", "ghatkopar west", "ghatkopar east"],
     "station": "Ghatkopar Police Station", "district": "Mumbai Suburban", "state": "Maharashtra",
     "address": "LBS Marg, Ghatkopar West, Mumbai - 400086", "phone": "022-25012505"},
    {"aliases": ["kurla", "kurla west"],
     "station": "Kurla Police Station", "district": "Mumbai Suburban", "state": "Maharashtra",
     "address": "LBS Marg, Kurla West, Mumbai - 400070", "phone": "022-26502502"},
    {"aliases": ["dharavi", "sion"],
     "station": "Dharavi Police Station", "district": "Mumbai City", "state": "Maharashtra",
     "address": "90 Feet Road, Dharavi, Mumbai - 400017", "phone": "022-24054008"},
    {"aliases": ["goregaon", "goregaon west", "goregaon east", "malad"],
     "station": "Goregaon Police Station", "district": "Mumbai Suburban", "state": "Maharashtra",
     "address": "SV Road, Goregaon West, Mumbai - 400062", "phone": "022-28722200"},
    {"aliases": ["mulund", "mulund west", "mulund east"],
     "station": "Mulund Police Station", "district": "Mumbai Suburban", "state": "Maharashtra",
     "address": "MG Road, Mulund West, Mumbai - 400080", "phone": "022-25673200"},
    {"aliases": ["thane", "thane west", "thane city", "thane east"],
     "station": "Thane City Police Station", "district": "Thane", "state": "Maharashtra",
     "address": "Naupada, Thane - 400602", "phone": "022-25393000"},
    {"aliases": ["navi mumbai", "vashi", "nerul", "belapur", "airoli"],
     "station": "Vashi Police Station", "district": "Navi Mumbai", "state": "Maharashtra",
     "address": "Vashi, Navi Mumbai - 400703", "phone": "022-27844600"},
    # ── Pune ────────────────────────────────────────────────────────────────
    {"aliases": ["pune", "pune city", "shivajinagar", "deccan"],
     "station": "Shivajinagar Police Station", "district": "Pune", "state": "Maharashtra",
     "address": "Shivajinagar, Pune - 411005", "phone": "020-25531000"},
    {"aliases": ["hadapsar", "magarpatta", "mundhwa"],
     "station": "Hadapsar Police Station", "district": "Pune", "state": "Maharashtra",
     "address": "Hadapsar, Pune - 411028", "phone": "020-26823200"},
    {"aliases": ["kothrud", "karve nagar"],
     "station": "Kothrud Police Station", "district": "Pune", "state": "Maharashtra",
     "address": "Kothrud, Pune - 411038", "phone": "020-25384300"},
    {"aliases": ["pimpri", "pimpri chinchwad", "chinchwad", "pcmc"],
     "station": "Pimpri Police Station", "district": "Pimpri-Chinchwad", "state": "Maharashtra",
     "address": "Old Mumbai-Pune Road, Pimpri - 411018", "phone": "020-27422200"},
    {"aliases": ["wakad", "hinjewadi", "baner"],
     "station": "Hinjewadi Police Station", "district": "Pune", "state": "Maharashtra",
     "address": "Hinjewadi, Pune - 411057", "phone": "020-22950100"},
    # ── Other MH ────────────────────────────────────────────────────────────
    {"aliases": ["nagpur", "nagpur city", "civil lines nagpur", "sitabuldi"],
     "station": "Sitabuldi Police Station", "district": "Nagpur", "state": "Maharashtra",
     "address": "Sitabuldi, Nagpur - 440012", "phone": "0712-2520500"},
    {"aliases": ["nashik", "nashik road", "deolali"],
     "station": "Nashik Road Police Station", "district": "Nashik", "state": "Maharashtra",
     "address": "Nashik Road, Nashik - 422101", "phone": "0253-2465300"},
    {"aliases": ["aurangabad", "sambhajinagar", "chhatrapati sambhajinagar", "cidco"],
     "station": "Cidco Police Station", "district": "Chhatrapati Sambhajinagar", "state": "Maharashtra",
     "address": "CIDCO N-5, Aurangabad - 431003", "phone": "0240-2474700"},
    {"aliases": ["kolhapur", "ichalkaranji"],
     "station": "Kolhapur City Police Station", "district": "Kolhapur", "state": "Maharashtra",
     "address": "Shahupuri, Kolhapur - 416001", "phone": "0231-2650100"},
    {"aliases": ["solapur", "sholapur"],
     "station": "Solapur City Police Station", "district": "Solapur", "state": "Maharashtra",
     "address": "Budhwar Peth, Solapur - 413002", "phone": "0217-2727200"},
    {"aliases": ["raigad", "panvel", "khopoli"],
     "station": "Panvel Police Station", "district": "Raigad", "state": "Maharashtra",
     "address": "Panvel, Raigad - 410206", "phone": "022-27460100"},
    {"aliases": ["amravati", "amrawati"],
     "station": "Amravati City Police Station", "district": "Amravati", "state": "Maharashtra",
     "address": "Rajkamal Chowk, Amravati - 444601", "phone": "0721-2662100"},

    # ════════════════════════════════════════════════════════════════════════
    # DELHI (NCT)
    # ════════════════════════════════════════════════════════════════════════
    {"aliases": ["connaught place", "cp", "central delhi", "barakhamba"],
     "station": "Connaught Place Police Station", "district": "Central Delhi", "state": "Delhi",
     "address": "Connaught Place, New Delhi - 110001", "phone": "011-23417001"},
    {"aliases": ["lajpat nagar", "south extension", "andrew ganj"],
     "station": "Lajpat Nagar Police Station", "district": "South Delhi", "state": "Delhi",
     "address": "Lajpat Nagar, New Delhi - 110024", "phone": "011-29834200"},
    {"aliases": ["dwarka", "dwarka sector", "uttam nagar"],
     "station": "Dwarka Police Station", "district": "South West Delhi", "state": "Delhi",
     "address": "Dwarka Sector 10, New Delhi - 110075", "phone": "011-25087602"},
    {"aliases": ["rohini", "pitampura", "shalimar bagh"],
     "station": "Rohini Police Station", "district": "North West Delhi", "state": "Delhi",
     "address": "Sector 3, Rohini, Delhi - 110085", "phone": "011-27050200"},
    {"aliases": ["karol bagh", "patel nagar", "rajendra place"],
     "station": "Karol Bagh Police Station", "district": "Central Delhi", "state": "Delhi",
     "address": "Karol Bagh, New Delhi - 110005", "phone": "011-23545700"},
    {"aliases": ["hauz khas", "green park", "safdarjung"],
     "station": "Hauz Khas Police Station", "district": "South Delhi", "state": "Delhi",
     "address": "Hauz Khas, New Delhi - 110016", "phone": "011-26569400"},
    {"aliases": ["janakpuri", "vikaspuri", "tilak nagar"],
     "station": "Janakpuri Police Station", "district": "West Delhi", "state": "Delhi",
     "address": "Janakpuri, New Delhi - 110058", "phone": "011-25523200"},
    {"aliases": ["shahdara", "krishna nagar", "preet vihar"],
     "station": "Shahdara Police Station", "district": "Shahdara", "state": "Delhi",
     "address": "Shahdara, Delhi - 110032", "phone": "011-22327200"},
    {"aliases": ["mayur vihar", "patparganj", "kondli"],
     "station": "Mayur Vihar Police Station", "district": "East Delhi", "state": "Delhi",
     "address": "Mayur Vihar Phase 1, Delhi - 110091", "phone": "011-22754200"},
    {"aliases": ["saket", "malviya nagar", "pushp vihar"],
     "station": "Saket Police Station", "district": "South Delhi", "state": "Delhi",
     "address": "Saket, New Delhi - 110017", "phone": "011-29563300"},
    {"aliases": ["civil lines", "tis hazari", "metcalfe house"],
     "station": "Civil Lines Police Station", "district": "North Delhi", "state": "Delhi",
     "address": "Civil Lines, Delhi - 110054", "phone": "011-23985200"},
    {"aliases": ["new delhi", "paharganj", "ajmeri gate"],
     "station": "Paharganj Police Station", "district": "Central Delhi", "state": "Delhi",
     "address": "Paharganj, New Delhi - 110055", "phone": "011-23583200"},

    # ════════════════════════════════════════════════════════════════════════
    # KARNATAKA (Bengaluru)
    # ════════════════════════════════════════════════════════════════════════
    {"aliases": ["koramangala", "hsr layout", "btm"],
     "station": "Koramangala Police Station", "district": "Bengaluru South", "state": "Karnataka",
     "address": "Koramangala, Bengaluru - 560034", "phone": "080-22942300"},
    {"aliases": ["indiranagar", "domlur", "old airport road"],
     "station": "Indiranagar Police Station", "district": "Bengaluru East", "state": "Karnataka",
     "address": "Indiranagar, Bengaluru - 560038", "phone": "080-25253800"},
    {"aliases": ["whitefield", "hoodi", "kadugodi", "itpl"],
     "station": "Whitefield Police Station", "district": "Bengaluru East", "state": "Karnataka",
     "address": "Whitefield, Bengaluru - 560066", "phone": "080-22943400"},
    {"aliases": ["marathahalli", "sarjapur", "outer ring road"],
     "station": "Marathahalli Police Station", "district": "Bengaluru East", "state": "Karnataka",
     "address": "Marathahalli, Bengaluru - 560037", "phone": "080-25733800"},
    {"aliases": ["jayanagar", "jp nagar", "banashankari"],
     "station": "Jayanagar Police Station", "district": "Bengaluru South", "state": "Karnataka",
     "address": "Jayanagar, Bengaluru - 560011", "phone": "080-22943700"},
    {"aliases": ["mg road", "brigade road", "richmond town", "shivajinagar bangalore"],
     "station": "Shivajinagar Police Station", "district": "Bengaluru Central", "state": "Karnataka",
     "address": "Shivajinagar, Bengaluru - 560001", "phone": "080-22204010"},
    {"aliases": ["rajajinagar", "yeshwanthpur", "malleswaram"],
     "station": "Rajajinagar Police Station", "district": "Bengaluru West", "state": "Karnataka",
     "address": "Rajajinagar, Bengaluru - 560010", "phone": "080-23440200"},
    {"aliases": ["hebbal", "yelahanka", "kempegowda airport"],
     "station": "Hebbal Police Station", "district": "Bengaluru North", "state": "Karnataka",
     "address": "Hebbal, Bengaluru - 560024", "phone": "080-23631900"},
    {"aliases": ["electronic city", "bommasandra", "hosur road"],
     "station": "Electronic City Police Station", "district": "Bengaluru South", "state": "Karnataka",
     "address": "Electronic City Phase 1, Bengaluru - 560100", "phone": "080-27838100"},
    {"aliases": ["bellandur", "kadubeesanahalli", "pannathur"],
     "station": "Bellandur Police Station", "district": "Bengaluru East", "state": "Karnataka",
     "address": "Bellandur, Bengaluru - 560103", "phone": "080-22943500"},
    {"aliases": ["mysuru", "mysore", "mysore city"],
     "station": "Mysuru North Police Station", "district": "Mysuru", "state": "Karnataka",
     "address": "Nazarbad, Mysuru - 570010", "phone": "0821-2432022"},

    # ════════════════════════════════════════════════════════════════════════
    # TAMIL NADU (Chennai + key cities)
    # ════════════════════════════════════════════════════════════════════════
    {"aliases": ["anna nagar", "anna nagar west", "anna nagar east"],
     "station": "Anna Nagar Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "Anna Nagar, Chennai - 600040", "phone": "044-26153100"},
    {"aliases": ["t nagar", "thyagaraya nagar", "pondy bazaar"],
     "station": "T Nagar Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "T Nagar, Chennai - 600017", "phone": "044-24342900"},
    {"aliases": ["mylapore", "royapettah", "alwarpet"],
     "station": "Mylapore Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "Mylapore, Chennai - 600004", "phone": "044-24942800"},
    {"aliases": ["adyar", "besant nagar", "thiruvanmiyur"],
     "station": "Adyar Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "Adyar, Chennai - 600020", "phone": "044-24412200"},
    {"aliases": ["velachery", "medavakkam", "perungudi"],
     "station": "Velachery Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "Velachery, Chennai - 600042", "phone": "044-22430100"},
    {"aliases": ["guindy", "ekkattuthangal", "chennai airport"],
     "station": "Guindy Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "Guindy, Chennai - 600032", "phone": "044-22354700"},
    {"aliases": ["egmore", "park town", "central chennai", "chennai central"],
     "station": "Egmore Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "Egmore, Chennai - 600008", "phone": "044-28523400"},
    {"aliases": ["tambaram", "chromepet", "pallavaram"],
     "station": "Tambaram Police Station", "district": "Kancheepuram", "state": "Tamil Nadu",
     "address": "Tambaram, Chennai - 600045", "phone": "044-22262200"},
    {"aliases": ["perambur", "kolathur", "villivakkam"],
     "station": "Perambur Police Station", "district": "Chennai City", "state": "Tamil Nadu",
     "address": "Perambur, Chennai - 600011", "phone": "044-26752200"},
    {"aliases": ["coimbatore", "coimbatore city", "rs puram"],
     "station": "RS Puram Police Station", "district": "Coimbatore", "state": "Tamil Nadu",
     "address": "R.S. Puram, Coimbatore - 641002", "phone": "0422-2542100"},

    # ════════════════════════════════════════════════════════════════════════
    # WEST BENGAL (Kolkata + key areas)
    # ════════════════════════════════════════════════════════════════════════
    {"aliases": ["park street", "esplanade", "chowringhee"],
     "station": "Park Street Police Station", "district": "Kolkata", "state": "West Bengal",
     "address": "Park Street, Kolkata - 700016", "phone": "033-22275100"},
    {"aliases": ["salt lake", "bidhannagar", "sector 5", "sector v"],
     "station": "Bidhannagar Police Station", "district": "North 24 Parganas", "state": "West Bengal",
     "address": "Salt Lake, Kolkata - 700064", "phone": "033-23358200"},
    {"aliases": ["dum dum", "dum dum airport", "nager bazar"],
     "station": "Dum Dum Police Station", "district": "North 24 Parganas", "state": "West Bengal",
     "address": "Dum Dum, Kolkata - 700028", "phone": "033-25511300"},
    {"aliases": ["howrah", "howrah station", "shibpur"],
     "station": "Howrah Police Station", "district": "Howrah", "state": "West Bengal",
     "address": "Howrah, West Bengal - 711101", "phone": "033-26382200"},
    {"aliases": ["ultadanga", "phoolbagan", "kankurgachi"],
     "station": "Ultadanga Police Station", "district": "Kolkata", "state": "West Bengal",
     "address": "Ultadanga, Kolkata - 700067", "phone": "033-23218800"},
    {"aliases": ["jadavpur", "lake town", "kasba"],
     "station": "Jadavpur Police Station", "district": "Kolkata", "state": "West Bengal",
     "address": "Jadavpur, Kolkata - 700032", "phone": "033-24143200"},
    {"aliases": ["gariahat", "dhakuria", "lake gardens"],
     "station": "Gariahat Police Station", "district": "Kolkata", "state": "West Bengal",
     "address": "Gariahat, Kolkata - 700029", "phone": "033-24663200"},
    {"aliases": ["behala", "parnasree", "joka"],
     "station": "Behala Police Station", "district": "Kolkata", "state": "West Bengal",
     "address": "Behala, Kolkata - 700034", "phone": "033-24011700"},
    {"aliases": ["alipore", "hastings", "new alipore"],
     "station": "Alipore Police Station", "district": "Kolkata", "state": "West Bengal",
     "address": "Alipore, Kolkata - 700027", "phone": "033-22391900"},
    {"aliases": ["entally", "topsia", "tangra"],
     "station": "Entally Police Station", "district": "Kolkata", "state": "West Bengal",
     "address": "Entally, Kolkata - 700014", "phone": "033-22862200"},
]


def _tokenise(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z]+", text.lower()) if len(t) >= 3]


def find_police_station(location_text: str) -> dict:
    """
    Match location text to nearest indexed police station across 5 states.

    Returns
    -------
    {
        "matched": bool,
        "station": str | None,
        "district": str | None,
        "state": str | None,
        "address": str | None,
        "phone": str | None,
        "zero_fir_note": str,
        "confidence": "high" | "low" | "none",
        "pilot_note": str,
    }
    """
    tokens = set(_tokenise(location_text))
    best_match = None
    best_score = 0

    for ps in _PS_DATA:
        score = 0
        for alias in ps["aliases"]:
            if alias.lower() in location_text.lower():
                score += 10
            else:
                alias_tokens = set(_tokenise(alias))
                if not alias_tokens:
                    # Alias has no tokenisable words (e.g. short abbreviations
                    # like "cp") and did not match as a substring above —
                    # skip it here rather than let an empty-set overlap
                    # falsely "match" every unrelated location text.
                    continue
                overlap = len(tokens & alias_tokens)
                if overlap >= len(alias_tokens):
                    score += 6
                elif overlap > 0:
                    score += overlap
        if score > best_score:
            best_score = score
            best_match = ps

    zero_fir = (
        "\U0001f4cc Zero FIR Right: Under Section 173(1) BNSS, you can file an FIR at "
        "ANY police station regardless of jurisdiction. The station MUST accept "
        "it and forward it to the jurisdictional station. Do not let anyone turn you away."
    )

    if best_match and best_score >= 6:
        return {
            "matched": True,
            "station": best_match["station"],
            "district": best_match["district"],
            "state": best_match.get("state", "India"),
            "address": best_match["address"],
            "phone": best_match["phone"],
            "confidence": "high" if best_score >= 10 else "low",
            "zero_fir_note": zero_fir,
            "pilot_note": "5-state pilot: Maharashtra, Delhi, Karnataka, Tamil Nadu, West Bengal. Confirm exact jurisdiction at the station.",
        }

    # Graceful degradation — reset best_match first. Otherwise a low,
    # sub-threshold score from the primary loop above (e.g. a single
    # partial token overlap that scored 1-5 points) would leak through
    # here and be presented as a "nearby suggestion" even though it
    # never actually matched the location text.
    best_match = None
    dist = None
    for ps in _PS_DATA:
        if ps["district"].lower() in location_text.lower() or ps.get("state", "").lower() in location_text.lower():
            dist = ps["district"]
            best_match = ps
            break

    return {
        "matched": False,
        "station": best_match["station"] if best_match else None,
        "district": dist,
        "state": best_match.get("state") if best_match else None,
        "address": best_match["address"] if best_match else None,
        "phone": best_match["phone"] if best_match else "100 (Police Control Room)",
        "confidence": "none",
        "zero_fir_note": zero_fir,
        "pilot_note": (
            "Location not precisely matched. Covered states: Maharashtra, Delhi, Karnataka, "
            "Tamil Nadu, West Bengal. Please confirm the exact station or call 100."
        ),
    }
