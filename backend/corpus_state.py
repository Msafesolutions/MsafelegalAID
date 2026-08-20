"""
DHARA STATE CORPUS — state and union-territory specific rules.

Central law (BNS, BNSS, Constitution, MV Act, RTI Act, CPA…) lives in corpus.py
and corpus_ipc.py. This file holds rules that apply ONLY inside one state or UT:
traffic compounding amounts, State Police Acts, State RTI Rules, excise and
prohibition, and rent control.

Every entry uses the SAME schema as CORPUS plus two extra fields:

  state      — ISO 3166-2:IN code from states.py (e.g. "GJ", "BR", "DL")
  text_kind  — "verbatim"          : official_text is the exact statutory text
               "official_summary"  : official_text is a faithful summary of the
                                     operative provision (used where the current
                                     position comes from an amendment/notification
                                     whose gazette wording could not be pinned
                                     down word-for-word). The UI labels these
                                     honestly so a user is never told a summary
                                     is a verbatim quote.

The retrieval layer returns state hits ALONGSIDE central hits so the answer can
show both as separate verified sources.
"""

STATE_CORPUS = [
    # -------------------- GUJARAT — prohibition --------------------
    {
        "key": "gj_prohibition_66",
        "state": "GJ",
        "citation": "Gujarat Prohibition Act 1949, Section 66(1)(b) — Penalty for consuming liquor",
        "short_label": "Gujarat Prohibition 66(1)(b)",
        "act": "Gujarat Prohibition Act",
        "text_kind": "official_summary",
        "official_text": (
            "Whoever, in contravention of the provisions of this Act or of any rule, "
            "regulation or order made or of any licence, permit, pass or authorisation "
            "issued thereunder, consumes, uses, possesses or buys any intoxicant, shall, "
            "on conviction, be punished — for a first offence, with imprisonment which may "
            "extend to six months and with fine which may extend to one thousand rupees; "
            "and for a second or subsequent offence, with imprisonment which may extend to "
            "two years, subject to a minimum of six months, and with fine which may extend "
            "to two thousand rupees.\n"
            "Consumption under a valid health permit, tourist permit, licence or pass issued "
            "under the Act is NOT an offence, because the section applies only where the act "
            "is in contravention of the Act or of the conditions of the permit."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/6165/1/h-2065_the_guj_prohibition_act_1949.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Gujarat is a dry state. Drinking or possessing liquor without a valid permit is a "
            "criminal offence — up to 6 months for a first offence. If you hold a valid health "
            "or tourist permit and stay within its conditions, you are not committing an offence."
        ),
        "keywords": [
            "gujarat liquor", "gujarat alcohol", "gujarat prohibition", "dry state gujarat",
            "drinking gujarat", "liquor permit gujarat", "tourist liquor permit",
            "health permit liquor", "caught drinking gujarat", "alcohol ban gujarat",
            "daru gujarat",
        ],
    },
    # -------------------- BIHAR — prohibition --------------------
    {
        "key": "br_prohibition_37",
        "state": "BR",
        "citation": "Bihar Prohibition and Excise Act 2016, Section 37 (as amended in 2022) — Penalty for consumption of liquor",
        "short_label": "Bihar Prohibition 37",
        "act": "Bihar Prohibition and Excise Act",
        "text_kind": "official_summary",
        "official_text": (
            "A person found to have consumed liquor or any intoxicant is produced before the "
            "Executive Magistrate. For a FIRST offence the Magistrate may release the person on "
            "payment of a penalty of not less than two thousand rupees and not more than five "
            "thousand rupees; if the person refuses or fails to pay that penalty, the person shall "
            "undergo simple imprisonment for one month.\n"
            "For a SECOND or subsequent offence the person is liable to imprisonment which may "
            "extend to one year and to fine, and the option of release on payment of penalty is "
            "not available.\n"
            "(This is the position after the Bihar Prohibition and Excise (Amendment) Act, 2022, "
            "which replaced the original 2016 penalties of 5-7 years' imprisonment.)"
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20567",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Bihar is a dry state. Since the 2022 amendment, a first-time drinker is normally let "
            "off on payment of a ₹2,000-₹5,000 penalty before an Executive Magistrate instead of "
            "going to jail — but a second offence means jail up to one year."
        ),
        "keywords": [
            "bihar liquor", "bihar alcohol", "bihar prohibition", "dry state bihar",
            "drinking bihar", "caught drinking bihar", "bihar sharab", "sharabbandi",
            "bihar liquor fine", "bihar first time offender liquor", "alcohol ban bihar",
        ],
    },
]
