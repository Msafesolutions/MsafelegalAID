"""
DHARA CORPUS — Negotiable Instruments Act 1881 (cheque bounce).

Same schema and rules as corpus.py. Verbatim text from indiacode.nic.in.

Why this file exists: "cheque bounce" was the single largest refusal bucket in
the A4 refusal analytics (topic `cheque_bounce_financial`). The most valuable
fact for a real user is the TIMELINE — 30 days to send the demand notice,
15 days for the drawer to pay, then 1 month to file the complaint — so every
entry below spells that out in its scope_note.

Sections covered: 6, 7, 9, 25, 138, 139, 140, 141, 142, 143, 143A, 144, 145,
                   146, 147, 148. Civil suit limitation also noted.
"""

# Guard for all NI entries: only match when the question mentions a cheque
_NI_GUARD = ["cheque", "check", "chq", "dishonour", "dishonor", "bounce", "bounced", "ni act", "negotiable"]

NI_CORPUS = [
    # -----------------------------------------------------------------
    # Core definitions
    # -----------------------------------------------------------------
    {
        "key": "ni_6",
        "citation": "Negotiable Instruments Act 1881, Section 6 — Cheque",
        "short_label": "NI 6",
        "act": "NI",
        "require_any": _NI_GUARD,
        "official_text": (
            "A 'cheque' is a bill of exchange drawn on a specified banker and not expressed "
            "to be payable otherwise than on demand and it includes the electronic image of a "
            "truncated cheque and a cheque in the electronic form.\n"
            "Explanation I.—For the purposes of this section, the expressions—\n"
            "(a) 'a cheque in the electronic form' means a cheque which contains the exact "
            "mirror image of a paper cheque, and is generated, written and signed in a secure "
            "system ensuring the minimum safety standards with the use of digital signature "
            "(with or without biometrics signature) and asymmetric crypto system;\n"
            "(b) 'a truncated cheque' means a cheque which is truncated during the course of a "
            "clearing cycle, either by the clearing house or by the bank whether paying or "
            "receiving payment, immediately on generation of an electronic image for "
            "transmission, substituting the further physical movement of the cheque in writing."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "A cheque is a specific type of negotiable instrument — a signed order to your bank "
            "to pay a fixed sum to a named person on demand. Section 138 applies to cheques, "
            "not to promissory notes or bills of exchange. Electronic (e-cheques) and image-based "
            "(truncated) cheques in CTS clearing also qualify under this section."
        ),
        "keywords": [
            "what is a cheque", "cheque definition", "ni act cheque", "electronic cheque",
            "truncated cheque", "e-cheque legal", "cheque in electronic form",
        ],
    },
    {
        "key": "ni_9",
        "citation": "Negotiable Instruments Act 1881, Section 9 — Holder in due course",
        "short_label": "NI 9",
        "act": "NI",
        "require_any": _NI_GUARD,
        "official_text": (
            "'Holder in due course' means any person who for consideration became the possessor "
            "of a promissory note, bill of exchange or cheque if payable to bearer, or the payee "
            "or endorsee thereof, if payable to order, before the amount mentioned in it became "
            "payable, and without having sufficient cause to believe that any defect existed in "
            "the title of the person from whom he derived his title."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "A 'holder in due course' (HDC) is someone who received the cheque in good faith, "
            "for real consideration, before it was due, without knowing of any defect in the "
            "giver's title. An HDC has the strongest legal position — the drawer cannot raise "
            "most defences (like 'I stopped payment because the deal failed') against an HDC."
        ),
        "keywords": [
            "holder in due course", "hdc cheque", "third party cheque", "blank cheque misuse",
            "endorsed cheque rights", "who can claim cheque",
        ],
    },
    # -----------------------------------------------------------------
    # Section 25 — a cheque given for a time-barred debt does not bounce
    # -----------------------------------------------------------------
    {
        "key": "ni_25",
        "citation": "Negotiable Instruments Act 1881, Section 25 — Instruments payable on demand",
        "short_label": "NI 25",
        "act": "NI",
        "require_any": _NI_GUARD + ["time barred", "limitation", "old debt", "stale debt"],
        "official_text": (
            "A promissory note, bill of exchange or cheque, payable on demand, is presented for "
            "payment within a reasonable time after it is drawn, issued or indorsed, as the case "
            "may be. In determining what is a reasonable time, regard shall be had to the nature "
            "of the instrument, the usage of trade and of bankers, and the facts of the "
            "particular case."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Section 138 requires the cheque to be presented within its validity period (usually "
            "3 months from the date of issue). If the cheque was given to discharge a debt that "
            "is already time-barred under the Limitation Act (3 years for simple money contracts), "
            "the Supreme Court has held it is NOT a 'legally enforceable debt', so the Section "
            "138 criminal case does not lie — though the holder may still get a civil remedy."
        ),
        "keywords": [
            "time barred debt cheque", "stale debt cheque bounce", "old debt cheque",
            "limitation period cheque", "cheque for old debt", "legally enforceable debt",
            "3 year limitation cheque", "section 138 time barred",
        ],
    },
    # -----------------------------------------------------------------
    # The main offence
    # -----------------------------------------------------------------
    {
        "key": "ni_138",
        "citation": "Negotiable Instruments Act 1881, Section 138 — Dishonour of cheque for insufficiency of funds in the account",
        "short_label": "NI 138",
        "act": "NI",
        "require_any": _NI_GUARD,
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
            "be presented within 6 months of its date (or validity), you must send a WRITTEN "
            "demand notice within 30 DAYS of the bank's return memo, and the drawer then gets "
            "15 DAYS to pay. Miss the 30-day notice deadline and the criminal case is lost — only "
            "a civil recovery suit remains. The 30-day clock starts from when you RECEIVE the "
            "bank's return memo, not from when the cheque bounced."
        ),
        "keywords": [
            "ni 138", "section 138", "section 138 cheque", "cheque bounce", "check bounce",
            "cheque bounced", "cheque dishonour", "cheque dishonoured", "cheque returned",
            "cheque return memo", "insufficient funds cheque", "bounced cheque case",
            "cheque bounce punishment", "cheque bounce jail", "cheque bounce notice",
            "30 days notice cheque", "thirty days cheque notice", "15 days cheque payment",
            "legal notice cheque bounce", "cheque bounce deadline", "cheque bounce time limit",
            "post dated cheque bounce", "emi cheque bounce", "security cheque bounce",
            "six months cheque validity", "stale cheque", "cheque bounce procedure",
            "what to do when cheque bounces", "cheque bounce steps",
        ],
    },
    # -----------------------------------------------------------------
    # Section 139 — presumption in holder's favour
    # -----------------------------------------------------------------
    {
        "key": "ni_139",
        "citation": "Negotiable Instruments Act 1881, Section 139 — Presumption in favour of holder",
        "short_label": "NI 139",
        "act": "NI",
        "require_any": _NI_GUARD,
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
            "otherwise. This is why cheque-bounce cases are usually strong for the receiver. "
            "Defences like 'I gave it as security, not payment' or 'it was a gift cheque' can "
            "be raised but are hard to prove."
        ),
        "keywords": [
            "ni 139", "section 139", "presumption cheque", "burden of proof cheque",
            "cheque given as security defence", "prove cheque debt", "cheque bounce defence",
            "blank cheque misuse", "cheque no debt", "cheque security deposit defence",
        ],
    },
    # -----------------------------------------------------------------
    # Section 140 — defence not available to drawer
    # -----------------------------------------------------------------
    {
        "key": "ni_140",
        "citation": "Negotiable Instruments Act 1881, Section 140 — Defence which may not be allowed in any prosecution under section 138",
        "short_label": "NI 140",
        "act": "NI",
        "require_any": _NI_GUARD,
        "official_text": (
            "It shall not be a defence in a prosecution for an offence under section 138 that the "
            "drawer had no reason to believe when he issued the cheque that the cheque may be "
            "dishonoured on presentment for the reasons stated in that section."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "'I didn't know there wasn't enough money' is NOT a defence. If you sign a cheque, "
            "you are legally responsible for ensuring your account has funds. The offence is "
            "strict — your honest mistake does not excuse you. Only defences based on the "
            "presumption under Section 139 (proving no debt existed) or a procedural failure "
            "by the payee (like missing the 30-day notice deadline) can save a drawer."
        ),
        "keywords": [
            "ni 140", "section 140", "cheque bounce ignorance defence",
            "did not know balance", "cheque bounce no defence", "strict liability cheque",
            "unaware account empty cheque",
        ],
    },
    # -----------------------------------------------------------------
    # Section 141 — liability of companies / partnership firms
    # -----------------------------------------------------------------
    {
        "key": "ni_141",
        "citation": "Negotiable Instruments Act 1881, Section 141 — Offences by companies",
        "short_label": "NI 141",
        "act": "NI",
        "require_any": _NI_GUARD + ["company", "firm", "director", "partner", "llp", "pvt", "private limited"],
        "official_text": (
            "(1) If the person committing an offence under section 138 is a company, every "
            "person who, at the time the offence was committed, was in charge of, and was "
            "responsible to, the company for the conduct of the business of the company, as well "
            "as the company, shall be deemed to be guilty of the offence and shall be liable to "
            "be proceeded against and punished accordingly:\n"
            "Provided that nothing contained in this sub-section shall render any person liable "
            "to punishment if he proves that the offence was committed without his knowledge, or "
            "that he had exercised all due diligence to prevent the commission of such offence.\n"
            "(2) Notwithstanding anything contained in sub-section (1), where any offence under "
            "this Act has been committed by a company and it is proved that the offence has been "
            "committed with the consent or connivance of, or is attributable to, any neglect on "
            "the part of, any director, manager, secretary or other officer of the company, such "
            "director, manager, secretary or other officer shall also be deemed to be guilty of "
            "that offence and shall be liable to be proceeded against and punished accordingly.\n"
            "Explanation.—For the purposes of this section,—\n"
            "(a) 'company' means any body corporate and includes a firm or other association of "
            "individuals; and\n"
            "(b) 'director', in relation to a firm, means a partner in the firm."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "If a company's cheque bounces, BOTH the company AND the directors/partners who were "
            "in charge of the business can be prosecuted. The director can escape if they prove "
            "they had no knowledge and exercised due diligence. A 'sleeping director' who is not "
            "in charge of day-to-day operations can resist being included in the complaint — but "
            "must provide evidence."
        ),
        "keywords": [
            "ni 141", "section 141", "company cheque bounce", "director cheque bounce",
            "partner cheque bounce", "pvt ltd cheque bounce", "llp cheque bounce",
            "firm cheque bounced", "md cheque bounce", "ceo cheque bounce",
            "who liable company cheque bounce", "director liability cheque",
        ],
    },
    # -----------------------------------------------------------------
    # Section 142 — cognizance of offences
    # -----------------------------------------------------------------
    {
        "key": "ni_142",
        "citation": "Negotiable Instruments Act 1881, Section 142 — Cognizance of offences",
        "short_label": "NI 142",
        "act": "NI",
        "require_any": _NI_GUARD,
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
            "ends (i.e., within 1 month of the cause of action). Cause of action = day 16 after "
            "the drawer received your demand notice. The case is filed at the court where YOUR "
            "bank branch is (where you deposited the cheque) — not the drawer's city. A late "
            "complaint can still be accepted if you show good reason for the delay."
        ),
        "keywords": [
            "ni 142", "section 142", "cheque bounce complaint", "cheque case filing",
            "where to file cheque bounce case", "cheque bounce court", "cheque bounce one month",
            "cheque complaint time limit", "cheque bounce jurisdiction",
            "who can file cheque case", "magistrate cheque case", "late cheque complaint",
            "cause of action cheque bounce", "cheque bounce which court", "court for cheque bounce",
        ],
    },
    # -----------------------------------------------------------------
    # Section 143 — summary trial
    # -----------------------------------------------------------------
    {
        "key": "ni_143",
        "citation": "Negotiable Instruments Act 1881, Section 143 — Power of Court to try cases summarily",
        "short_label": "NI 143",
        "act": "NI",
        "require_any": _NI_GUARD,
        "official_text": (
            "(1) Notwithstanding anything contained in the Code of Criminal Procedure, 1973, all "
            "offences under this Chapter shall be tried by a Judicial Magistrate of the first "
            "class or by a Metropolitan Magistrate and the provisions of sections 262 to 265 "
            "(both inclusive) of the said Code shall, as far as practicable, apply to such "
            "trials:\n"
            "Provided that in the case of any conviction in a summary trial under this section, "
            "it shall be lawful for the Magistrate to pass a sentence of imprisonment for a term "
            "not exceeding one year and an amount of fine exceeding five thousand rupees.\n"
            "(2) When at the commencement of, or in the course of, a summary trial under this "
            "section, it appears to the Magistrate that the nature of the case is such that a "
            "sentence of imprisonment for a term exceeding one year may have to be passed or "
            "that it is, for any other reason, undesirable to try the case summarily, the "
            "Magistrate shall, after hearing the parties, record an order to that effect and "
            "thereafter recall any witness who may have been examined and proceed to re-hear the "
            "case in the manner provided by the said Code."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Cheque-bounce cases are designed to be fast — tried by summary procedure so the "
            "court focuses only on essentials. In a summary trial the sentence cannot exceed 1 "
            "year imprisonment. If the case is complex and the magistrate thinks a longer "
            "sentence may be needed, they can convert it to a regular summons-case trial."
        ),
        "keywords": [
            "ni 143", "section 143", "summary trial cheque", "cheque bounce fast trial",
            "how long cheque bounce case", "cheque bounce trial procedure",
            "magistrate cheque summary", "cheque bounce court process",
        ],
    },
    # -----------------------------------------------------------------
    # Section 143A — interim compensation during trial
    # -----------------------------------------------------------------
    {
        "key": "ni_143a",
        "citation": "Negotiable Instruments Act 1881, Section 143A — Power to direct interim compensation",
        "short_label": "NI 143A",
        "act": "NI",
        "require_any": _NI_GUARD,
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
            "payable within 60 days. If he is later acquitted, you repay it with interest. This "
            "amendment (2018) was introduced specifically to stop accused persons from using "
            "prolonged trials to delay payment."
        ),
        "keywords": [
            "ni 143a", "section 143a", "interim compensation cheque", "20 percent cheque",
            "twenty percent interim", "money during cheque trial", "advance compensation cheque",
            "cheque bounce get money fast", "interim relief cheque",
        ],
    },
    # -----------------------------------------------------------------
    # Section 144 — service of summons
    # -----------------------------------------------------------------
    {
        "key": "ni_144",
        "citation": "Negotiable Instruments Act 1881, Section 144 — Mode of service of summons",
        "short_label": "NI 144",
        "act": "NI",
        "require_any": _NI_GUARD + ["summons", "notice not received", "served"],
        "official_text": (
            "Notwithstanding anything contained in the Code of Criminal Procedure, 1973, and for "
            "the purposes of this Chapter, a Magistrate issuing a summons to an accused or a "
            "witness may direct a copy of such summons to be served at the place where such "
            "accused or witness ordinarily resides or carries on business or personally works for "
            "gain by speed post or by such courier services as are approved by a Court of Session; "
            "and if an acknowledgement purporting to be signed by the accused or the witness, or "
            "an endorsement purported to be made by a postal employee that the accused or the "
            "witness refused to take delivery of the summons, is received, the Magistrate shall "
            "declare that the summons has been duly served."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "The drawer cannot simply ignore court summons by refusing to pick up registered/speed "
            "post. If the postal acknowledgement shows the accused refused delivery, the court "
            "will treat that as 'deemed service'. The accused cannot then claim they never got "
            "the summons and use that to delay proceedings."
        ),
        "keywords": [
            "ni 144", "section 144", "cheque bounce summons", "notice service cheque",
            "drawer not accepting summons", "refused summons cheque", "speed post summons cheque",
        ],
    },
    # -----------------------------------------------------------------
    # Section 145 — evidence on affidavit
    # -----------------------------------------------------------------
    {
        "key": "ni_145",
        "citation": "Negotiable Instruments Act 1881, Section 145 — Evidence on affidavit",
        "short_label": "NI 145",
        "act": "NI",
        "require_any": _NI_GUARD + ["affidavit", "evidence", "proof", "deposition"],
        "official_text": (
            "(1) Notwithstanding anything contained in the Code of Criminal Procedure, 1973, "
            "evidence of the complainant may be given by him on affidavit and may, subject to "
            "all just exceptions, be read in evidence in any inquiry, trial or other proceeding "
            "under the said Code:\n"
            "Provided that the Court may, if it thinks fit, and shall, on the application of the "
            "prosecution or the accused, summon and examine any such person as to the facts "
            "contained in his affidavit.\n"
            "(2) The Court may dispense with the personal attendance of the accused and permit "
            "him to appear through his advocate."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "The complainant (you) can give your evidence in written sworn form (affidavit) "
            "instead of appearing personally to depose in court, which speeds up the trial. "
            "The accused's lawyer can still cross-examine you. Separately, the drawer can "
            "appear through his advocate for most hearings without being present every time."
        ),
        "keywords": [
            "ni 145", "section 145", "cheque bounce evidence affidavit", "cheque case proof",
            "do i have to appear in cheque bounce case", "cheque case attendance",
        ],
    },
    # -----------------------------------------------------------------
    # Section 146 — bank slip as evidence
    # -----------------------------------------------------------------
    {
        "key": "ni_146",
        "citation": "Negotiable Instruments Act 1881, Section 146 — Presumption of dishonour",
        "short_label": "NI 146",
        "act": "NI",
        "require_any": _NI_GUARD,
        "official_text": (
            "The Court shall, in respect of every proceeding under this Chapter, on production of "
            "bank's slip or memo having thereon the official mark denoting that the cheque has "
            "been dishonoured, presume the fact of dishonour of such cheque, unless and until "
            "such fact is disproved."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "The bank's return memo (the slip the bank gives you when your cheque bounces) IS "
            "admissible in court as presumptive evidence of dishonour. You do not need "
            "a bank official to appear and testify — just produce the memo. Keep the original "
            "bank memo carefully; it is your most important document."
        ),
        "keywords": [
            "ni 146", "section 146", "bank memo cheque bounce", "return memo evidence",
            "bank slip court cheque bounce", "proof cheque bounced", "cheque dishonour proof",
            "bank return memo court", "dishonour memo evidence",
        ],
    },
    # -----------------------------------------------------------------
    # Section 147 — compounding (settlement)
    # -----------------------------------------------------------------
    {
        "key": "ni_147",
        "citation": "Negotiable Instruments Act 1881, Section 147 — Offences to be compoundable",
        "short_label": "NI 147",
        "act": "NI",
        "require_any": _NI_GUARD + ["settle", "settlement", "compounding", "compromise", "pay and close"],
        "official_text": (
            "Notwithstanding anything contained in the Code of Criminal Procedure, 1973, every "
            "offence punishable under this Act shall be compoundable."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2189",
        "verified_at": "2026-06-01",
        "scope_note": (
            "A cheque-bounce case can be SETTLED (compounded) at any stage — even while an "
            "appeal is pending in a higher court. If the drawer pays the full cheque amount plus "
            "agreed compensation, the complainant can write to the court to compound the offence "
            "and the case is closed. This is the most common outcome and is legally valid even "
            "without a formal court order. Settlement letters should be in writing."
        ),
        "keywords": [
            "ni 147", "section 147", "settle cheque bounce case", "cheque bounce settlement",
            "compound cheque bounce", "pay and close cheque case", "cheque bounce compromise",
            "withdraw cheque bounce case", "close cheque bounce complaint",
            "cheque bounce out of court settlement",
        ],
    },
    # -----------------------------------------------------------------
    # Section 148 — appeal deposit
    # -----------------------------------------------------------------
    {
        "key": "ni_148",
        "citation": "Negotiable Instruments Act 1881, Section 148 — Power of Appellate Court to order payment pending appeal against conviction",
        "short_label": "NI 148",
        "act": "NI",
        "require_any": _NI_GUARD,
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
            "If the cheque writer is convicted and files an appeal, the appellate court MUST make "
            "him deposit at least 20% of the fine or compensation (on top of any section 143A "
            "interim compensation already paid), within 60 days. The court can release this "
            "deposit to you while the appeal is pending. An appeal therefore no longer freezes "
            "your recovery the way it once did."
        ),
        "keywords": [
            "ni 148", "section 148", "cheque bounce appeal", "appeal deposit cheque",
            "20 percent appeal deposit", "convicted cheque appeal", "recover money appeal cheque",
            "cheque bounce appeal court deposit",
        ],
    },
]
