"""
DHARA CORPUS — Negotiable Instruments Act 1881 (cheque bounce).

Same schema and rules as corpus.py. Verbatim text from indiacode.nic.in.

Why this file exists: "cheque bounce" was the single largest refusal bucket in
the A4 refusal analytics (topic `cheque_bounce_financial`). The most valuable
fact for a real user is the TIMELINE — 30 days to send the demand notice,
15 days for the drawer to pay, then 1 month to file the complaint — so every
entry below spells that out in its scope_note.
"""

NI_CORPUS = [
    {
        "key": "ni_138",
        "citation": "Negotiable Instruments Act 1881, Section 138 — Dishonour of cheque for insufficiency of funds in the account",
        "short_label": "NI 138",
        "act": "NI",
        # Guard: these entries may only match when the question actually mentions a
        # cheque — otherwise generic words like "deposit", "notice" or "appeal"
        # pulled cheque sections into unrelated answers (e.g. rent deposits).
        "require_any": ["cheque", "check", "chq", "dishonour", "dishonor", "bounce", "bounced"],
        "official_text": (
            "Where any cheque drawn by a person on an account maintained by him with a banker "
            "for payment of any amount of money to another person from out of that account for "
            "the discharge, in whole or in part, of any debt or other liability, is returned by "
            "the bank unpaid, either because of the amount of money standing to the credit of "
            "that account is insufficient to honour the cheque or that it exceeds the amount "
            "arranged to be paid from that account by an agreement made with that bank, such "
            "person shall be deemed to have committed an offence and shall, without prejudice "
            "to any other provisions of this Act, be punished with imprisonment for a term which "
            "may be extended to two years, or with fine which may extend to twice the amount of "
            "the cheque, or with both:\n"
            "Provided that nothing contained in this section shall apply unless—\n"
            "(a) the cheque has been presented to the bank within a period of six months from "
            "the date on which it is drawn or within the period of its validity, whichever is "
            "earlier;\n"
            "(b) the payee or the holder in due course of the cheque, as the case may be, makes "
            "a demand for the payment of the said amount of money by giving a notice in writing, "
            "to the drawer of the cheque, within thirty days of the receipt of information by him "
            "from the bank regarding the return of the cheque as unpaid; and\n"
            "(c) the drawer of such cheque fails to make the payment of the said amount of money "
            "to the payee or, as the case may be, to the holder in due course of the cheque, "
            "within fifteen days of the receipt of the said notice.\n"
            "Explanation.—For the purposes of this section, 'debt or other liability' means a "
            "legally enforceable debt or other liability."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "A bounced cheque is a criminal offence — up to 2 years jail or a fine up to twice "
            "the cheque amount. But the case only stands if you follow the clock: the cheque must "
            "be presented within 6 months of its date, you must send a WRITTEN demand notice "
            "within 30 DAYS of the bank's return memo, and the drawer then gets 15 DAYS to pay. "
            "Miss the 30-day notice deadline and the criminal case is lost — only a civil "
            "recovery suit remains."
        ),
        "keywords": [
            "ni 138", "section 138", "section 138 cheque", "cheque bounce", "check bounce",
            "cheque bounced", "cheque dishonour", "cheque dishonoured", "cheque returned",
            "cheque return memo", "insufficient funds cheque", "bounced cheque case",
            "cheque bounce punishment", "cheque bounce jail", "cheque bounce notice",
            "30 days notice cheque", "thirty days cheque notice", "15 days cheque payment",
            "legal notice cheque bounce", "cheque bounce deadline", "cheque bounce time limit",
            "post dated cheque bounce", "emi cheque bounce", "security cheque bounce",
            "six months cheque validity", "stale cheque",
        ],
    },
    {
        "key": "ni_142",
        "citation": "Negotiable Instruments Act 1881, Section 142 — Cognizance of offences",
        "short_label": "NI 142",
        "act": "NI",
        # Guard: these entries may only match when the question actually mentions a
        # cheque — otherwise generic words like "deposit", "notice" or "appeal"
        # pulled cheque sections into unrelated answers (e.g. rent deposits).
        "require_any": ["cheque", "check", "chq", "dishonour", "dishonor", "bounce", "bounced"],
        "official_text": (
            "(1) Notwithstanding anything contained in the Code of Criminal Procedure, 1973,—\n"
            "(a) no court shall take cognizance of any offence punishable under section 138 "
            "except upon a complaint, in writing, made by the payee or, as the case may be, the "
            "holder in due course of the cheque;\n"
            "(b) such complaint is made within one month of the date on which the cause of action "
            "arises under clause (c) of the proviso to section 138:\n"
            "Provided that the cognizance of a complaint may be taken by the Court after the "
            "prescribed period, if the complainant satisfies the Court that he had sufficient "
            "cause for not making a complaint within such period;\n"
            "(c) no court inferior to that of a Metropolitan Magistrate or a Judicial Magistrate "
            "of the first class shall try any offence punishable under section 138.\n"
            "(2) The offence under section 138 shall be inquired into and tried only by a court "
            "within whose local jurisdiction,—\n"
            "(a) if the cheque is delivered for collection through an account, the branch of the "
            "bank where the payee or holder in due course, as the case may be, maintains the "
            "account, is situated; or\n"
            "(b) if the cheque is presented for payment by the payee or holder in due course "
            "otherwise than through an account, the branch of the drawee bank where the drawer "
            "maintains the account, is situated."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Only the person who was to receive the money can file the cheque-bounce complaint, "
            "in writing, and it must be filed WITHIN ONE MONTH after the 15-day payment window "
            "ends. The case is filed in the court where YOUR bank branch is — not the drawer's "
            "city. A late complaint can still be accepted if you show good reason for the delay."
        ),
        "keywords": [
            "ni 142", "section 142", "cheque bounce complaint", "cheque case filing",
            "where to file cheque bounce case", "cheque bounce court", "cheque bounce one month",
            "cheque complaint time limit", "cheque bounce jurisdiction",
            "who can file cheque case", "magistrate cheque case", "late cheque complaint",
        ],
    },
    {
        "key": "ni_139",
        "citation": "Negotiable Instruments Act 1881, Section 139 — Presumption in favour of holder",
        "short_label": "NI 139",
        "act": "NI",
        # Guard: these entries may only match when the question actually mentions a
        # cheque — otherwise generic words like "deposit", "notice" or "appeal"
        # pulled cheque sections into unrelated answers (e.g. rent deposits).
        "require_any": ["cheque", "check", "chq", "dishonour", "dishonor", "bounce", "bounced"],
        "official_text": (
            "It shall be presumed, unless the contrary is proved, that the holder of a cheque "
            "received the cheque of the nature referred to in section 138 for the discharge, in "
            "whole or in part, of any debt or other liability."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "The law starts by BELIEVING the person holding the cheque — it is presumed the "
            "cheque was given to pay a real debt. The person who wrote the cheque has to prove "
            "otherwise. This is why cheque-bounce cases are usually strong for the receiver."
        ),
        "keywords": [
            "ni 139", "section 139", "presumption cheque", "burden of proof cheque",
            "cheque given as security defence", "prove cheque debt", "cheque bounce defence",
            "blank cheque misuse", "cheque no debt",
        ],
    },
    {
        "key": "ni_143a",
        "citation": "Negotiable Instruments Act 1881, Section 143A — Power to direct interim compensation",
        "short_label": "NI 143A",
        "act": "NI",
        # Guard: these entries may only match when the question actually mentions a
        # cheque — otherwise generic words like "deposit", "notice" or "appeal"
        # pulled cheque sections into unrelated answers (e.g. rent deposits).
        "require_any": ["cheque", "check", "chq", "dishonour", "dishonor", "bounce", "bounced"],
        "official_text": (
            "(1) Notwithstanding anything contained in the Code of Criminal Procedure, 1973, the "
            "Court trying an offence under section 138 may order the drawer of the cheque to pay "
            "interim compensation to the complainant—\n"
            "(a) in a summary trial or a summons case, where he pleads not guilty to the "
            "accusation made in the complaint; and\n"
            "(b) in any other case, upon framing of charge.\n"
            "(2) The interim compensation under sub-section (1) shall not exceed twenty per cent. "
            "of the amount of the cheque.\n"
            "(3) The interim compensation shall be paid within sixty days from the date of the "
            "order under sub-section (1), or within such further period not exceeding thirty days "
            "as may be directed by the Court on sufficient cause being shown by the drawer of the "
            "cheque.\n"
            "(4) If the drawer of the cheque is acquitted, the Court shall direct the complainant "
            "to repay to the drawer the amount of interim compensation, with interest at the bank "
            "rate as published by the Reserve Bank of India, prevalent at the beginning of the "
            "relevant financial year, within sixty days from the date of the order, or within "
            "such further period not exceeding thirty days as may be directed by the Court on "
            "sufficient cause being shown by the complainant."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "You do not have to wait for the whole trial to get some money. The court can order "
            "the cheque writer to pay you INTERIM COMPENSATION of up to 20% of the cheque amount, "
            "payable within 60 days. If he is later acquitted, you repay it with interest."
        ),
        "keywords": [
            "ni 143a", "section 143a", "interim compensation cheque", "20 percent cheque",
            "twenty percent interim", "money during cheque trial", "advance compensation cheque",
        ],
    },
    {
        "key": "ni_148",
        "citation": "Negotiable Instruments Act 1881, Section 148 — Power of Appellate Court to order payment pending appeal against conviction",
        "short_label": "NI 148",
        "act": "NI",
        # Guard: these entries may only match when the question actually mentions a
        # cheque — otherwise generic words like "deposit", "notice" or "appeal"
        # pulled cheque sections into unrelated answers (e.g. rent deposits).
        "require_any": ["cheque", "check", "chq", "dishonour", "dishonor", "bounce", "bounced"],
        "official_text": (
            "(1) Notwithstanding anything contained in the Code of Criminal Procedure, 1973, in "
            "an appeal by the drawer against conviction under section 138, the Appellate Court "
            "may order the appellant to deposit such sum which shall be a minimum of twenty per "
            "cent. of the fine or compensation awarded by the trial Court:\n"
            "Provided that the amount payable under this sub-section shall be in addition to any "
            "interim compensation paid by the appellant under section 143A.\n"
            "(2) The amount referred to in sub-section (1) shall be deposited within sixty days "
            "from the date of the order, or within such further period not exceeding thirty days "
            "as may be directed by the Court on sufficient cause being shown by the appellant.\n"
            "(3) The Appellate Court may direct the release of the amount deposited by the "
            "appellant to the complainant at any time during the pendency of the appeal."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "If the cheque writer is convicted and files an appeal, the appeal court must make "
            "him deposit at least 20% of the fine or compensation, and can release that money to "
            "you while the appeal is still going on. An appeal no longer freezes your recovery."
        ),
        "keywords": [
            "ni 148", "section 148", "cheque bounce appeal", "appeal deposit cheque",
            "20 percent appeal deposit", "convicted cheque appeal", "recover money appeal cheque",
        ],
    },
]
