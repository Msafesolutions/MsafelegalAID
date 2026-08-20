"""
DHARA CORPUS — cyber fraud: Information Technology Act 2000, the cheating
sections of the Bharatiya Nyaya Sanhita 2023, and the two official REPORTING
pathways a victim must use in the first 72 hours.

Same schema as corpus.py, plus the optional `text_kind` field used by
corpus_state.py:

  "verbatim"         — official_text is the exact statutory text
  "official_summary" — official_text faithfully states the operative rule from an
                       official instrument (an RBI master direction / MHA portal
                       procedure) whose full gazette wording is not reproduced.

Why the reporting entries exist: for UPI / OTP fraud the LAW is not the urgent
part — the CLOCK is. Money is recoverable only if the bank is told fast (RBI
zero-liability window) and the complaint is filed on the national portal /
helpline 1930 so the receiving account can be frozen.
"""

CYBER_CORPUS = [
    {
        "key": "it_66c",
        "citation": "Information Technology Act 2000, Section 66C — Punishment for identity theft",
        "short_label": "IT 66C",
        "act": "IT",
        "text_kind": "verbatim",
        "official_text": (
            "Whoever, fraudulently or dishonestly make use of the electronic signature, password "
            "or any other unique identification feature of any other person, shall be punished "
            "with imprisonment of either description for a term which may extend to three years "
            "and shall also be liable to fine which may extend to rupees one lakh."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1999",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Using someone else's password, OTP, e-signature, Aadhaar or other unique ID to "
            "cheat them is identity theft — up to 3 years jail and ₹1 lakh fine. This is the "
            "section used when a fraudster logs in as you or uses your stolen OTP."
        ),
        "keywords": [
            "it 66c", "section 66c", "identity theft", "otp misuse", "otp fraud",
            "password stolen", "someone used my otp", "aadhaar misuse", "account hacked",
            "my account hacked", "electronic signature misuse", "impersonation online",
            "someone using my id", "sim swap fraud",
        ],
    },
    {
        "key": "it_66d",
        "citation": "Information Technology Act 2000, Section 66D — Punishment for cheating by personation by using computer resource",
        "short_label": "IT 66D",
        "act": "IT",
        "text_kind": "verbatim",
        "official_text": (
            "Whoever, by means of any communication device or computer resource cheats by "
            "personation, shall be punished with imprisonment of either description for a term "
            "which may extend to three years and shall also be liable to fine which may extend "
            "to one lakh rupees."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1999",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Anyone who pretends to be a bank officer, police officer, courier agent, electricity "
            "board or relative on a phone, WhatsApp or website to cheat you commits this offence "
            "— up to 3 years jail and ₹1 lakh fine. This covers 'digital arrest' calls, fake "
            "customer-care numbers and KYC-update scams."
        ),
        "keywords": [
            "it 66d", "section 66d", "cheating by personation", "fake bank call",
            "fake customer care", "digital arrest", "digital arrest scam", "kyc update fraud",
            "phishing", "phishing link", "fake website fraud", "whatsapp scam",
            "telegram investment scam", "trading app fraud", "job offer scam",
            "electricity bill scam", "courier parcel scam", "impersonated police call",
            "online scam", "online fraud", "upi fraud", "upi scam", "money debited fraud",
        ],
    },
    {
        "key": "it_43",
        "citation": "Information Technology Act 2000, Section 43 — Penalty and compensation for damage to computer, computer system, etc.",
        "short_label": "IT 43",
        "act": "IT",
        "text_kind": "verbatim",
        "official_text": (
            "If any person, without permission of the owner or any other person who is in charge "
            "of a computer, computer system or computer network,—\n"
            "(a) accesses or secures access to such computer, computer system or computer "
            "network or computer resource;\n"
            "(b) downloads, copies or extracts any data, computer data base or information from "
            "such computer, computer system or computer network including information or data "
            "held or stored in any removable storage medium;\n"
            "(c) introduces or causes to be introduced any computer contaminant or computer "
            "virus into any computer, computer system or computer network;\n"
            "(i) destroys, deletes or alters any information residing in a computer resource or "
            "diminishes its value or utility or affects it injuriously by any means;\n"
            "(j) steals, conceals, destroys or alters or causes any person to steal, conceal, "
            "destroy or alter any computer source code used for a computer resource with an "
            "intention to cause damage,\n"
            "he shall be liable to pay damages by way of compensation to the person so affected."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1999",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Besides the police case, you can claim MONEY COMPENSATION from whoever accessed your "
            "account, phone or data without permission. Claims are filed before the state "
            "Adjudicating Officer (the IT Secretary) — a civil route that runs parallel to the "
            "criminal complaint."
        ),
        "keywords": [
            "it 43", "section 43 information technology", "compensation cyber fraud",
            "claim money back hacking", "unauthorised access account", "data stolen compensation",
            "adjudicating officer it act", "civil claim cyber", "virus damage claim",
        ],
    },
    {
        "key": "bns_318",
        "citation": "Bharatiya Nyaya Sanhita 2023, Section 318 — Cheating",
        "short_label": "BNS 318",
        "act": "BNS",
        "text_kind": "verbatim",
        "official_text": (
            "(1) Whoever, by deceiving any person, fraudulently or dishonestly induces the person "
            "so deceived to deliver any property to any person, or to consent that any person "
            "shall retain any property, or intentionally induces the person so deceived to do or "
            "omit to do anything which he would not do or omit if he were not so deceived, and "
            "which act or omission causes or is likely to cause damage or harm to that person in "
            "body, mind, reputation or property, is said to 'cheat'.\n"
            "(2) Whoever cheats shall be punished with imprisonment of either description for a "
            "term which may extend to three years, or with fine, or with both.\n"
            "(3) Whoever cheats with the knowledge that he is likely thereby to cause wrongful "
            "loss to a person whose interest in the transaction to which the cheating relates, he "
            "was bound, either by law, or by a legal contract, to protect, shall be punished with "
            "imprisonment of either description for a term which may extend to five years, or "
            "with fine, or with both.\n"
            "(4) Whoever cheats and thereby dishonestly induces the person deceived to deliver "
            "any property to any person, or to make, alter or destroy the whole or any part of a "
            "valuable security, or anything which is signed or sealed, and which is capable of "
            "being converted into a valuable security, shall be punished with imprisonment of "
            "either description for a term which may extend to seven years, and shall also be "
            "liable to fine."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20062",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Any fraud where you were tricked into paying or transferring money is 'cheating'. "
            "When the trick made you hand over money or property, the punishment goes up to 7 "
            "years jail and fine. This is the main criminal section in an online-fraud FIR, used "
            "along with the computer-fraud sections."
        ),
        "keywords": [
            "bns 318", "cheating", "cheating punishment", "fraud case", "fraud fir",
            "money fraud", "cheated of money", "duped money", "fraud investment",
            "chit fund fraud", "ponzi scheme", "loan app fraud", "fake seller online",
            "product never delivered fraud", "advance paid fraud", "420 case",
        ],
    },
    {
        "key": "bns_319",
        "citation": "Bharatiya Nyaya Sanhita 2023, Section 319 — Cheating by personation",
        "short_label": "BNS 319",
        "act": "BNS",
        "text_kind": "verbatim",
        "official_text": (
            "(1) A person is said to 'cheat by personation' if he cheats by pretending to be some "
            "other person, or by knowingly substituting one person for or another, or "
            "representing that he or any other person is a person other than he or such other "
            "person really is.\n"
            "Explanation.—The offence is committed whether the individual personated is a real or "
            "imaginary person.\n"
            "(2) Whoever cheats by personation shall be punished with imprisonment of either "
            "description for a term which may extend to five years, or with fine, or with both."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20062",
        "verified_at": "2026-06-01",
        "scope_note": (
            "If the fraudster pretended to be someone else — a bank officer, an army man buying "
            "your OLX item, a relative in trouble, or even an imaginary person — that is cheating "
            "by personation, punishable with up to 5 years jail. Mention this in your complaint "
            "along with the computer-fraud section."
        ),
        "keywords": [
            "bns 319", "cheating by personation", "fake identity fraud", "olx fraud",
            "army man scam", "pretending bank officer", "fake profile fraud",
            "matrimonial fraud", "impersonation fraud", "fake relative call",
        ],
    },
    {
        "key": "cyber_report_1930",
        "citation": "National Cyber Crime Reporting Portal (Ministry of Home Affairs) — Citizen Financial Cyber Fraud Reporting and Management System, helpline 1930",
        "short_label": "Cyber report 1930",
        "act": "Cyber reporting",
        "text_kind": "official_summary",
        "official_text": (
            "Financial cyber fraud must be reported on the National Cyber Crime Reporting Portal "
            "at cybercrime.gov.in or on the national cyber-crime helpline number 1930, which is "
            "operated under the Citizen Financial Cyber Fraud Reporting and Management System of "
            "the Indian Cyber Crime Coordination Centre, Ministry of Home Affairs.\n"
            "On reporting, the transaction details are placed on a common platform shared by "
            "banks, wallets, payment aggregators and law-enforcement agencies so that the "
            "beneficiary account through which the money moved can be put on hold. The chance of "
            "the money being stopped falls sharply with delay, so the report should be made "
            "within the GOLDEN HOUR — as soon as the fraud is noticed.\n"
            "The portal also accepts complaints about cyber-stalking, obscene content, hacking "
            "and crimes against women and children (which may be filed anonymously). A complaint "
            "filed on the portal is routed to the police station having jurisdiction; the "
            "complainant receives an acknowledgement number and can track the status online."
        ),
        "source_url": "https://cybercrime.gov.in/",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Do this FIRST, within minutes: call 1930 or file on cybercrime.gov.in with the "
            "transaction reference, amount, date and the number that contacted you. This is what "
            "gets the fraudster's account frozen — a police station visit alone does not freeze "
            "the money."
        ),
        "keywords": [
            "cyber crime report", "how to report cyber fraud", "1930", "1930 helpline",
            "cybercrime gov in", "cyber crime portal", "report online fraud",
            "report upi fraud", "where to complain cyber fraud", "cyber police complaint",
            "golden hour cyber fraud", "freeze fraud account", "money gone upi what to do",
            "fraud transaction complaint", "cyber cell complaint", "report otp fraud",
            "report phishing", "report digital arrest", "track cyber complaint",
        ],
    },
    {
        "key": "rbi_zero_liability",
        "citation": "Reserve Bank of India — Customer Protection: Limiting Liability of Customers in Unauthorised Electronic Banking Transactions (Master Direction / Circular DBR.No.Leg.BC.78/09.07.005/2017-18)",
        "short_label": "RBI zero liability",
        "act": "RBI customer protection",
        "text_kind": "official_summary",
        "official_text": (
            "Where an unauthorised electronic banking transaction happens, the customer's "
            "liability depends on WHEN the customer notifies the bank:\n"
            "(a) Contributory fraud, negligence or deficiency on the part of the bank — the "
            "customer bears ZERO liability, irrespective of whether the transaction is reported.\n"
            "(b) Third-party breach where the deficiency lies neither with the bank nor with the "
            "customer, and the customer notifies the bank within THREE working days of receiving "
            "the communication about the transaction — the customer bears ZERO liability.\n"
            "(c) The same third-party breach notified within FOUR to SEVEN working days — the "
            "customer's liability is limited to the transaction value or a per-account cap "
            "prescribed in the direction, whichever is lower.\n"
            "(d) Notification beyond seven working days — the customer's liability is determined "
            "as per the bank's board-approved policy.\n"
            "Where the customer is at fault, for example by sharing payment credentials, the "
            "customer bears the entire loss until the transaction is reported to the bank; loss "
            "occurring AFTER the report is borne by the bank.\n"
            "On being notified, the bank must credit (shadow reversal) the amount involved to the "
            "customer's account within TEN working days from the date of notification, and must "
            "resolve the complaint within ninety days. Banks must provide customers a 24x7 "
            "reporting channel, including a direct link on the home page of the internet banking "
            "site and in the mobile app, and must send a positive acknowledgement of the report."
        ),
        "source_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11040",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Tell your BANK in writing within 3 WORKING DAYS of the fraud and your liability is "
            "ZERO — the bank must put the money back within 10 working days. Report between 4 and "
            "7 days and you may bear a capped loss. After 7 days it is the bank's policy that "
            "decides, so never wait."
        ),
        "keywords": [
            "rbi zero liability", "unauthorised transaction bank", "money debited without otp",
            "bank fraud refund", "get money back fraud", "3 working days bank report",
            "three working days fraud", "10 working days credit", "bank must refund fraud",
            "who pays cyber fraud loss", "shared otp liability", "bank refused refund fraud",
            "unauthorized debit card transaction", "net banking fraud refund",
            "wallet fraud refund", "upi fraud refund",
        ],
    },
]
