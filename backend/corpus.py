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
    # -------------------- Right to Information Act 2005 --------------------
    {
        "key": "rti_6",
        "citation": "Right to Information Act 2005, Section 6 — Request for obtaining information",
        "short_label": "RTI 6",
        "act": "RTI",
        "official_text": (
            "(1) A person, who desires to obtain any information under this Act, shall make a "
            "request in writing or through electronic means in English or Hindi or in the official "
            "language of the area in which the application is being made, accompanying such fee "
            "as may be prescribed, to—\n"
            "(a) the Central Public Information Officer or State Public Information Officer, as "
            "the case may be, of the concerned public authority;\n"
            "(b) the Central Assistant Public Information Officer or State Assistant Public "
            "Information Officer, as the case may be, specifying the particulars of the information "
            "sought by him or her:\n"
            "Provided that where such request cannot be made in writing, the Central Public "
            "Information Officer or State Public Information Officer, as the case may be, shall "
            "render all reasonable assistance to the person making the request orally to reduce the "
            "same in writing.\n"
            "(2) An applicant making request for information shall not be required to give any "
            "reason for requesting the information or any other personal details except those that "
            "may be necessary for contacting him."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1362",
        "verified_at": "2026-02-01",
        "scope_note": (
            "RTI Section 6 lets you ask any public authority for information in writing (or "
            "electronically) in English, Hindi, or the local language. You DO NOT need to give a "
            "reason. If you cannot write, the PIO must help you put your request in writing."
        ),
        "keywords": [
            "rti 6", "section 6 rti", "file rti", "filing rti", "how to file rti",
            "rti application", "rti request", "apply rti", "rti procedure",
            "public information officer", "pio", "spio", "cpio",
            "rti online", "rti fee", "rti in hindi", "rti local language",
            "right to information", "government information",
        ],
    },
    {
        "key": "rti_7",
        "citation": "Right to Information Act 2005, Section 7 — Disposal of request",
        "short_label": "RTI 7",
        "act": "RTI",
        "official_text": (
            "(1) Subject to the proviso to sub-section (2) of section 5 or the proviso to "
            "sub-section (3) of section 6, the Central Public Information Officer or State Public "
            "Information Officer, as the case may be, on receipt of a request under section 6 "
            "shall, as expeditiously as possible, and in any case within thirty days of the "
            "receipt of the request, either provide the information on payment of such fee as may "
            "be prescribed or reject the request for any of the reasons specified in sections 8 and 9:\n"
            "Provided that where the information sought for concerns the life or liberty of a "
            "person, the same shall be provided within forty-eight hours of the receipt of the "
            "request.\n"
            "(2) If the Central Public Information Officer or State Public Information Officer, "
            "as the case may be, fails to give decision on the request for information within the "
            "period specified under sub-section (1), the Central Public Information Officer or "
            "State Public Information Officer, as the case may be, shall be deemed to have refused "
            "the request.\n"
            "(6) Notwithstanding anything contained in sub-section (5), the person making request "
            "for the information shall be provided the information free of charge where a public "
            "authority fails to comply with the time limits specified in sub-section (1)."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1362",
        "verified_at": "2026-02-01",
        "scope_note": (
            "RTI Section 7 gives the government 30 days to reply to your RTI (48 hours if it "
            "concerns life or liberty). If they miss the deadline, you get the information FREE "
            "and it counts as a deemed refusal you can appeal."
        ),
        "keywords": [
            "rti 7", "section 7 rti", "rti 30 days", "rti timeline", "rti deadline",
            "rti reply time", "rti response time", "deemed refusal", "rti free",
            "rti not answered", "rti no reply", "rti delay", "48 hours rti",
            "life and liberty rti", "rti time limit",
        ],
    },
    {
        "key": "rti_19",
        "citation": "Right to Information Act 2005, Section 19 — Appeal",
        "short_label": "RTI 19",
        "act": "RTI",
        "official_text": (
            "(1) Any person who does not receive a decision within the time specified in "
            "sub-section (1) or clause (a) of sub-section (3) of section 7, or is aggrieved by a "
            "decision of the Central Public Information Officer or State Public Information "
            "Officer, as the case may be, may within thirty days from the expiry of such period or "
            "from the receipt of such a decision prefer an appeal to such officer who is senior in "
            "rank to the Central Public Information Officer or State Public Information Officer, "
            "as the case may be, in each public authority.\n"
            "(3) A second appeal against the decision under sub-section (1) shall lie within "
            "ninety days from the date on which the decision should have been made or was actually "
            "received, with the Central Information Commission or the State Information Commission."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1362",
        "verified_at": "2026-02-01",
        "scope_note": (
            "If your RTI is refused or ignored, you can file a FIRST APPEAL within 30 days to a "
            "senior officer in the same department. If still not satisfied, a SECOND APPEAL goes "
            "to the Central or State Information Commission within 90 days."
        ),
        "keywords": [
            "rti 19", "section 19 rti", "rti appeal", "rti first appeal", "rti second appeal",
            "first appellate authority", "information commission", "central information commission",
            "state information commission", "cic", "sic", "rti refused appeal",
            "how to appeal rti", "rti complaint",
        ],
    },
    {
        "key": "rti_20",
        "citation": "Right to Information Act 2005, Section 20 — Penalties",
        "short_label": "RTI 20",
        "act": "RTI",
        "official_text": (
            "(1) Where the Central Information Commission or the State Information Commission, "
            "as the case may be, at the time of deciding any complaint or appeal is of the opinion "
            "that the Central Public Information Officer or the State Public Information Officer, "
            "as the case may be, has, without any reasonable cause, refused to receive an "
            "application for information or has not furnished information within the time "
            "specified under sub-section (1) of section 7 or malafidely denied the request for "
            "information or knowingly given incorrect, incomplete or misleading information or "
            "destroyed information which was the subject of the request or obstructed in any "
            "manner in furnishing the information, it shall impose a penalty of two hundred and "
            "fifty rupees each day till application is received or information is furnished, so "
            "however, the total amount of such penalty shall not exceed twenty-five thousand rupees:\n"
            "Provided that the Central Public Information Officer or the State Public Information "
            "Officer, as the case may be, shall be given a reasonable opportunity of being heard "
            "before any penalty is imposed on him."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1362",
        "verified_at": "2026-02-01",
        "scope_note": (
            "RTI Section 20 lets the Information Commission fine the PIO ₹250 per day (up to "
            "₹25,000) if they wrongly refuse your RTI, delay it, or give false / incomplete "
            "information. This penalty comes out of the officer's salary."
        ),
        "keywords": [
            "rti 20", "section 20 rti", "rti penalty", "penalty pio", "pio fine",
            "rti punishment", "action against pio", "fine information officer",
            "wrong rti reply", "false rti reply", "misleading rti",
        ],
    },
    # -------------------- Consumer Protection Act 2019 --------------------
    {
        "key": "cpa_2_7",
        "citation": "Consumer Protection Act 2019, Section 2(7) — Definition of consumer",
        "short_label": "CPA 2(7)",
        "act": "CPA",
        "official_text": (
            "'consumer' means any person who—\n"
            "(i) buys any goods for a consideration which has been paid or promised or partly "
            "paid and partly promised, or under any system of deferred payment and includes any "
            "user of such goods other than the person who buys such goods for consideration paid "
            "or promised or partly paid or partly promised, or under any system of deferred "
            "payment, when such use is made with the approval of such person, but does not include "
            "a person who obtains such goods for resale or for any commercial purpose; or\n"
            "(ii) hires or avails of any service for a consideration which has been paid or "
            "promised or partly paid and partly promised, or under any system of deferred payment "
            "and includes any beneficiary of such service other than the person who hires or "
            "avails of the services for consideration paid or promised, or partly paid and partly "
            "promised, or under any system of deferred payment, when such services are availed of "
            "with the approval of the first mentioned person, but does not include a person who "
            "avails of such service for any commercial purpose.\n"
            "Explanation.—For the purposes of this clause,—\n"
            "(a) the expression 'commercial purpose' does not include use by a person of goods "
            "bought and used by him exclusively for the purpose of earning his livelihood, by "
            "means of self-employment;\n"
            "(b) the expressions 'buys any goods' and 'hires or avails any services' includes "
            "offline or online transactions through electronic means or by teleshopping or direct "
            "selling or multi-level marketing."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/15256",
        "verified_at": "2026-02-01",
        "scope_note": (
            "You are a CONSUMER under this law if you paid for goods or services (offline OR "
            "online) for personal use — not for resale or business. Family members who use what "
            "you bought are also protected."
        ),
        "keywords": [
            "cpa 2", "cpa 2(7)", "section 2 consumer protection", "who is a consumer",
            "consumer definition", "am i a consumer", "online purchase consumer",
            "buyer rights", "customer rights", "e-commerce consumer",
        ],
    },
    {
        "key": "cpa_34",
        "citation": "Consumer Protection Act 2019, Section 34 — Jurisdiction of District Commission",
        "short_label": "CPA 34",
        "act": "CPA",
        "official_text": (
            "(1) Subject to the other provisions of this Act, the District Commission shall have "
            "jurisdiction to entertain complaints where the value of the goods or services paid as "
            "consideration does not exceed fifty lakh rupees.\n"
            "(2) A complaint shall be instituted in a District Commission within the local limits "
            "of whose jurisdiction,—\n"
            "(a) the opposite party or each of the opposite parties, where there are more than "
            "one, at the time of the institution of the complaint, ordinarily resides or carries "
            "on business or has a branch office or personally works for gain; or\n"
            "(b) any of the opposite parties, where there are more than one, at the time of the "
            "institution of the complaint, actually and voluntarily resides, or carries on "
            "business or has a branch office, or personally works for gain, provided that in such "
            "case the permission of the District Commission is given; or\n"
            "(c) the cause of action, wholly or in part, arises; or\n"
            "(d) the complainant resides or personally works for gain."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/15256",
        "verified_at": "2026-02-01",
        "scope_note": (
            "For consumer complaints up to ₹50 lakh, file at the DISTRICT Commission. You can "
            "file where the seller does business, where the transaction happened, OR where you "
            "yourself live — you no longer have to travel to the seller's city."
        ),
        "keywords": [
            "cpa 34", "section 34 consumer", "district commission", "district consumer forum",
            "where to file consumer complaint", "consumer complaint jurisdiction",
            "50 lakh consumer", "pecuniary jurisdiction consumer",
            "consumer court location", "consumer forum near me",
        ],
    },
    {
        "key": "cpa_35",
        "citation": "Consumer Protection Act 2019, Section 35 — Manner in which complaint shall be made",
        "short_label": "CPA 35",
        "act": "CPA",
        "official_text": (
            "(1) A complaint, in relation to any goods sold or delivered or agreed to be sold or "
            "delivered or any service provided or agreed to be provided, may be filed with a "
            "District Commission by—\n"
            "(a) the consumer,—\n"
            "  (i) to whom such goods are sold or delivered or agreed to be sold or delivered or "
            "such service is provided or agreed to be provided; or\n"
            "  (ii) who alleges unfair trade practice in respect of such goods or service;\n"
            "(b) any recognised consumer association, whether the consumer to whom such goods are "
            "sold or delivered or agreed to be sold or delivered or such service is provided or "
            "agreed to be provided, or who alleges unfair trade practice, is a member of such "
            "association or not;\n"
            "(c) one or more consumers, where there are numerous consumers having the same "
            "interest, with the permission of the District Commission, on behalf of, or for the "
            "benefit of, all consumers so interested;\n"
            "(d) the Central Government, the Central Authority or the State Government, as the "
            "case may be:\n"
            "Provided that the complaint under this sub-section may be filed electronically in "
            "such manner as may be prescribed."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/15256",
        "verified_at": "2026-02-01",
        "scope_note": (
            "You can file a consumer complaint yourself, or through a recognised consumer group. "
            "Complaints can now be filed ONLINE via the e-Daakhil portal (edaakhil.nic.in)."
        ),
        "keywords": [
            "cpa 35", "section 35 consumer", "how to file consumer complaint",
            "file consumer case", "consumer court complaint", "e-daakhil", "edaakhil",
            "online consumer complaint", "consumer helpline", "cheated by seller",
            "faulty product", "defective goods", "bad service complaint",
            "shopkeeper cheated", "online shopping fraud",
        ],
    },
    {
        "key": "cpa_69",
        "citation": "Consumer Protection Act 2019, Section 69 — Limitation period",
        "short_label": "CPA 69",
        "act": "CPA",
        "official_text": (
            "(1) The District Commission, the State Commission or the National Commission shall "
            "not admit a complaint unless it is filed within two years from the date on which the "
            "cause of action has arisen.\n"
            "(2) Notwithstanding anything contained in sub-section (1), a complaint may be "
            "entertained after the period specified in sub-section (1), if the complainant "
            "satisfies the District Commission, the State Commission or the National Commission, "
            "as the case may be, that he had sufficient cause for not filing the complaint within "
            "such period:\n"
            "Provided that no such complaint shall be entertained unless the District Commission "
            "or the State Commission or the National Commission, as the case may be, records its "
            "reasons for condoning such delay."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/15256",
        "verified_at": "2026-02-01",
        "scope_note": (
            "You must file your consumer complaint within TWO YEARS from the date the problem "
            "arose. Later than that, the court can still accept it only if you show a good reason "
            "for the delay."
        ),
        "keywords": [
            "cpa 69", "section 69 consumer", "consumer complaint time limit",
            "consumer limitation", "2 years consumer", "two years consumer complaint",
            "old consumer complaint", "delayed consumer complaint",
        ],
    },
    # -------------------- Motor Vehicles Act 1988 (as amended 2019) --------------------
    {
        "key": "mv_129",
        "citation": "Motor Vehicles Act 1988, Section 129 — Wearing of protective headgear",
        "short_label": "MV 129",
        "act": "MV",
        "official_text": (
            "Every person, above four years of age, driving or riding or being carried on a "
            "motor cycle of any class or description shall, while in a public place, wear "
            "protective headgear conforming to such standards as may be prescribed by the "
            "Central Government:\n"
            "Provided that the provisions of this section shall not apply to a person who is a "
            "Sikh, if he is, while driving or riding on the motor cycle, in a public place, "
            "wearing a turban:\n"
            "Provided further that the Central Government may by rules provide for measures for "
            "the safety of children below four years of age riding or being carried on a motor cycle.\n"
            "Explanation.—'Protective headgear' means a helmet which—\n"
            "(a) by virtue of its shape, material and construction, could reasonably be expected "
            "to afford to the person driving or riding on a motor cycle a degree of protection "
            "from injury in the event of an accident; and\n"
            "(b) is fastened to the head of the wearer by means of straps or other fastenings "
            "provided on the headgear."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1798",
        "verified_at": "2026-02-01",
        "scope_note": (
            "Everyone above 4 years — driver AND pillion — must wear a proper BIS-certified "
            "helmet on a two-wheeler in public. Sikhs wearing a turban are exempted."
        ),
        "keywords": [
            "mv 129", "section 129 motor vehicles", "helmet law", "helmet rule",
            "helmet mandatory", "helmet fine", "two wheeler helmet", "pillion helmet",
            "bike helmet", "scooter helmet", "sikh helmet exemption",
        ],
    },
    {
        "key": "mv_132",
        "citation": "Motor Vehicles Act 1988, Section 132 — Duty of driver to stop in certain cases",
        "short_label": "MV 132",
        "act": "MV",
        "official_text": (
            "(1) The driver of a motor vehicle shall cause the vehicle to stop and cause it to "
            "remain stationary so long as may reasonably be necessary,—\n"
            "(a) when required to do so by any police officer in uniform, or by a person "
            "authorised to remove obstructions to traffic; or\n"
            "(b) when required to do so by any other person indicating that the vehicle is "
            "required to be stopped for the purpose of enabling any person to board or alight "
            "from another vehicle;\n"
            "(c) on the occurrence of an accident in which the vehicle is involved, in the manner "
            "prescribed in section 134.\n"
            "(2) The driver of a motor vehicle shall, on demand by a police officer in uniform, "
            "produce his driving licence for examination."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1798",
        "verified_at": "2026-02-01",
        "scope_note": (
            "You MUST stop when signalled by a UNIFORMED police officer, and you must show your "
            "driving licence on demand. Refusing to stop is itself an offence."
        ),
        "keywords": [
            "mv 132", "section 132 motor vehicles", "police stopped vehicle", "traffic stop",
            "traffic police stop", "duty to stop", "show license traffic",
            "produce driving licence", "traffic check", "traffic police powers",
            "vehicle check", "police checking vehicle",
        ],
    },
    {
        "key": "mv_134",
        "citation": "Motor Vehicles Act 1988, Section 134 — Duty of driver in case of accident and injury to a person",
        "short_label": "MV 134",
        "act": "MV",
        "official_text": (
            "When any person is injured or any property of a third party is damaged, as a result "
            "of an accident in which a motor vehicle is involved, the driver of the vehicle or "
            "other person in charge of the vehicle shall—\n"
            "(a) unless it is not practicable to do so on account of mob fury or any other "
            "reason beyond his control, take all reasonable steps to secure medical attention for "
            "the injured person, by conveying him to the nearest medical practitioner or hospital, "
            "and it shall be the duty of every registered medical practitioner or the doctor on "
            "duty in the hospital immediately to attend to the injured person and render medical "
            "aid or treatment without waiting for any procedural formalities, unless the injured "
            "person or his guardian, in case he is a minor, desires otherwise;\n"
            "(b) give on demand by a police officer any information required by him, or, if no "
            "police officer is present, report the circumstances of the occurrence, including the "
            "circumstances, if any, for not taking reasonable steps to secure medical attention "
            "as required under clause (a), at the nearest police station as soon as possible, and "
            "in any case within twenty-four hours of the occurrence."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1798",
        "verified_at": "2026-02-01",
        "scope_note": (
            "If you are in a road accident, the law REQUIRES you to help the injured person to a "
            "hospital and report the accident to police within 24 hours. Hospitals must treat the "
            "injured immediately — no paperwork first. Good Samaritans are protected from "
            "harassment."
        ),
        "keywords": [
            "mv 134", "section 134 motor vehicles", "road accident", "accident duty",
            "hit and run", "duty after accident", "accident report police", "accident 24 hours",
            "good samaritan", "help injured accident", "hospital accident treatment",
            "car accident what to do", "bike accident what to do", "accident procedure",
        ],
    },
    {
        "key": "mv_185",
        "citation": "Motor Vehicles Act 1988, Section 185 — Driving by a drunken person or by a person under the influence of drugs",
        "short_label": "MV 185",
        "act": "MV",
        "official_text": (
            "Whoever, while driving, or attempting to drive, a motor vehicle,—\n"
            "(a) has, in his blood, alcohol exceeding 30 mg. per 100 ml. of blood detected in a "
            "test by a breath analyser, or in any another test including a laboratory test, or\n"
            "(b) is under the influence of a drug to such an extent as to be incapable of "
            "exercising proper control over the vehicle,\n"
            "shall be punishable for the first offence with imprisonment for a term which may "
            "extend to six months, or with fine which may extend to ten thousand rupees, or with "
            "both; and for a second or subsequent offence, if committed within three years of the "
            "commission of the previous similar offence, with imprisonment for a term which may "
            "extend to two years, or with fine which may extend to fifteen thousand rupees, or "
            "with both."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1798",
        "verified_at": "2026-02-01",
        "scope_note": (
            "Legal blood-alcohol limit is 30 mg per 100 ml. Cross that OR drive under the "
            "influence of drugs, and the first offence is up to 6 months jail or ₹10,000 fine (or "
            "both). A repeat within 3 years can lead to 2 years jail or ₹15,000."
        ),
        "keywords": [
            "mv 185", "section 185 motor vehicles", "drunk driving", "drink and drive",
            "dui india", "alcohol driving", "breath analyser", "breathalyzer",
            "blood alcohol limit", "drugs driving", "drunk driving fine",
            "drunk driving punishment", "drunk driving jail",
        ],
    },
    {
        "key": "mv_194b",
        "citation": "Motor Vehicles Act 1988, Section 194B — Use of safety belts and the safety measures for children below fourteen years of age",
        "short_label": "MV 194B",
        "act": "MV",
        "official_text": (
            "(1) Whoever drives a motor vehicle without wearing a safety belt or carries "
            "passengers not wearing seat belts shall be punishable with a fine of one thousand "
            "rupees.\n"
            "(2) Whoever drives a motor vehicle without securing a child, who has not attained "
            "the age of fourteen years, either by a safety belt or a child restraint system, in "
            "accordance with such standards as may be prescribed, shall be punishable with a fine "
            "of one thousand rupees."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1798",
        "verified_at": "2026-02-01",
        "scope_note": (
            "Everyone in a car — driver AND passengers — must wear a seat belt. Children under "
            "14 must be secured with a seat belt or a proper child restraint. Fine is ₹1,000 per "
            "offence."
        ),
        "keywords": [
            "mv 194b", "section 194b motor vehicles", "seat belt", "seatbelt",
            "seat belt fine", "seat belt law", "child seat", "child restraint",
            "back seat belt", "passenger seat belt", "seat belt mandatory",
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
    (_re.compile(r"\b(?:[Ss]ec(?:tion|\.)?\s+\d+[A-Z]?(?:\(\d+\))?\s+(?:of\s+)?(?:BNS|BNSS|BSA|IPC|CrPC|RTI|CPA|MV|MVA))(?![A-Za-z0-9])"), "the law"),
    (_re.compile(r"\b(?:BNS|BNSS|BSA|IPC|CrPC|RTI|CPA|MV|MVA)\s+[Ss]ec(?:tion|\.)?\s+\d+[A-Z]?(?:\(\d+\))?(?![A-Za-z0-9])"), "the law"),
    # Bare "BNSS 43(5)" or "PWDVA 12" or "RTI 6" or "CPA 2(7)" or "MV 194B" style
    (_re.compile(r"\b(?:BNS|BNSS|BSA|IPC|CrPC|PWDVA|DV Act|RTI|CPA|MV|MVA)\s+\d+[A-Z]?(?:\(\d+\))?(?![A-Za-z0-9])"), "the law"),
    # Just "Section 35" alone
    (_re.compile(r"\b[Ss]ec(?:tion|\.)?\s+\d+[A-Z]?(?:\(\d+\))?(?![A-Za-z0-9])"), "the law"),
    # Long forms of the statutes
    (_re.compile(r"\bBharatiya\s+(?:Nyaya|Nagarik|Sakshya)\s+(?:Sanhita|Suraksha|Adhiniyam)(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\bIndian\s+Penal\s+Code(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\bCode\s+of\s+Criminal\s+Procedure(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\b(?:Protection\s+of\s+Women\s+from\s+Domestic\s+Violence\s+Act|PWDVA)(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\b(?:Right\s+to\s+Information\s+Act|RTI\s+Act)(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\bConsumer\s+Protection\s+Act(?:,?\s*\d{4})?\b"), "the law"),
    (_re.compile(r"\bMotor\s+Vehicles\s+Act(?:,?\s*\d{4})?\b"), "the law"),
]


def sanitize_model_output(text: str) -> str:
    """
    Defense-in-depth. Even with prompt instructions, models sometimes leak
    section/article identifiers. Strip them here BEFORE showing to the user.
    Citations are rendered separately from the verified corpus.

    Also strips markdown syntax (**bold**, __underline__, `code`, #headers) since
    the UI renders plain text — otherwise users see literal `**Answer:**` in the
    bubble instead of a formatted heading. Per P3 style spec: no markdown.
    """
    if not text:
        return text
    out = text
    for pat, repl in _CITATION_LEAK_PATTERNS:
        out = pat.sub(repl, out)
    # Strip markdown formatting the model occasionally emits despite the prompt.
    out = _re.sub(r"\*\*(.+?)\*\*", r"\1", out)        # **bold** → bold
    out = _re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)", r"\1", out)  # *italic* → italic
    out = _re.sub(r"__([^_\n]+?)__", r"\1", out)       # __underline__ → underline
    out = _re.sub(r"`([^`\n]+?)`", r"\1", out)         # `code` → code
    out = _re.sub(r"^#{1,6}\s+", "", out, flags=_re.MULTILINE)  # # heading → heading
    # collapse double spaces + trailing whitespace on lines
    out = _re.sub(r"[ \t]{2,}", " ", out)
    out = _re.sub(r"[ \t]+\n", "\n", out)
    return out
