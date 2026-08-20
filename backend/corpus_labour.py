"""
DHARA CORPUS — wages, termination and gratuity under the four Labour Codes.

The four Labour Codes were brought into force on 21 November 2025, so the
operative law for a worker asking about unpaid salary, termination or gratuity
today is the Code on Wages 2019, the Industrial Relations Code 2020 and the
Code on Social Security 2020 — NOT the repealed Payment of Wages Act 1936,
Industrial Disputes Act 1947 or Payment of Gratuity Act 1972.

Same schema as corpus.py. `text_kind` marks entries whose official_text is a
faithful statement of the operative rule rather than a word-for-word quote.

Every entry carries a `require_any` guard so generic words ("notice", "pay",
"claim") cannot pull a labour section into an unrelated answer.
"""

_WORK_GUARD = [
    "salary", "wage", "wages", "pay", "paid", "payment", "employer", "employee",
    "job", "work", "worker", "staff", "company", "boss", "termination", "terminate",
    "retrench", "retrenchment", "dismiss", "fired", "sacked", "resign", "notice period",
    "gratuity", "overtime", "bonus", "pf", "provident", "labour", "labor", "hr",
]

LABOUR_CORPUS = [
    {
        "key": "wages_17",
        "citation": "Code on Wages 2019, Section 17 — Time limit for payment of wages",
        "short_label": "Wage Code 17",
        "act": "Code on Wages",
        "text_kind": "verbatim",
        "require_any": _WORK_GUARD,
        "official_text": (
            "(1) The employer shall pay or cause to be paid wages to the employees, engaged on—\n"
            "(i) daily basis, at the end of the shift;\n"
            "(ii) weekly basis, on the last working day of the week, that is to say, before the "
            "weekly holiday;\n"
            "(iii) fortnightly basis, before the end of the second day after the end of the "
            "fortnight;\n"
            "(iv) monthly basis, before the expiry of the seventh day of the succeeding month.\n"
            "(2) Where an employee has been—\n"
            "(i) removed or dismissed from service; or\n"
            "(ii) retrenched or has resigned from service, or became unemployed due to closure "
            "of the establishment,\n"
            "the wages payable to him shall be paid within two working days of his removal, "
            "dismissal, retrenchment or, as the case may be, his resignation."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/15793/1/aA2019-29.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "A monthly-paid worker must be paid by the 7th of the next month. If you were fired, "
            "retrenched, resigned or the business shut down, ALL wages due must be paid within "
            "TWO WORKING DAYS. Anything later is a violation you can complain about."
        ),
        "keywords": [
            "wage code 17", "salary not paid", "salary delayed", "employer not paying salary",
            "salary due date", "7th of month salary", "when should salary be paid",
            "final settlement salary", "full and final settlement", "wages after resignation",
            "salary after termination", "last salary not paid", "company not paying salary",
            "two working days wages", "unpaid wages", "wages not paid",
        ],
    },
    {
        "key": "wages_18",
        "citation": "Code on Wages 2019, Section 18 — Deductions which may be made from wages",
        "short_label": "Wage Code 18",
        "act": "Code on Wages",
        "text_kind": "verbatim",
        "require_any": _WORK_GUARD + ["deduction", "deducted", "cut", "fine"],
        "official_text": (
            "(1) Notwithstanding anything contained in any other law for the time being in force, "
            "there shall be no deductions from the wages of the employee, except those as are "
            "authorised under this Code.\n"
            "(2) Deductions from the wages of an employee shall be made in accordance with the "
            "provisions of this Code, and may be made only of the following kinds, namely:—"
            "(a) fines imposed on him; (b) deductions for his absence from duty; (c) deductions "
            "for damage to or loss of goods expressly entrusted to the employee for custody, or "
            "for loss of money for which he is required to account, where such damage or loss is "
            "directly attributable to his neglect or default; (d) deductions for house "
            "accommodation supplied by the employer or by the Government; (e) deductions for such "
            "amenities and services supplied by the employer as the Government may authorise; "
            "(f) deductions for recovery of advances or for adjustment of overpayment of wages; "
            "(g) deductions for recovery of loans made from any fund constituted for the welfare "
            "of labour; (h) deductions of income-tax or any other statutory levy; (i) deductions "
            "required to be made by order of a court or other competent authority; (j) deductions "
            "for subscription to, and repayment of advances from, any provident fund; "
            "(k) deductions for payment to co-operative societies or insurance premia, with the "
            "written authorisation of the employee.\n"
            "(3) Notwithstanding anything contained in this Code, the total amount of deductions "
            "in any wage period from the wages of an employee shall not exceed fifty per cent. of "
            "such wages."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/15793/1/aA2019-29.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Your employer can only cut your pay for the reasons the law lists — fines, absence, "
            "proven loss you caused, taxes, PF, court orders and a few authorised services. Total "
            "deductions can NEVER be more than half of your wages for that period."
        ),
        "keywords": [
            "wage code 18", "salary deduction", "salary deducted", "illegal deduction",
            "pay cut without consent", "employer deducting money", "fine deducted from salary",
            "half salary deducted", "deduction limit salary", "notice period recovery",
        ],
    },
    {
        "key": "wages_45",
        "citation": "Code on Wages 2019, Section 45 — Appointment of authority for claims and adjudication",
        "short_label": "Wage Code 45",
        "act": "Code on Wages",
        "text_kind": "official_summary",
        "require_any": _WORK_GUARD + ["claim", "complain", "complaint"],
        "official_text": (
            "The appropriate Government appoints an authority, not below the rank of a Gazetted "
            "Officer, to hear and determine claims arising under this Code, including claims for "
            "non-payment or short payment of wages, bonus, equal remuneration and any other "
            "amount due to an employee.\n"
            "An application may be made by the employee, by a registered trade union of which the "
            "employee is a member, or by an Inspector-cum-Facilitator, and must be filed within "
            "THREE YEARS from the date on which the claim arose; the authority may admit a later "
            "application if the applicant satisfies it that there was sufficient cause for the "
            "delay.\n"
            "Where the authority finds the claim proved, it may direct payment of the amount due "
            "and, in addition, may award compensation to the employee of up to TEN TIMES the "
            "amount found due. The authority has the powers of a civil court to summon persons "
            "and require the production of documents, and its order is recoverable as an arrear "
            "of land revenue."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/15793/1/aA2019-29.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "You do not need a court case for unpaid salary. File a claim with the authority "
            "appointed under the wage law (usually the Labour Commissioner's office) within THREE "
            "YEARS. It can order your money back plus compensation of up to ten times the amount "
            "your employer withheld."
        ),
        "keywords": [
            "wage code 45", "where to complain salary", "labour commissioner complaint",
            "unpaid salary complaint", "salary claim authority", "how to recover salary",
            "salary case", "three years salary claim", "compensation unpaid wages",
            "employer not paying what to do", "trade union claim wages",
        ],
    },
    {
        "key": "labour_samadhan",
        "citation": "Ministry of Labour & Employment — SAMADHAN portal for industrial dispute and wage grievance filing",
        "short_label": "SAMADHAN portal",
        "act": "Labour grievance pathway",
        "text_kind": "official_summary",
        "require_any": _WORK_GUARD + ["complain", "complaint", "grievance", "where"],
        "official_text": (
            "The Ministry of Labour & Employment operates SAMADHAN (samadhan.labour.gov.in), an "
            "online portal through which a worker, an employer or a trade union can file an "
            "industrial dispute or a grievance relating to non-payment of wages, illegal "
            "termination, retrenchment or other labour matters.\n"
            "A complaint filed on the portal is allotted a unique registration number and routed "
            "to the conciliation officer / Assistant Labour Commissioner having jurisdiction, who "
            "calls both sides for conciliation. The complainant can track the status of the case "
            "online.\n"
            "Establishments under State jurisdiction are handled by the State Labour Department; "
            "central-sphere establishments are handled by the Chief Labour Commissioner "
            "(Central). Filing on the portal does not take away the worker's right to file a "
            "claim before the wage authority or to raise an industrial dispute."
        ),
        "source_url": "https://samadhan.labour.gov.in/",
        "verified_at": "2026-06-01",
        "scope_note": (
            "File online at samadhan.labour.gov.in — you get a registration number and the "
            "Labour Commissioner's office calls both sides for conciliation. Keep your appointment "
            "letter, payslips, bank statement and any WhatsApp or email proof ready."
        ),
        "keywords": [
            "samadhan portal", "labour complaint online", "where to complain employer",
            "labour commissioner online", "industrial dispute filing", "conciliation officer",
            "file labour case online", "labour department complaint", "worker grievance portal",
        ],
    },
    {
        "key": "ir_70",
        "citation": "Industrial Relations Code 2020, Section 70 — Conditions precedent to retrenchment of workers",
        "short_label": "IR Code 70",
        "act": "Industrial Relations Code",
        "text_kind": "verbatim",
        "require_any": _WORK_GUARD,
        "official_text": (
            "No worker employed in any industrial establishment who has been in continuous "
            "service for not less than one year under an employer shall be retrenched by that "
            "employer until—\n"
            "(a) the worker has been given one month's notice in writing indicating the reasons "
            "for retrenchment and the period of notice has expired, or the worker has been paid "
            "in lieu of such notice, wages for the period of the notice;\n"
            "(b) the worker has been paid, at the time of retrenchment, compensation which shall "
            "be equivalent to fifteen days' average pay, or average pay of such number of days as "
            "may be notified by the appropriate Government, for every completed year of "
            "continuous service or any part thereof in excess of six months; and\n"
            "(c) notice in the prescribed manner is served on the appropriate Government or such "
            "authority as may be specified by the appropriate Government by notification."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/22040/1/a35_of_2020.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "If you have completed one year and are retrenched, you are owed ONE MONTH'S written "
            "notice (or one month's wages instead) PLUS 15 days' average pay for every completed "
            "year of service — and the government has to be told. A retrenchment done without "
            "these is illegal."
        ),
        "keywords": [
            "ir code 70", "retrenchment", "retrenched", "laid off", "layoff compensation",
            "termination compensation", "notice pay", "one month notice termination",
            "15 days pay per year", "illegal termination", "wrongful termination",
            "fired without notice", "job loss compensation", "removed from job",
            "terminated without reason", "severance pay",
        ],
    },
    {
        "key": "ir_71",
        "citation": "Industrial Relations Code 2020, Section 71 — Procedure for retrenchment (last in, first out) and re-employment",
        "short_label": "IR Code 71",
        "act": "Industrial Relations Code",
        "text_kind": "official_summary",
        "require_any": _WORK_GUARD,
        "official_text": (
            "Where any worker in an industrial establishment who is a citizen of India is to be "
            "retrenched and he belongs to a particular category of workers in that "
            "establishment, in the absence of any agreement between the employer and the worker "
            "in this behalf, the employer shall ordinarily retrench the worker who was the LAST "
            "person to be employed in that category, unless for reasons to be recorded the "
            "employer retrenches any other worker.\n"
            "Where any workers are retrenched and the employer proposes to take into his employ "
            "any persons within one year of such retrenchment, the employer shall give an "
            "opportunity to the retrenched workers who are citizens of India to offer themselves "
            "for re-employment, and such retrenched workers shall have preference over other "
            "persons."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/22040/1/a35_of_2020.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Retrenchment normally follows 'last in, first out' within your job category — if a "
            "junior person was kept and you were removed, the employer must have recorded written "
            "reasons. If the company hires again within one year, retrenched workers get first "
            "preference."
        ),
        "keywords": [
            "ir code 71", "last in first out", "seniority retrenchment",
            "junior kept senior removed", "re employment after retrenchment",
            "company hiring again after layoff", "unfair selection retrenchment",
        ],
    },
    {
        "key": "ss_53",
        "citation": "Code on Social Security 2020, Section 53 — Payment of gratuity",
        "short_label": "SS Code 53",
        "act": "Code on Social Security",
        "text_kind": "official_summary",
        "require_any": _WORK_GUARD + ["gratuity", "retire", "retirement"],
        "official_text": (
            "Gratuity shall be payable to an employee on the termination of his employment after "
            "he has rendered continuous service for not less than five years—(a) on his "
            "superannuation; (b) on his retirement or resignation; (c) on his death or "
            "disablement due to accident or disease; (d) on termination of his contract period "
            "under fixed term employment; or (e) on the happening of any such event as may be "
            "notified by the Central Government.\n"
            "The condition of five years' continuous service is NOT necessary where the "
            "termination is due to death or disablement, or in the case of a fixed term employee "
            "or a working journalist, for whom the qualifying period is as provided in the Code.\n"
            "For every completed year of service, or part thereof in excess of six months, the "
            "employer shall pay gratuity at the rate of fifteen days' wages, based on the rate of "
            "wages last drawn by the employee."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/16823/1/aA2020-36.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "After five years with the same employer you are owed gratuity — 15 days' wages for "
            "every completed year, calculated on your last drawn wages. The five-year condition "
            "does not apply on death or disablement, and fixed-term employees qualify earlier as "
            "provided in the Code."
        ),
        "keywords": [
            "ss code 53", "gratuity", "gratuity eligibility", "gratuity 5 years",
            "gratuity calculation", "gratuity not paid", "gratuity after resignation",
            "gratuity fixed term", "gratuity on death", "how much gratuity",
        ],
    },
]
