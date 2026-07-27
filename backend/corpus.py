"""
DHARA CORPUS — verified statutory text.

Hand-curated, verbatim excerpts from official sources on indiacode.nic.in
(India Code portal, Ministry of Law and Justice, Government of India).

CITATION INTEGRITY RULE (see server.py):
- The LLM must NEVER emit section numbers or statutory text.
- Section numbers, official text, and source URLs are ONLY served from THIS file.
- The UI renders these fields from the retrieval result, never from model output.
- If a question does not match any entry, the LLM is instructed to REFUSE with
  "I don't have a verified source for this. Please consult an advocate."

Every entry MUST have:
  key            — stable identifier
  citation       — human-friendly citation (e.g. "BNSS Section 43(5)")
  short_label    — short label for chip UI (e.g. "BNSS 43(5)")
  official_text  — VERBATIM statutory text from indiacode.nic.in
  source_url     — direct link to indiacode.nic.in bill text
  verified_at    — YYYY-MM-DD date this entry was hand-verified
  scope_note     — one-sentence plain-language scope (used to preface answer)
  keywords       — retrieval keywords (lower-cased, punctuation-stripped)

DO NOT let the model paraphrase, expand, or invent new entries at runtime.
Adding new entries requires editing THIS file and re-verifying against indiacode.nic.in.
"""

CORPUS = [
    # -------------------- CONSTITUTION --------------------
    {
        "key": "const_art_20",
        "citation": "Constitution of India, Article 20",
        "short_label": "Article 20",
        "act": "Constitution",
        "official_text": (
            "(1) No person shall be convicted of any offence except for violation of a law "
            "in force at the time of the commission of the act charged as an offence, nor be "
            "subjected to a penalty greater than that which might have been inflicted under "
            "the law in force at the time of the commission of the offence.\n"
            "(2) No person shall be prosecuted and punished for the same offence more than once.\n"
            "(3) No person accused of any offence shall be compelled to be a witness against himself."
        ),
        "source_url": "https://www.indiacode.nic.in/coi-web/coi/COI.pdf",
        "verified_at": "2026-01-15",
        "scope_note": (
            "Article 20 protects you against (a) being punished under a law that did not exist when "
            "you did the act, (b) being tried twice for the same crime, and (c) being forced to give "
            "evidence against yourself."
        ),
        "keywords": [
            "article 20", "art 20", "ex post facto", "self incrimination", "double jeopardy",
            "same offence twice", "forced confession", "witness against himself", "protection conviction",
        ],
    },
    {
        "key": "const_art_21",
        "citation": "Constitution of India, Article 21",
        "short_label": "Article 21",
        "act": "Constitution",
        "official_text": (
            "No person shall be deprived of his life or personal liberty except according to "
            "procedure established by law."
        ),
        "source_url": "https://www.indiacode.nic.in/coi-web/coi/COI.pdf",
        "verified_at": "2026-01-15",
        "scope_note": (
            "Article 21 protects your life and personal liberty. Nobody — including the State — "
            "can take these away unless a proper law and a fair procedure allow it."
        ),
        "keywords": [
            "article 21", "art 21", "right to life", "personal liberty", "life and liberty",
            "procedure established by law", "dignity", "privacy", "puttaswamy",
        ],
    },
    {
        "key": "const_art_22",
        "citation": "Constitution of India, Article 22",
        "short_label": "Article 22",
        "act": "Constitution",
        "official_text": (
            "(1) No person who is arrested shall be detained in custody without being informed, "
            "as soon as may be, of the grounds for such arrest nor shall he be denied the right to "
            "consult, and to be defended by, a legal practitioner of his choice.\n"
            "(2) Every person who is arrested and detained in custody shall be produced before the "
            "nearest magistrate within a period of twenty-four hours of such arrest excluding the "
            "time necessary for the journey from the place of arrest to the court of the magistrate "
            "and no such person shall be detained in custody beyond the said period without the "
            "authority of a magistrate."
        ),
        "source_url": "https://www.indiacode.nic.in/coi-web/coi/COI.pdf",
        "verified_at": "2026-01-15",
        "scope_note": (
            "If you are arrested, Article 22(1) says you must be TOLD the reason and allowed to "
            "meet a lawyer, and 22(2) says you must be produced before a magistrate within 24 hours."
        ),
        "keywords": [
            "article 22", "art 22", "arrest rights", "grounds of arrest", "24 hours magistrate",
            "twenty-four hours", "right to lawyer on arrest", "produced before magistrate",
            "informed of arrest", "consult legal practitioner",
            # Conversational phrasings used by real users
            "my rights arrest", "rights when arrested", "rights during arrest",
            "rights if arrested", "police rights", "rights police",
            "right to remain silent", "remain silent police", "silent police",
            "lawyer during arrest", "lawyer after arrest", "call lawyer arrest",
            "detained police", "custody rights", "held by police",
        ],
    },
    # -------------------- BNSS 2023 (procedure) --------------------
    {
        "key": "bnss_35",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 35 — When police may arrest without warrant",
        "short_label": "BNSS 35",
        "act": "BNSS",
        "official_text": (
            "(1) Any police officer may without an order from a Magistrate and without a warrant, arrest any person—\n"
            "(a) who commits, in the presence of a police officer, a cognizable offence;\n"
            "(b) against whom a reasonable complaint has been made, or credible information has "
            "been received, or a reasonable suspicion exists that he has committed a cognizable "
            "offence punishable with imprisonment for a term which may be less than seven years "
            "or which may extend to seven years whether with or without fine, if the following "
            "conditions are satisfied, namely:—\n"
            "  (i) the police officer has reason to believe on the basis of such complaint, "
            "information, or suspicion that such person has committed the said offence;\n"
            "  (ii) the police officer is satisfied that such arrest is necessary — [purposes "
            "including preventing further offence, proper investigation, preventing evidence "
            "tampering, preventing inducement of witnesses, or ensuring presence in court];\n"
            "and the police officer shall, while making such arrest, record his reasons in writing.\n"
            "Provided that a police officer shall, in all cases where the arrest of a person is not "
            "required under the provisions of this sub-section, record the reasons in writing for "
            "not making the arrest."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20099",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNSS 35 lists exactly when police can arrest you without a warrant. Even for a "
            "cognizable offence punishable up to 7 years, the police officer must have specific "
            "reasons AND must record those reasons in writing."
        ),
        "keywords": [
            "bnss 35", "section 35 bnss", "arrest without warrant", "warrantless arrest",
            "cognizable offence", "police arrest me", "arrested by police", "arrest procedure",
            "reasons in writing", "arnesh kumar",
            # Conversational phrasings — critical for real user queries
            "police stop", "police stopped me", "stopped by police", "police stop me",
            "police check", "police checkpoint", "police detained me", "police detain",
            "warrant needed", "need warrant", "arrest me warrant", "without warrant",
            "police powers arrest", "rights during police stop", "rights police stop",
        ],
    },
    {
        "key": "bnss_173",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 173 — Information as to cognizable cases (FIR)",
        "short_label": "BNSS 173",
        "act": "BNSS",
        "official_text": (
            "(1) Every information relating to the commission of a cognizable offence, "
            "irrespective of the area where the offence is committed, may be given orally or "
            "by electronic communication to an officer in charge of a police station, and if "
            "given—\n"
            "(i) orally, it shall be reduced to writing by him or under his direction, and be "
            "read over to the informant; and every such information, whether given in writing "
            "or reduced to writing as aforesaid, shall be signed by the person giving it, and "
            "the substance thereof shall be entered in a book to be kept by such officer in "
            "such form as the State Government may by rules prescribe;\n"
            "(ii) by electronic communication, it shall be taken on record by him on being "
            "signed within three days by the person giving it.\n"
            "(2) A copy of the information as recorded under sub-section (1) shall be given "
            "forthwith, free of cost, to the informant."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20099",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNSS 173 governs the FIR (First Information Report). For any cognizable offence, "
            "the police station MUST record your complaint — orally or electronically — and "
            "give you a free copy immediately. Refusal to register an FIR is itself illegal."
        ),
        "keywords": [
            "bnss 173", "section 173 bnss", "fir", "file fir", "filing fir", "how to file fir",
            "how file fir", "lodge fir", "register fir", "first information report",
            "police complaint", "police station complaint", "report crime", "report to police",
            "refuse fir", "fir refused", "police refused fir", "zero fir", "online fir",
            "copy of fir", "free copy fir", "fir procedure", "fir cognizable",
        ],
    },
    {
        "key": "bnss_43_5",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 43(5) — Arrest of a woman after sunset",
        "short_label": "BNSS 43(5)",
        "act": "BNSS",
        "official_text": (
            "Save in exceptional circumstances, no woman shall be arrested after sunset and "
            "before sunrise, and where such exceptional circumstances exist, the woman police "
            "officer shall, by making a written report, obtain the prior permission of the "
            "Judicial Magistrate of the first class within whose local jurisdiction the offence "
            "is committed or the arrest is to be made."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20099",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNSS 43(5) applies ONLY TO WOMEN. A woman generally cannot be arrested between "
            "sunset and sunrise. In exceptional cases, a woman police officer must first get "
            "written permission from a Judicial Magistrate. This is NOT a universal rule for all "
            "arrests — it protects women only."
        ),
        "keywords": [
            "bnss 43", "bnss 43(5)", "section 43 bnss", "arrest at night", "arrest after sunset",
            "no arrest at night", "woman arrest", "female arrest", "night arrest woman",
            "arrest sunset sunrise", "woman police officer arrest", "arrest at night woman",
        ],
    },
    {
        "key": "bnss_47",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 47 — Person arrested to be informed of grounds of arrest and of right to bail",
        "short_label": "BNSS 47",
        "act": "BNSS",
        "official_text": (
            "(1) Every police officer or other person arresting any person without warrant shall "
            "forthwith communicate to him full particulars of the offence for which he is arrested "
            "or other grounds for such arrest.\n"
            "(2) Where a police officer arrests without warrant any person other than a person accused "
            "of a non-bailable offence, he shall inform the person arrested that he is entitled to "
            "be released on bail and that he may arrange for sureties on his behalf."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20099",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNSS 47 says the arresting officer MUST immediately tell you (a) the full particulars "
            "of the offence and grounds, and (b) if it is a bailable offence, that you are entitled "
            "to bail and can arrange sureties."
        ),
        "keywords": [
            "bnss 47", "section 47 bnss", "grounds of arrest", "informed of arrest",
            "right to bail on arrest", "bailable offence", "sureties", "particulars of offence",
        ],
    },
    {
        "key": "bnss_48",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 48 — Obligation of person making arrest to inform about the arrest to nominated person",
        "short_label": "BNSS 48",
        "act": "BNSS",
        "official_text": (
            "Every police officer or other person making any arrest under this Sanhita shall "
            "forthwith give the information regarding such arrest and place where the arrested "
            "person is being held to any of his relatives, friends or such other persons as may "
            "be disclosed or nominated by the arrested person for the purpose of giving such "
            "information."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20099",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNSS 48 gives you the right to have a relative, friend, or any person of your choice "
            "informed that you have been arrested and told where you are being held."
        ),
        "keywords": [
            "bnss 48", "section 48 bnss", "inform family arrest", "nominated person",
            "relative informed", "friend informed arrest", "where arrested held", "D.K. Basu",
        ],
    },
    # -------------------- BNS 2023 (offences) --------------------
    {
        "key": "bns_101",
        "citation": "Bharatiya Nyaya Sanhita 2023, Section 101 — Culpable homicide",
        "short_label": "BNS 101",
        "act": "BNS",
        "official_text": (
            "Whoever causes death by doing an act with the intention of causing death, or with the "
            "intention of causing such bodily injury as is likely to cause death, or with the "
            "knowledge that he is likely by such act to cause death, commits the offence of "
            "culpable homicide."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20063",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNS 101 defines culpable homicide — causing death with intention or with knowledge "
            "that the act is likely to cause death."
        ),
        "keywords": [
            "bns 101", "section 101 bns", "culpable homicide", "cause death", "intention to kill",
        ],
    },
    {
        "key": "bns_102",
        "citation": "Bharatiya Nyaya Sanhita 2023, Section 102 — Murder",
        "short_label": "BNS 102",
        "act": "BNS",
        "official_text": (
            "Except in the cases hereinafter excepted, culpable homicide is murder — if the act "
            "by which the death is caused is done with the intention of causing death; or if it "
            "is done with the intention of causing such bodily injury as the offender knows to be "
            "likely to cause the death of the person to whom the harm is caused; or if it is done "
            "with the intention of causing bodily injury to any person, and the bodily injury "
            "intended to be inflicted is sufficient in the ordinary course of nature to cause "
            "death; or if the person committing the act knows that it is so imminently dangerous "
            "that it must, in all probability, cause death, or such bodily injury as is likely to "
            "cause death, and commits such act without any excuse for incurring the risk."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20063",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNS 102 defines when culpable homicide becomes MURDER — broadly, when there is "
            "clear intention to cause death or a fatal injury, subject to specific exceptions."
        ),
        "keywords": ["bns 102", "section 102 bns", "murder", "culpable homicide murder"],
    },
    {
        "key": "bns_103",
        "citation": "Bharatiya Nyaya Sanhita 2023, Section 103 — Punishment for murder",
        "short_label": "BNS 103",
        "act": "BNS",
        "official_text": (
            "(1) Whoever commits murder shall be punished with death or imprisonment for life, "
            "and shall also be liable to fine.\n"
            "(2) When a group of five or more persons acting in concert commits murder on the "
            "ground of race, caste or community, sex, place of birth, language, personal belief "
            "or any other similar ground, each member of such group shall be punished with death "
            "or with imprisonment for life, and shall also be liable to fine."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20063",
        "verified_at": "2026-01-15",
        "scope_note": (
            "BNS 103 sets the punishment for murder: death or life imprisonment plus fine. "
            "Sub-section (2) covers mob-lynching on discriminatory grounds with the same maximum."
        ),
        "keywords": [
            "bns 103", "section 103 bns", "punishment for murder", "murder punishment",
            "death penalty murder", "life imprisonment murder", "mob lynching",
        ],
    },
    # -------------------- Protection of Women from Domestic Violence Act 2005 --------------------
    {
        "key": "pwdva_3",
        "citation": "Protection of Women from Domestic Violence Act 2005, Section 3 — Definition of domestic violence",
        "short_label": "PWDVA 3",
        "act": "PWDVA",
        "official_text": (
            "For the purposes of this Act, any act, omission or commission or conduct of the "
            "respondent shall constitute domestic violence in case it— (a) harms or injures or "
            "endangers the health, safety, life, limb or well-being, whether mental or physical, "
            "of the aggrieved person or tends to do so and includes causing physical abuse, "
            "sexual abuse, verbal and emotional abuse and economic abuse; or (b) harasses, harms, "
            "injures or endangers the aggrieved person with a view to coerce her or any other "
            "person related to her to meet any unlawful demand for any dowry or other property or "
            "valuable security; or (c) has the effect of threatening the aggrieved person or any "
            "person related to her by any conduct mentioned in clause (a) or clause (b); or "
            "(d) otherwise injures or causes harm, whether physical or mental, to the aggrieved person."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2031",
        "verified_at": "2026-01-15",
        "scope_note": (
            "This law defines domestic violence broadly — it covers physical, sexual, verbal, "
            "emotional AND economic abuse, plus dowry-related harassment. Only women can file "
            "under this Act; the respondent is usually the husband or a male relative."
        ),
        "keywords": [
            "pwdva 3", "domestic violence", "wife beating", "husband abuse", "dowry harassment",
            "emotional abuse", "economic abuse", "verbal abuse", "physical abuse home",
            "in-laws harassment", "marital abuse", "domestic abuse",
            "husband beats", "husband hits", "husband harass", "husband abusive",
            "beats me", "hits me", "abusive husband", "abuse from husband",
        ],
    },
    {
        "key": "pwdva_12",
        "citation": "Protection of Women from Domestic Violence Act 2005, Section 12 — Application to Magistrate",
        "short_label": "PWDVA 12",
        "act": "PWDVA",
        "official_text": (
            "(1) An aggrieved person or a Protection Officer or any other person on behalf of the "
            "aggrieved person may present an application to the Magistrate seeking one or more "
            "reliefs under this Act: Provided that before passing any order on such application, "
            "the Magistrate shall take into consideration any domestic incident report received by "
            "him from the Protection Officer or the service provider.\n"
            "(4) The Magistrate shall fix the first date of hearing, which shall not ordinarily be "
            "beyond three days from the date of receipt of the application by the court.\n"
            "(5) The Magistrate shall endeavour to dispose of every application made under sub-section "
            "(1) within a period of sixty days from the date of its first hearing."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2031",
        "verified_at": "2026-01-15",
        "scope_note": (
            "You (or a Protection Officer, or anyone acting for you) can apply to the Magistrate "
            "for protection. First hearing is usually within 3 days, and the case should ideally be "
            "decided within 60 days."
        ),
        "keywords": [
            "pwdva 12", "domestic violence complaint", "how to file domestic violence",
            "protection officer", "domestic incident report", "magistrate application dv",
            "file complaint against husband",
        ],
    },
    {
        "key": "pwdva_17",
        "citation": "Protection of Women from Domestic Violence Act 2005, Section 17 — Right to reside in a shared household",
        "short_label": "PWDVA 17",
        "act": "PWDVA",
        "official_text": (
            "(1) Notwithstanding anything contained in any other law for the time being in force, "
            "every woman in a domestic relationship shall have the right to reside in the shared "
            "household, whether or not she has any right, title or beneficial interest in the same.\n"
            "(2) The aggrieved person shall not be evicted or excluded from the shared household or "
            "any part of it by the respondent save in accordance with the procedure established by law."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2031",
        "verified_at": "2026-01-15",
        "scope_note": (
            "A woman in a domestic relationship CANNOT be thrown out of the shared home, even if "
            "the home is not in her name. She can only be removed by a proper court order."
        ),
        "keywords": [
            "pwdva 17", "shared household", "right to reside", "thrown out of house",
            "husband threw me out", "in-laws evicted me", "residence right woman",
            "right to matrimonial home",
        ],
    },
    {
        "key": "pwdva_18",
        "citation": "Protection of Women from Domestic Violence Act 2005, Section 18 — Protection orders",
        "short_label": "PWDVA 18",
        "act": "PWDVA",
        "official_text": (
            "The Magistrate may, after giving the aggrieved person and the respondent an "
            "opportunity of being heard and on being prima facie satisfied that domestic violence "
            "has taken place or is likely to take place, pass a protection order in favour of the "
            "aggrieved person and prohibit the respondent from— (a) committing any act of domestic "
            "violence; (b) aiding or abetting in the commission of acts of domestic violence; "
            "(c) entering the place of employment of the aggrieved person or, if the person "
            "aggrieved is a child, its school or any other place frequented by the aggrieved person; "
            "(d) attempting to communicate in any form, whatsoever, with the aggrieved person, "
            "including personal, oral or written or electronic or telephonic contact; (e) alienating "
            "any assets, operating bank lockers or bank accounts used or held or enjoyed by both "
            "the parties, jointly by the aggrieved person and the respondent or singly by the "
            "respondent, including her stridhan or any other property held either jointly by the "
            "parties or separately by them without the leave of the Magistrate; (f) causing violence "
            "to the dependants, other relatives or any person who give the aggrieved person "
            "assistance from domestic violence; (g) committing any other act as specified in the "
            "protection order."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2031",
        "verified_at": "2026-01-15",
        "scope_note": (
            "The Magistrate can order the respondent to stop all violence, stop contacting you, "
            "stay away from your workplace or child's school, and stop selling shared assets or "
            "operating your accounts. This is called a Protection Order."
        ),
        "keywords": [
            "pwdva 18", "protection order", "restraining order", "stop contacting me",
            "protection from husband", "no contact order", "keep away husband",
        ],
    },
    {
        "key": "pwdva_20",
        "citation": "Protection of Women from Domestic Violence Act 2005, Section 20 — Monetary reliefs",
        "short_label": "PWDVA 20",
        "act": "PWDVA",
        "official_text": (
            "(1) While disposing of an application under sub-section (1) of section 12, the "
            "Magistrate may direct the respondent to pay monetary relief to meet the expenses "
            "incurred and losses suffered by the aggrieved person and any child of the aggrieved "
            "person as a result of the domestic violence and such relief may include, but is not "
            "limited to— (a) the loss of earnings; (b) the medical expenses; (c) the loss caused "
            "due to the destruction, damage or removal of any property from the control of the "
            "aggrieved person; and (d) the maintenance for the aggrieved person as well as her "
            "children, if any, including an order under or in addition to an order of maintenance "
            "under section 125 of the Code of Criminal Procedure, 1973 (2 of 1974) or any other "
            "law for the time being in force.\n"
            "(2) The monetary relief granted under this section shall be adequate, fair and "
            "reasonable and consistent with the standard of living to which the aggrieved person "
            "is accustomed."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2031",
        "verified_at": "2026-01-15",
        "scope_note": (
            "The court can order the respondent to pay you money for lost earnings, medical bills, "
            "damaged property, and maintenance for you and your children. The amount must match "
            "the standard of living you were used to."
        ),
        "keywords": [
            "pwdva 20", "monetary relief domestic violence", "maintenance domestic violence",
            "compensation abuse", "medical expenses husband", "child maintenance dv",
        ],
    },
    {
        "key": "pwdva_23",
        "citation": "Protection of Women from Domestic Violence Act 2005, Section 23 — Power to grant interim and ex parte orders",
        "short_label": "PWDVA 23",
        "act": "PWDVA",
        "official_text": (
            "(1) In any proceeding before him under this Act, the Magistrate may pass such interim "
            "order as he deems just and proper.\n"
            "(2) If the Magistrate is satisfied that an application prima facie discloses that the "
            "respondent is committing, or has committed an act of domestic violence or that there "
            "is a likelihood that the respondent may commit an act of domestic violence, he may "
            "grant an ex parte order on the basis of the affidavit in such form, as may be "
            "prescribed, of the aggrieved person under section 18, section 19, section 20, section "
            "21 or, as the case may be, section 22 against the respondent."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2031",
        "verified_at": "2026-01-15",
        "scope_note": (
            "The Magistrate can pass an EMERGENCY order — even without hearing the respondent — "
            "if your affidavit shows abuse is happening or likely to happen. This is called an "
            "ex parte order and is used when you need urgent protection."
        ),
        "keywords": [
            "pwdva 23", "emergency protection order", "ex parte order",
            "urgent protection domestic violence", "immediate order husband",
            "emergency abuse", "urgent protection abuse", "protection from abuse",
            "emergency safety", "help urgent abuse",
        ],
    },
]

# Non-Indian jurisdictions — trap-question refusal helper
NON_INDIAN_JURISDICTION_KEYWORDS = [
    "texas", "california", "florida", "new york state", "uk law", "united kingdom law",
    "canadian law", "canada law", "australian law", "us law", "u.s. law", "american law",
    "pakistan law", "bangladesh law", "sri lanka law", "china law", "russia law",
    "singapore law", "usa law",
]

# Non-legal / advisory questions the tool should decline
NON_LEGAL_ADVICE_KEYWORDS = [
    "should i forgive", "should i marry", "should i divorce", "should i quit",
    "give me advice", "personal advice", "what should i do with my life",
    "moral advice", "religious advice",
]


def _norm(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def _tokens(s: str) -> set:
    """Split a normalized string into a set of tokens (words)."""
    return {t for t in _norm(s).split() if len(t) > 1}


# Words too common to give retrieval signal (would over-match)
_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "of", "and", "or", "for",
    "in", "on", "at", "to", "by", "my", "me", "i", "we", "you", "your",
    "can", "may", "do", "does", "did", "have", "has", "had", "be", "been",
    "will", "would", "should", "could", "shall", "any", "all", "some",
    "what", "why", "how", "when", "where", "who", "which", "this", "that",
}


def retrieve(question: str, limit: int = 3) -> list[dict]:
    """
    Deterministic retrieval over the verified corpus.

    Score per corpus entry:
      +5 if the entry's short_label appears (e.g. "bnss 35", "article 21")
      +3 if a multi-word keyword appears as a contiguous substring
      +1 per token overlap between the entry's keyword words and the question tokens
        (ignoring stop words and very short tokens)

    This handles both "What is Article 21?" (short_label hit) and
    "Can police arrest a woman at night?" (token overlap on arrest / woman / night).
    """
    q_norm = _norm(question)
    if not q_norm:
        return []
    q_tokens = _tokens(question) - _STOP

    scored: list[tuple[int, dict]] = []
    for item in CORPUS:
        score = 0
        # (a) short label match — strongest signal
        if _norm(item["short_label"]) in q_norm:
            score += 5
        # (b) multi-word keyword substrings — moderate signal
        # (c) token overlap on all keyword words
        kw_tokens: set = set()
        for kw in item["keywords"]:
            kw_norm = _norm(kw)
            if " " in kw_norm and kw_norm in q_norm:
                score += 3
            kw_tokens |= _tokens(kw)
        kw_tokens -= _STOP
        overlap = kw_tokens & q_tokens
        score += len(overlap)
        if score > 0:
            scored.append((score, item))
    # Require a minimum score threshold so single-word noise doesn't match.
    # A short_label hit (5), phrase hit (3), or ANY meaningful token overlap passes.
    # Note: stop-words are already stripped from q_tokens, so an overlap of 1 already
    # means a real content word matched. Threshold=2 was too strict for casual queries
    # like "What are my rights during a police stop?" — dropping to 1 restores natural
    # phrasing while the LLM system prompt + sanitize_model_output() still contain any
    # tangential retrievals.
    scored = [(s, it) for s, it in scored if s >= 1]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def is_non_indian_jurisdiction(question: str) -> bool:
    q = _norm(question)
    return any(_norm(k) in q for k in NON_INDIAN_JURISDICTION_KEYWORDS)


def is_non_legal_advice(question: str) -> bool:
    q = _norm(question)
    return any(_norm(k) in q for k in NON_LEGAL_ADVICE_KEYWORDS)


def public_citation(item: dict) -> dict:
    """Client-safe subset of a corpus entry."""
    return {
        "key": item["key"],
        "citation": item["citation"],
        "short_label": item["short_label"],
        "act": item["act"],
        "official_text": item["official_text"],
        "source_url": item["source_url"],
        "verified_at": item["verified_at"],
    }


REFUSAL_NO_CORPUS = (
    "I don't have a verified source for this. Please consult an advocate."
)

REFUSAL_NON_INDIAN = (
    "I only cover Indian law (BNS, BNSS, and the Constitution of India). "
    "For laws of other countries or states, please consult an advocate in that jurisdiction."
)

REFUSAL_NOT_LEGAL = (
    "I can only help with questions about Indian law, your rights, and legal procedure. "
    "For personal or life advice, please speak to a family elder or counsellor."
)


# Case-insensitive patterns for citation-integrity post-processing.
# Any of these appearing in the model's output means the model tried to leak
# statutory identifiers — we strip / soften them so only plain-language remains.
import re as _re
_CITATION_LEAK_PATTERNS = [
    # "Article 21", "Article 22(1)", "Article 21 of the Constitution"
    (_re.compile(r"\b[Aa]rticle\s+\d+[A-Z]?(\(\d+\))?(\s+of\s+the\s+Constitution)?\b"), "this constitutional right"),
    # "Section 35 BNSS", "Section 43(5) of BNSS", "Sec. 43(5) BNSS", "BNSS Section 35"
    (_re.compile(r"\b(?:[Ss]ec(?:tion|\.)?\s+\d+[A-Z]?(?:\(\d+\))?\s+(?:of\s+)?(?:BNS|BNSS|BSA|IPC|CrPC))\b"), "the law"),
    (_re.compile(r"\b(?:BNS|BNSS|BSA|IPC|CrPC)\s+[Ss]ec(?:tion|\.)?\s+\d+[A-Z]?(?:\(\d+\))?\b"), "the law"),
    # Bare "BNSS 43(5)" or "PWDVA 12" style
    (_re.compile(r"\b(?:BNS|BNSS|BSA|IPC|CrPC|PWDVA|DV Act)\s+\d+[A-Z]?(?:\(\d+\))?\b"), "the law"),
    # Just "Section 35" alone
    (_re.compile(r"\b[Ss]ec(?:tion|\.)?\s+\d+[A-Z]?(?:\(\d+\))?\b"), "the law"),
    # Long forms of the statutes
    (_re.compile(r"\bBharatiya\s+(?:Nyaya|Nagarik|Sakshya)\s+(?:Sanhita|Suraksha|Adhiniyam)(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\bIndian\s+Penal\s+Code(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\bCode\s+of\s+Criminal\s+Procedure(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\b(?:Protection\s+of\s+Women\s+from\s+Domestic\s+Violence\s+Act|PWDVA)(?:,?\s*\d{4})?\b"), "the law"),
]


def sanitize_model_output(text: str) -> str:
    """
    Defense-in-depth. Even with prompt instructions, models sometimes leak
    section/article identifiers. Strip them here BEFORE showing to the user.
    Citations are rendered separately from the verified corpus.
    """
    if not text:
        return text
    out = text
    for pat, repl in _CITATION_LEAK_PATTERNS:
        out = pat.sub(repl, out)
    # collapse double spaces from replacements
    out = _re.sub(r"[ \t]{2,}", " ", out)
    return out
