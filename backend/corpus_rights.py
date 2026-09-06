"""
DHARA CORPUS — citizen-rights clusters added per audit: protest/assembly,
FIR refusal, bail, under-trial detention, consumer protection, RTI, child
labour/marriage, and senior-citizen maintenance.

Same schema as corpus.py / corpus_labour.py. Every `official_text` below is
copied/excerpted directly from the verified section text in the MongoDB
`legal_sections` collection (bns-know-your-rights-gandhikar_db) — checked
section-by-section for `is_dead_law` before being added here. No statutory
content in this file was written from training-data knowledge.

PROTEST / ASSEMBLY NOTE: Constitution Article 19(1)(a)/(b) (freedom of
speech, freedom of assembly) is NOT in the MongoDB corpus — only 3
Constitution sections exist there at all (§186, §187, §195; none are
fundamental-rights articles). The two entries below are therefore anchored
to BNS §189 (definition of unlawful assembly) and BNSS §148 (dispersal
procedure) instead — i.e. "when police CAN and CANNOT legally act against a
gathering" — and NEVER claim to state the Article 19 right itself. Ingesting
Constitution Part III into the corpus is a separate, future data task.
"""

RIGHTS_CORPUS = [
    # -------------------- Right to protest / unlawful assembly --------------------
    {
        "key": "bns_189",
        "citation": "Bharatiya Nyaya Sanhita 2023, Section 189 — Unlawful assembly",
        "short_label": "BNS 189",
        "act": "Bharatiya Nyaya Sanhita",
        "text_kind": "verbatim",
        "require_any": [
            "protest", "rally", "march", "assembly", "gather", "gathering",
            "demonstration", "dharna", "procession", "andolan", "morcha",
        ],
        "official_text": (
            "(1) An assembly of five or more persons is designated an unlawful assembly, if the "
            "common object of the persons composing that assembly is— (a) to overawe by criminal "
            "force, or show of criminal force, the Central Government or any State Government or "
            "Parliament or the Legislature of any State, or any public servant in the exercise of "
            "the lawful power of such public servant; or (b) to resist the execution of any law, or "
            "of any legal process; or (c) to commit any mischief or criminal trespass, or other "
            "offence; or (d) by means of criminal force, or show of criminal force, to any person, "
            "to take or obtain possession of any property... or to enforce any right or supposed "
            "right; or (e) by means of criminal force, or show of criminal force, to compel any "
            "person to do what he is not legally bound to do, or to omit to do what he is legally "
            "entitled to do."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/2191",
        "verified_at": "2026-06-04",
        "scope_note": (
            "Open your answer with this honest caveat, in your own words: the right to peacefully "
            "protest is guaranteed by the Constitution, but the specific constitutional articles "
            "are not yet in our verified database, so this answer explains what the CRIMINAL LAW "
            "says about when police can and cannot legally act against a gathering — not the "
            "constitutional right itself. Substance: a gathering of 5+ people is ONLY an 'unlawful "
            "assembly' if its object is one of the five listed things above (using or showing "
            "criminal force against the government/a public servant, resisting a law, mischief or "
            "trespass, forcibly grabbing property or a right, or forcing someone to act against "
            "their legal rights). A peaceful protest with none of these objects is NOT an unlawful "
            "assembly under this section merely for being a protest."
        ),
        "keywords": [
            "bns 189", "right to protest", "can i protest", "protest rights india",
            "can i hold a rally", "permission for protest", "can police stop a march",
            "can police stop us from marching", "is protesting illegal", "arrested for protesting",
            "police stopped our rally", "unlawful assembly meaning", "when is a protest illegal",
        ],
    },
    {
        "key": "bnss_148",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 148 — Dispersal of assembly by use of civil force",
        "short_label": "BNSS 148",
        "act": "Bharatiya Nagarik Suraksha Sanhita",
        "text_kind": "verbatim",
        "require_any": [
            "protest", "rally", "march", "assembly", "gather", "gathering",
            "demonstration", "dharna", "procession", "andolan", "morcha", "disperse",
        ],
        "official_text": (
            "(1) Any Executive Magistrate or officer in charge of a police station or, in the "
            "absence of such officer in charge, any police officer, not below the rank of a "
            "sub-inspector, may command any unlawful assembly, or any assembly of five or more "
            "persons likely to cause a disturbance of the public peace, to disperse; and it shall "
            "thereupon be the duty of the members of such assembly to disperse accordingly. "
            "(2) If, upon being so commanded, any such assembly does not disperse... any Executive "
            "Magistrate or police officer... may proceed to disperse such assembly by force... and, "
            "if necessary, arresting and confining the persons who form part of it."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/6a5b6a6a",
        "verified_at": "2026-06-04",
        "scope_note": (
            "Police cannot simply arrest a gathering on the spot. The law requires an Executive "
            "Magistrate or an officer at least sub-inspector rank to FIRST COMMAND the assembly to "
            "disperse — only if people refuse to disperse after that command can force or arrest "
            "follow. If no such command was given, or the protest is not an unlawful assembly under "
            "BNS s.189, action against it is not lawfully justified under this section."
        ),
        "keywords": [
            "bnss 148", "dispersal of protest", "police order to disperse", "can police force disperse",
            "police baton charge legal", "lathi charge protest legal", "order to disperse crowd",
            "who can order dispersal", "magistrate order disperse",
        ],
    },
    # -------------------- Police refusing to register FIR --------------------
    # NOTE: BNSS s.173 already has a hand-curated entry in corpus.py's main
    # CORPUS list (key "bnss_173", added earlier) with keywords covering
    # "fir refused", "police refused fir", "zero fir" etc. Verified below
    # (test phrasing 2) that it already retrieves correctly — no duplicate
    # entry added here to avoid a duplicate citation for the same section.
    # -------------------- Bail --------------------
    {
        "key": "bnss_478",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 478 — In what cases bail to be taken",
        "short_label": "BNSS 478",
        "act": "Bharatiya Nagarik Suraksha Sanhita",
        "text_kind": "verbatim",
        "require_any": [
            "bail", "arrest", "arrested", "custody", "jail", "detain", "detained", "police station",
        ],
        "official_text": (
            "(1) When any person other than a person accused of a nonbailable offence is arrested "
            "or detained without warrant by an officer in charge of a police station, or appears "
            "or is brought before a Court, and is prepared at any time while in the custody of such "
            "officer or at any stage of the proceeding before such Court to give bail, such person "
            "shall be released on bail: Provided that such officer or Court... shall, if such "
            "person is indigent and is unable to furnish surety, instead of taking bail bond from "
            "such person, discharge him on his executing a bond for his appearance."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/6c56b21d-5320-43cb-b572-5b6d359df1a1",
        "verified_at": "2026-06-04",
        "scope_note": (
            "If the offence is BAILABLE, bail is a RIGHT, not a favour — the police or court must "
            "release the person on bail if they are willing to give it. If the person is too poor "
            "to arrange a surety, the law says they must still be released on just their own bond "
            "(no surety needed) — being unable to arrange bail within a week is itself proof of "
            "poverty for this purpose."
        ),
        "keywords": [
            "bnss 478", "how do i get bail", "what is bail", "bail meaning",
            "bailable offence bail", "surety for bail", "cannot afford bail",
            "released on bail bond", "bail without surety",
        ],
    },
    {
        "key": "bnss_480",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 480 — When bail may be taken in case of non-bailable offence",
        "short_label": "BNSS 480",
        "act": "Bharatiya Nagarik Suraksha Sanhita",
        "text_kind": "verbatim",
        "require_any": [
            "bail", "arrest", "arrested", "custody", "jail", "detain", "detained", "son", "daughter",
        ],
        "official_text": (
            "(1) When any person accused of, or suspected of, the commission of any non-bailable "
            "offence is arrested or detained without warrant... or appears or is brought before a "
            "Court... he may be released on bail, but— (i) such person shall not be so released if "
            "there appear reasonable grounds for believing that he has been guilty of an offence "
            "punishable with death or imprisonment for life... Provided that the Court may direct "
            "that a person referred to in clause (i) or clause (ii) be released on bail if such "
            "person is a child or is a woman or is sick or infirm. (6) If, in any case triable by a "
            "Magistrate, the trial of a person accused of any non-bailable offence is not concluded "
            "within a period of sixty days from the first date fixed for taking evidence in the "
            "case, such person shall, if he is in custody during the whole of the said period, be "
            "released on bail to the satisfaction of the Magistrate, unless for reasons to be "
            "recorded in writing, the Magistrate otherwise directs."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/d1cd36f9-1f54-4292-98e2-397e05e48799",
        "verified_at": "2026-06-04",
        "scope_note": (
            "For a NON-bailable offence, bail is at the court's discretion, not automatic — but it "
            "is still available. Bail is usually refused only if there are reasonable grounds the "
            "person is guilty of an offence carrying death or life imprisonment; even then, a "
            "child, woman, or a sick/infirm person can still be granted bail. A lawyer can file a "
            "bail application before the Magistrate or Sessions Court handling the case; there is "
            "no need to wait for the trial to finish."
        ),
        "keywords": [
            "bnss 480", "they arrested my son can he get bail", "non bailable offence bail",
            "bail application", "how to apply for bail", "bail for serious offence",
            "son arrested bail", "daughter arrested bail", "get someone out on bail",
        ],
    },
    {
        "key": "bnss_479",
        "citation": "Bharatiya Nagarik Suraksha Sanhita 2023, Section 479 — Maximum period for which under-trial prisoner can be detained",
        "short_label": "BNSS 479",
        "act": "Bharatiya Nagarik Suraksha Sanhita",
        "text_kind": "verbatim",
        "require_any": [
            "under trial", "undertrial", "jail", "custody", "detained", "detention", "no bail",
            "trial", "months", "years", "long time",
        ],
        "official_text": (
            "(1) Where a person has, during the period of investigation, inquiry or trial... "
            "undergone detention for a period extending up to one-half of the maximum period of "
            "imprisonment specified for that offence under that law, he shall be released by the "
            "Court on bail: Provided that where such person is a first-time offender... he shall "
            "be released on bond by the Court, if he has undergone detention for the period "
            "extending up to one-third of the maximum period of imprisonment specified for such "
            "offence... Provided also that no such person shall in any case be detained during the "
            "period of investigation, inquiry or trial for more than the maximum period of "
            "imprisonment provided for the said offence under that law."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/c0874ba2-3985-4c3f-9c1d-969c9e5b7db3",
        "verified_at": "2026-06-04",
        "scope_note": (
            "A person who has been in jail awaiting trial for a long time, with no final verdict "
            "yet, has a right to be released once their custody time reaches HALF of the maximum "
            "possible sentence for that offence (or ONE-THIRD if it is their first-ever offence). "
            "This applies to most offences (not ones where death or life imprisonment is a "
            "possible punishment). The jail superintendent is legally required to apply to the "
            "court for this release once that time is reached — the family does not have to wait "
            "for it; they can also remind the jail authorities or the lawyer to file this "
            "application."
        ),
        "keywords": [
            "bnss 479", "brother in jail for two years without trial",
            "how long can police keep someone without bail", "under-trial prisoner rights",
            "bail not given for months", "undertrial detention limit", "stuck in jail no trial",
            "how long can someone be in jail without trial", "trial delayed still in jail",
        ],
    },
    # -------------------- Consumer protection --------------------
    # NOTE: CPA s.35 (complaint filing) already has a hand-curated entry in
    # corpus.py's main CORPUS list (key "cpa_35") with keywords covering
    # "faulty product", "defective goods", "shopkeeper cheated" etc. — not
    # duplicated here. Only s.2 (defect/deficiency definitions) is new.
    {
        "key": "cpa_2",
        "citation": "Consumer Protection Act 2019, Section 2 — Definitions (consumer, defect, deficiency, complaint)",
        "short_label": "CPA 2",
        "act": "Consumer Protection Act",
        "text_kind": "official_summary",
        "require_any": [
            "consumer", "product", "goods", "shop", "shopkeeper", "refund", "defective",
            "company", "seller", "purchase", "bought", "phone", "item", "warranty",
        ],
        "official_text": (
            "Section 2(10) 'defect' means any fault, imperfection or shortcoming in the quality, "
            "quantity, potency, purity or standard which is required to be maintained by or under "
            "any law, contract, or as claimed by the trader — in relation to any goods or product. "
            "Section 2(11) 'deficiency' means any fault, imperfection, shortcoming or inadequacy in "
            "the quality, nature or manner of a service, including negligence and deliberately "
            "withholding relevant information. Section 2(7) 'consumer' means any person who buys "
            "goods or hires a service for consideration — but does NOT include a person who buys "
            "goods for resale or commercial purpose. Section 2(6) 'complaint' includes an allegation "
            "that goods bought suffer from one or more defects, or that a trader charged more than "
            "the price displayed or agreed."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/a601b993-e93b-4355-b727-924747c0fe46",
        "verified_at": "2026-06-04",
        "scope_note": (
            "A product that doesn't work as it should, or a shortcoming in quality/quantity/purity "
            "that the seller promised, legally counts as a 'defect' — and a defective product or a "
            "deficient service is exactly what the Consumer Protection Act exists to fix. You "
            "qualify as a 'consumer' as long as you bought it for your own use, not to resell."
        ),
        "keywords": [
            "cpa 2", "i bought a defective product", "defective phone", "product not working",
            "company cheated me how to complain", "bought a faulty item", "product quality complaint",
            "what counts as a defect", "am i a consumer",
        ],
    },
    # -------------------- Right to Information --------------------
    # NOTE: RTI s.6 (application procedure) and s.7 (time limit) already have
    # hand-curated entries in corpus.py's main CORPUS list (keys "rti_6" and
    # "rti_7") with good keyword coverage ("how to file rti", "rti 30 days",
    # "rti not answered" etc.) — not duplicated here. Only s.3 (the
    # foundational right itself) was missing and is added below.
    {
        "key": "rti_3",
        "citation": "Right to Information Act 2005, Section 3 — Right to information",
        "short_label": "RTI 3",
        "act": "Right to Information Act",
        "text_kind": "verbatim",
        "require_any": [
            "rti", "information", "government", "public authority", "application", "officer", "record",
        ],
        "official_text": "Subject to the provisions of this Act, all citizens shall have the right to information.",
        "source_url": "https://indiacode.gov.in/handle/123456789/4706576b-ebac-4bcc-8c6f-d51b1e106e35",
        "verified_at": "2026-06-04",
        "scope_note": (
            "Every Indian citizen has the legal right to ask any government office for information "
            "it holds. You do not need to explain why you want it."
        ),
        "keywords": [
            "rti 3", "right to information", "how do i file rti", "rti application",
            "government not giving information", "what is rti",
        ],
    },
    # -------------------- Child labour --------------------
    {
        "key": "cal_3",
        "citation": "Child and Adolescent Labour (Prohibition and Regulation) Act 1986, Section 3 — Prohibition of employment of children",
        "short_label": "CAL 3",
        "act": "Child and Adolescent Labour (Prohibition and Regulation) Act",
        "text_kind": "verbatim",
        "require_any": [
            "child", "children", "minor", "factory", "labour", "labor", "work", "working", "employ",
        ],
        "official_text": (
            "(1) No child shall be employed or permitted to work in any occupation or process. "
            "(2) Nothing in sub-section (1) shall apply where the child— (a) helps his family or "
            "family enterprise, which is other than any hazardous occupations or processes set "
            "forth in the Schedule, after his school hours or during vacations; (b) works as an "
            "artist in an audio-visual entertainment industry... except the circus... Provided that "
            "no such work under this clause shall effect the school education of the Child."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/3e0e974b-424f-4b05-828e-2ef1ff229cf4",
        "verified_at": "2026-06-04",
        "scope_note": (
            "Employing a child (under 14) in any job or process is illegal, with only two narrow "
            "exceptions: helping the family's own non-hazardous business outside school hours, or "
            "working as a performer in entertainment (never in a circus), and even that must never "
            "affect the child's schooling. A child working in a factory falls under neither "
            "exception and is illegal child labour — report it to the Labour Department or Childline."
        ),
        "keywords": [
            "cal 3", "my child is working in a factory", "child labour", "underage worker",
            "minor working illegally", "child employed factory", "child labour complaint",
        ],
    },
    # -------------------- Child marriage --------------------
    {
        "key": "pcma_3",
        "citation": "Prohibition of Child Marriage Act 2006, Section 3 — Child marriages voidable at the option of the child",
        "short_label": "PCMA 3",
        "act": "Prohibition of Child Marriage Act",
        "text_kind": "verbatim",
        "require_any": [
            "child marriage", "underage marriage", "minor marriage", "child bride", "married",
            "marry", "forced marriage",
        ],
        "official_text": (
            "(1) Every child marriage, whether solemnised before or after the commencement of this "
            "Act, shall be voidable at the option of the contracting party who was a child at the "
            "time of the marriage: Provided that a petition for annulling a child marriage by a "
            "decree of nullity may be filed in the district court only by a contracting party to "
            "the marriage who was a child at the time of the marriage. (3) The petition under this "
            "section may be filed at any time but before the child filing the petition completes "
            "two years of attaining majority."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/1c2c80a7-aa27-48ca-8b35-e9477914bb63",
        "verified_at": "2026-06-04",
        "scope_note": (
            "A child marriage is not automatically cancelled — the person who was a child at the "
            "time can apply to a district court to have it annulled, any time up until 2 years "
            "after they turn 18. But if a marriage is being FORCED or is about to happen, do not "
            "wait for annulment: contact the local Child Marriage Prohibition Officer, call "
            "Childline on 1098, or inform the police immediately — forcing or solemnising a child "
            "marriage is also a separate criminal offence."
        ),
        "keywords": [
            "pcma 3", "forced child marriage", "underage marriage how to stop", "child marriage",
            "stop a child marriage", "minor being married off", "child bride rights",
        ],
    },
    # -------------------- Senior citizen maintenance --------------------
    {
        "key": "swpsc_4",
        "citation": "Maintenance and Welfare of Parents and Senior Citizens Act 2007, Section 4 — Maintenance of parents and senior citizens",
        "short_label": "SWPSC 4",
        "act": "Maintenance and Welfare of Parents and Senior Citizens Act",
        "text_kind": "verbatim",
        "require_any": [
            "parent", "parents", "mother", "father", "senior citizen", "old age", "elderly", "son", "daughter",
        ],
        "official_text": (
            "(1) A senior citizen including parent who is unable to maintain himself from his own "
            "earning or out of the property owned by him, shall be entitled to make an application "
            "under section 5... against one or more of his children not being a minor. (2) The "
            "obligation of the children or relative... extends to the needs of such citizen so that "
            "senior citizen may lead a normal life. (3) The obligation of the children to maintain "
            "his or her parent extends to the needs of such parent either father or mother or both."
        ),
        "source_url": "https://indiacode.gov.in/handle/123456789/40bf285c-5467-4b99-b572-046c2a5322c9",
        "verified_at": "2026-06-04",
        "scope_note": (
            "If a parent or senior citizen cannot support themselves from their own income or "
            "property, they have a LEGAL RIGHT to be maintained by their adult children — this is "
            "enforceable, not just a moral expectation. They can apply to the Maintenance Tribunal "
            "set up under this Act (usually at the Sub-Divisional Magistrate's office) without "
            "needing a lawyer or a civil court case."
        ),
        "keywords": [
            "swpsc 4", "children not taking care of parents", "son not giving money to old parents",
            "can i force my son to support me", "maintenance for parents", "elderly parents rights",
            "old age maintenance claim", "senior citizen maintenance tribunal",
        ],
    },
]
