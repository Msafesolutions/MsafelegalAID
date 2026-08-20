"""
Indian States and Union Territories — the jurisdiction list used for
state-specific legal rules (traffic compounding amounts, State Police Acts,
State RTI Rules, excise/prohibition, rent control).

`code` values are the official 2-letter ISO 3166-2:IN subdivision codes, so they
are stable and safe to store on the user document forever.
"""

STATES = [
    # ---- 28 States ----
    {"code": "AP", "name": "Andhra Pradesh", "native": "ఆంధ్రప్రదేశ్", "type": "state"},
    {"code": "AR", "name": "Arunachal Pradesh", "native": "अरुणाचल प्रदेश", "type": "state"},
    {"code": "AS", "name": "Assam", "native": "অসম", "type": "state"},
    {"code": "BR", "name": "Bihar", "native": "बिहार", "type": "state"},
    {"code": "CG", "name": "Chhattisgarh", "native": "छत्तीसगढ़", "type": "state"},
    {"code": "GA", "name": "Goa", "native": "गोवा", "type": "state"},
    {"code": "GJ", "name": "Gujarat", "native": "ગુજરાત", "type": "state"},
    {"code": "HR", "name": "Haryana", "native": "हरियाणा", "type": "state"},
    {"code": "HP", "name": "Himachal Pradesh", "native": "हिमाचल प्रदेश", "type": "state"},
    {"code": "JH", "name": "Jharkhand", "native": "झारखंड", "type": "state"},
    {"code": "KA", "name": "Karnataka", "native": "ಕರ್ನಾಟಕ", "type": "state"},
    {"code": "KL", "name": "Kerala", "native": "കേരളം", "type": "state"},
    {"code": "MP", "name": "Madhya Pradesh", "native": "मध्य प्रदेश", "type": "state"},
    {"code": "MH", "name": "Maharashtra", "native": "महाराष्ट्र", "type": "state"},
    {"code": "MN", "name": "Manipur", "native": "মণিপুর", "type": "state"},
    {"code": "ML", "name": "Meghalaya", "native": "मेघालय", "type": "state"},
    {"code": "MZ", "name": "Mizoram", "native": "मिजोरम", "type": "state"},
    {"code": "NL", "name": "Nagaland", "native": "नागालैंड", "type": "state"},
    {"code": "OD", "name": "Odisha", "native": "ଓଡ଼ିଶା", "type": "state"},
    {"code": "PB", "name": "Punjab", "native": "ਪੰਜਾਬ", "type": "state"},
    {"code": "RJ", "name": "Rajasthan", "native": "राजस्थान", "type": "state"},
    {"code": "SK", "name": "Sikkim", "native": "सिक्किम", "type": "state"},
    {"code": "TN", "name": "Tamil Nadu", "native": "தமிழ்நாடு", "type": "state"},
    {"code": "TG", "name": "Telangana", "native": "తెలంగాణ", "type": "state"},
    {"code": "TR", "name": "Tripura", "native": "ত্রিপুরা", "type": "state"},
    {"code": "UP", "name": "Uttar Pradesh", "native": "उत्तर प्रदेश", "type": "state"},
    {"code": "UK", "name": "Uttarakhand", "native": "उत्तराखंड", "type": "state"},
    {"code": "WB", "name": "West Bengal", "native": "পশ্চিমবঙ্গ", "type": "state"},
    # ---- 8 Union Territories ----
    {"code": "AN", "name": "Andaman & Nicobar Islands", "native": "अंडमान और निकोबार", "type": "ut"},
    {"code": "CH", "name": "Chandigarh", "native": "चंडीगढ़", "type": "ut"},
    {"code": "DH", "name": "Dadra & Nagar Haveli and Daman & Diu", "native": "दादरा नगर हवेली और दमन दीव", "type": "ut"},
    {"code": "DL", "name": "Delhi (NCT)", "native": "दिल्ली", "type": "ut"},
    {"code": "JK", "name": "Jammu & Kashmir", "native": "जम्मू और कश्मीर", "type": "ut"},
    {"code": "LA", "name": "Ladakh", "native": "लद्दाख", "type": "ut"},
    {"code": "LD", "name": "Lakshadweep", "native": "लक्षद्वीप", "type": "ut"},
    {"code": "PY", "name": "Puducherry", "native": "புதுச்சேரி", "type": "ut"},
]

STATE_BY_CODE = {s["code"]: s for s in STATES}


def state_name(code: str) -> str:
    s = STATE_BY_CODE.get((code or "").upper())
    return s["name"] if s else ""


def is_valid_state(code: str) -> bool:
    return (code or "").upper() in STATE_BY_CODE
