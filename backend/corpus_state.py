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
    # -------------------- BIHAR — rent / tenancy --------------------
    {
        "key": "br_rent_premises",
        "state": "BR",
        "citation": "Bihar Premises (Control of Rent and Eviction) Act 1947 — Tenant protection and eviction grounds",
        "short_label": "Bihar Rent Control Act",
        "act": "Bihar Premises (Control of Rent and Eviction) Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "The Bihar Premises (Control of Rent and Eviction) Act, 1947 applies to urban "
            "premises in the State. Under this Act, no landlord can evict a tenant except "
            "through an order of the Rent Controller on one of the specified grounds, which "
            "include: non-payment of rent; sub-letting without the landlord's consent; using "
            "the premises for a purpose other than that for which they were let; conduct "
            "amounting to nuisance; and bona fide requirement of the landlord for personal "
            "occupation.\n\n"
            "Important: Bihar does NOT yet have a modern rent-regulation law on the lines of "
            "the Central Model Tenancy Act 2021 (which Bihar has not adopted as of mid-2026). "
            "The 1947 Act is quite old and its coverage and procedures vary by district. For "
            "any tenancy dispute in Bihar the best first step is to approach the Rent Controller "
            "(usually the Civil Court of the concerned district) or contact NALSA on 15100 for "
            "free legal aid."
        ),
        "source_url": "https://law.bihar.gov.in",
        "verified_at": "2026-06-01",
        "scope_note": (
            "Bihar tenants are protected by the 1947 Act, but the law is old and the procedures "
            "can be slow. For a landlord to evict you, they must get an order from the Rent "
            "Controller. A landlord who locks you out without a court order is acting illegally. "
            "Bihar has NOT adopted the Model Tenancy Act 2021, so there is no 2-month deposit "
            "cap or mandatory written agreement under state law yet — your written agreement "
            "and proof of rent payment are your main protection."
        ),
        "keywords": [
            "bihar rent", "patna rent", "bihar tenant", "bihar landlord", "bihar eviction",
            "bihar rent control", "landlord evicting me bihar", "bihar vacate notice",
            "bihar rent dispute", "gaya rent", "muzaffarpur rent", "bhagalpur rent",
            "bihar security deposit", "bihar rent advance", "patna landlord eviction",
        ],
    },
    # -------------------- DELHI — rent --------------------
    {
        "key": "dl_rent_14",
        "state": "DL",
        "citation": "Delhi Rent Control Act 1958, Section 14 — Protection of tenant against eviction",
        "short_label": "Delhi Rent Control 14",
        "act": "Delhi Rent Control Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "Notwithstanding anything to the contrary contained in any other law or contract, no "
            "order or decree for the recovery of possession of any premises shall be made by any "
            "court or Controller in favour of the landlord against a tenant, except on one or "
            "more of the grounds set out in section 14(1), which include—non-payment of rent "
            "within two months of a notice of demand; unlawful sub-letting or parting with "
            "possession without the landlord's written consent; use of the premises for a purpose "
            "other than that for which they were let; the premises not being used for the purpose "
            "let for six months immediately before the application; the tenant acquiring vacant "
            "possession of, or being allotted, another suitable residence; and bona fide "
            "requirement of the premises by the landlord for occupation as a residence for "
            "himself or his family, where the landlord has no other reasonably suitable "
            "accommodation.\n"
            "Where the ground is non-payment of rent, no order for eviction shall be made if the "
            "tenant pays or deposits the arrears of rent, with interest and costs, within the "
            "time allowed by the Controller — and this protection is available to a tenant only "
            "once.\n"
            "A landlord who has acquired the premises by transfer cannot apply for eviction on "
            "the bona-fide-requirement ground before the expiry of five years from the date of "
            "the transfer (section 14(6)).\n"
            "This Act applies only to premises whose monthly rent does not exceed three thousand "
            "five hundred rupees; tenancies above that rent are governed by the tenancy contract "
            "and the Transfer of Property Act, 1882."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/19223/1/a1958-59.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Delhi a landlord cannot simply throw you out — eviction needs a Rent Controller's "
            "order on one of the listed grounds. If the ground is unpaid rent, paying the arrears "
            "with interest in the time the Controller gives saves your tenancy (once only). This "
            "protection covers tenancies of ₹3,500 a month or less; above that, your written "
            "agreement governs."
        ),
        "keywords": [
            "delhi rent", "delhi tenant", "delhi landlord", "delhi eviction",
            "delhi rent control", "landlord evicting me delhi", "delhi vacate notice",
            "delhi rent arrears", "delhi subletting", "delhi rent controller",
            "delhi tenancy dispute", "delhi rent 3500",
        ],
    },
    # -------------------- MAHARASHTRA — rent --------------------
    {
        "key": "mh_rent_16",
        "state": "MH",
        "citation": "Maharashtra Rent Control Act 1999, Section 16 — When landlord may recover possession",
        "short_label": "Maharashtra Rent Control 16",
        "act": "Maharashtra Rent Control Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "A landlord is entitled to recover possession of premises only on an order of the "
            "Competent Authority or Court, and only where the Court is satisfied of one or more "
            "of the grounds in section 16(1), which include—the tenant has not paid the standard "
            "rent and permitted increases due within ninety days of a notice of demand; the "
            "tenant has unlawfully sub-let, assigned or transferred his interest; the tenant has "
            "erected a permanent structure without the landlord's written consent; the tenant or "
            "any person residing with him has been guilty of conduct which is a nuisance or "
            "annoyance to neighbours; the premises are reasonably and bona fide required by the "
            "landlord for occupation by himself or by any person for whose benefit the premises "
            "are held; and the premises have not been used without reasonable cause for the "
            "purpose for which they were let for a continuous period of six months.\n"
            "Where the ground is non-payment of rent, no decree for eviction shall be passed if "
            "the tenant pays or tenders in Court the standard rent and permitted increases, "
            "together with the costs of the suit, on the first day of hearing or on such other "
            "date as the Court may fix.\n"
            "The Act also allows a landlord to increase the rent by not more than four per cent "
            "per year over the standard rent, and requires a written rent receipt for every "
            "payment received."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/15817/1/the_maharashtra_rent_control_act_1999.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Maharashtra your landlord needs a court order on a listed ground to evict you, and "
            "clearing the arrears with costs on the first hearing date stops an eviction for "
            "unpaid rent. The landlord must give you a rent receipt, and the yearly rent increase "
            "under this Act is capped at 4%."
        ),
        "keywords": [
            "maharashtra rent", "mumbai rent", "pune rent", "maharashtra tenant",
            "maharashtra landlord", "mumbai eviction", "maharashtra rent control",
            "landlord evicting me mumbai", "rent receipt maharashtra", "rent increase maharashtra",
            "maharashtra vacate notice", "leave and licence", "pagdi tenant",
        ],
    },
    # -------------------- KARNATAKA — rent --------------------
    {
        "key": "ka_rent_27",
        "state": "KA",
        "citation": "Karnataka Rent Act 1999, Section 27 — Protection of tenant against eviction",
        "short_label": "Karnataka Rent Act 27",
        "act": "Karnataka Rent Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "Notwithstanding anything contained in any other law, no order or decree for recovery "
            "of possession of any premises shall be made by the Court in favour of the landlord "
            "against the tenant except on an application made to it on one or more of the grounds "
            "in section 27(2), which include—the tenant has neither paid nor tendered the whole "
            "of the arrears of rent within two months of the date on which a notice of demand was "
            "served; the tenant has sub-let, assigned or otherwise parted with possession of the "
            "premises without the landlord's written permission; the tenant has used the premises "
            "for a purpose other than that for which they were let; the tenant or any person "
            "residing with him has been guilty of conduct which is a nuisance or annoyance to "
            "the occupiers of adjoining premises; and the premises are required bona fide by the "
            "landlord for occupation by himself or by any member of his family.\n"
            "Where the ground is non-payment of rent, no order for eviction shall be made if the "
            "tenant pays the arrears with interest and the cost of the proceedings within the "
            "time fixed by the Court, and the tenant is entitled to this relief once only.\n"
            "The Act also requires the landlord to give a written receipt for the rent and "
            "advance received, and permits the Court to fix the fair rent on an application."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/7810/1/34_of_2001_e.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Karnataka a landlord must go to Court and prove a listed ground to evict you; "
            "locking you out or cutting water and power is not lawful. Clearing the arrears with "
            "interest in the time the Court gives saves the tenancy (once). Insist on a written "
            "receipt for rent and advance."
        ),
        "keywords": [
            "karnataka rent", "bangalore rent", "bengaluru rent", "karnataka tenant",
            "karnataka landlord", "bangalore eviction", "karnataka rent act",
            "landlord evicting me bangalore", "rent receipt karnataka", "karnataka fair rent",
            "karnataka vacate notice", "advance rent bangalore",
        ],
    },
    # -------------------- TAMIL NADU — rent --------------------
    {
        "key": "tn_tenancy_4",
        "state": "TN",
        "citation": "Tamil Nadu Regulation of Rights and Responsibilities of Landlords and Tenants Act 2017, Section 4 — Tenancy agreement and registration",
        "short_label": "TN Tenancy Act 4",
        "act": "Tamil Nadu Tenancy Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "No person shall, after the commencement of this Act, let or take on rent any "
            "premises except by an agreement in writing. The landlord and the tenant shall "
            "jointly intimate the Rent Authority about the tenancy agreement, in the prescribed "
            "form, within the period prescribed from the date of the agreement, and the Rent "
            "Authority shall, on receipt of the intimation, register the tenancy agreement and "
            "issue a unique identification number to the parties.\n"
            "Where the agreement is entered into before the commencement of this Act, the parties "
            "shall jointly intimate the Rent Authority within the prescribed period. Any "
            "amendment to the terms of the tenancy shall likewise be intimated to the Rent "
            "Authority.\n"
            "A tenancy registered under this Act continues for the period agreed; on expiry the "
            "tenant is liable to pay enhanced rent as prescribed for the period of unlawful "
            "occupation, and the landlord may apply to the Rent Court for eviction."
        ),
        "source_url": "https://prsindia.org/files/bills_acts/acts_states/tamil-nadu/2017/2017TN42.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Tamil Nadu every tenancy must be in WRITING and registered with the Rent "
            "Authority — both landlord and tenant have to file it jointly and they get a unique "
            "number. An unregistered oral tenancy weakens both sides in any dispute, so insist on "
            "the written registered agreement."
        ),
        "keywords": [
            "tamil nadu rent", "chennai rent", "tamil nadu tenant", "tamil nadu landlord",
            "chennai eviction", "tamil nadu tenancy act", "rent agreement registration tamil nadu",
            "rent authority tamil nadu", "written rent agreement chennai",
            "tamil nadu rent court", "coimbatore rent", "madurai rent",
        ],
    },
    {
        "key": "tn_tenancy_11",
        "state": "TN",
        "citation": "Tamil Nadu Regulation of Rights and Responsibilities of Landlords and Tenants Act 2017, Section 11 — Security deposit",
        "short_label": "TN Tenancy Act 11",
        "act": "Tamil Nadu Tenancy Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "The security deposit to be paid by the tenant in advance shall not exceed three "
            "months' rent in the case of residential premises, and shall not exceed the amount "
            "prescribed for non-residential premises.\n"
            "The security deposit shall be refunded to the tenant on the date of taking over "
            "vacant possession of the premises, after making due deductions of any liability of "
            "the tenant towards the landlord."
        ),
        "source_url": "https://prsindia.org/files/bills_acts/acts_states/tamil-nadu/2017/2017TN42.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Tamil Nadu a landlord cannot demand more than THREE MONTHS' rent as advance or "
            "security deposit for a home, and the deposit must be returned when you hand over "
            "vacant possession, minus any genuine dues."
        ),
        "keywords": [
            "tamil nadu security deposit", "chennai advance rent", "tamil nadu advance deposit",
            "how much advance chennai", "deposit refund tamil nadu", "3 months advance chennai",
            "landlord not returning deposit chennai", "tamil nadu deposit limit",
        ],
    },
    # -------------------- UTTAR PRADESH — rent --------------------
    {
        "key": "up_tenancy_4",
        "state": "UP",
        "citation": "Uttar Pradesh Regulation of Urban Premises Tenancy Act 2021, Section 4 — Tenancy agreement and intimation to Rent Authority",
        "short_label": "UP Tenancy Act 4",
        "act": "UP Urban Premises Tenancy Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "No person shall, after the commencement of this Act, let or take on rent any premises "
            "except by an agreement in writing. The landlord and the tenant shall jointly inform "
            "the Rent Authority about the tenancy agreement in the prescribed form within the "
            "prescribed period, and the Rent Authority shall provide a unique identification "
            "number to the parties.\n"
            "Where a tenancy existed before the commencement of this Act, the landlord and the "
            "tenant shall jointly submit the information to the Rent Authority within the "
            "prescribed period. Any subsequent change in the terms of the tenancy shall also be "
            "intimated jointly.\n"
            "Where the tenancy period expires and the tenant continues in occupation, the tenant "
            "is liable to pay enhanced rent as provided in the Act for the period of such "
            "occupation."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/21157",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Uttar Pradesh every tenancy must be a WRITTEN agreement, and landlord and tenant "
            "must jointly report it to the Rent Authority to get a unique number. Old tenancies "
            "also have to be reported. Keep your copy — it is your main proof in any dispute."
        ),
        "keywords": [
            "up rent", "uttar pradesh rent", "lucknow rent", "noida rent", "kanpur rent",
            "uttar pradesh tenant", "uttar pradesh landlord", "up tenancy act",
            "rent agreement registration up", "rent authority up", "up eviction",
            "ghaziabad rent", "varanasi rent", "agra rent",
        ],
    },
    {
        "key": "up_tenancy_11",
        "state": "UP",
        "citation": "Uttar Pradesh Regulation of Urban Premises Tenancy Act 2021, Section 11 — Security deposit",
        "short_label": "UP Tenancy Act 11",
        "act": "UP Urban Premises Tenancy Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "The security deposit to be paid by the tenant in advance shall not exceed two "
            "months' rent in the case of residential premises, and shall not exceed six months' "
            "rent in the case of non-residential premises.\n"
            "The security deposit shall be refunded to the tenant on the date of taking over "
            "vacant possession of the premises from the tenant, after making due deduction of any "
            "liability of the tenant."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/21157",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Uttar Pradesh the advance or security deposit cannot be more than TWO months' "
            "rent for a home (six months for a shop or office), and it must be refunded when you "
            "hand over vacant possession, minus genuine dues."
        ),
        "keywords": [
            "up security deposit", "uttar pradesh advance rent", "lucknow advance deposit",
            "noida deposit limit", "up deposit refund", "2 months advance up",
            "landlord not returning deposit up", "up deposit limit",
        ],
    },
    # -------------------- TELANGANA — rent --------------------
    {
        "key": "tg_rent_10",
        "state": "TG",
        "citation": "Telangana Buildings (Lease, Rent and Eviction) Control Act 1960, Section 10 — Eviction of tenants",
        "short_label": "Telangana Rent Control 10",
        "act": "Telangana Buildings (Lease, Rent and Eviction) Control Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "A tenant in possession of a building shall not be evicted, whether in execution of a "
            "decree or otherwise, except in accordance with the provisions of this section. The "
            "landlord must apply to the Rent Controller, who may pass an eviction order only if "
            "satisfied of one or more of the grounds in section 10(2), which include—the tenant "
            "has not paid or tendered the rent due within fifteen days after the expiry of the "
            "time fixed in the tenancy agreement or, in the absence of such agreement, by the "
            "last day of the month next following that for which the rent is payable; the tenant "
            "has, after 1 April 1956, without the landlord's written consent, transferred his "
            "right under the lease or sub-let the building; the tenant has used the building for "
            "a purpose other than that for which it was leased; the tenant has committed acts of "
            "waste likely to impair materially the value or utility of the building; the tenant "
            "has been convicted of using the building for an immoral or illegal purpose; the "
            "tenant has been guilty of conduct which is a nuisance to occupiers of other portions "
            "or of neighbouring buildings; the tenant has ceased to occupy the building for a "
            "continuous period of four months without reasonable cause; and the tenant has denied "
            "the title of the landlord or claimed a right of permanent tenancy and such denial or "
            "claim was not bona fide.\n"
            "Where the ground is non-payment of rent, the Controller shall give the tenant a "
            "reasonable time, not exceeding fifteen days, to pay or tender the rent due, and if "
            "the tenant does so the application for eviction shall be rejected."
        ),
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/8607/1/act_15_of_1960.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Telangana your landlord must go to the Rent Controller and prove a listed ground "
            "to evict you. Even for unpaid rent, the Controller must first give you up to 15 days "
            "to pay — if you pay, the eviction petition is rejected."
        ),
        "keywords": [
            "telangana rent", "hyderabad rent", "telangana tenant", "telangana landlord",
            "hyderabad eviction", "telangana rent control", "rent controller hyderabad",
            "landlord evicting me hyderabad", "telangana vacate notice", "secunderabad rent",
            "warangal rent",
        ],
    },
    # -------------------- WEST BENGAL — rent --------------------
    {
        "key": "wb_rent_6",
        "state": "WB",
        "citation": "West Bengal Premises Tenancy Act 1997, Sections 6 and 7 — Protection against eviction and deposit of rent in a suit",
        "short_label": "WB Premises Tenancy 6-7",
        "act": "West Bengal Premises Tenancy Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "No order or decree for the recovery of possession of any premises shall be made by "
            "any court in favour of the landlord against a tenant, except on one or more of the "
            "grounds provided in the Act, which include—the tenant has defaulted in payment of "
            "rent for two months within a period of twelve months; the tenant has, without the "
            "previous consent in writing of the landlord, sub-let, assigned or transferred the "
            "whole or any part of the premises; the tenant has used the premises for a purpose "
            "other than that for which they were let; the tenant has caused or permitted to be "
            "caused substantial damage to the premises; the tenant has been guilty of conduct "
            "which is a nuisance or annoyance to the occupiers of neighbouring premises; the "
            "premises are reasonably required by the landlord for his own occupation or for "
            "building or rebuilding; and the tenant has ceased to occupy the premises without "
            "reasonable cause.\n"
            "In a suit or proceeding for recovery of possession on the ground of default in "
            "payment of rent, the tenant may, within one month of the service of the writ of "
            "summons, deposit in court the entire amount of rent in arrears together with "
            "interest at the rate of ten per cent per annum and continue to deposit the rent "
            "month by month; where the tenant does so and complies with the Act, relief against "
            "eviction on that ground is available to him."
        ),
        "source_url": "https://prsindia.org/files/bills_acts/acts_states/west-bengal/1997/1997WB37.pdf",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In West Bengal a court order on a listed ground is needed to evict you. If the ground "
            "is rent default, depositing the arrears in court with 10% a year interest within a "
            "month of the summons — and paying month by month after that — protects you from "
            "eviction on that ground."
        ),
        "keywords": [
            "west bengal rent", "kolkata rent", "west bengal tenant", "west bengal landlord",
            "kolkata eviction", "west bengal tenancy act", "rent default kolkata",
            "landlord evicting me kolkata", "deposit rent in court", "howrah rent",
            "siliguri rent",
        ],
    },
    # -------------------- KERALA — rent --------------------
    {
        "key": "kl_rent_11",
        "state": "KL",
        "citation": "Kerala Buildings (Lease and Rent Control) Act 1965, Section 11 — Eviction of tenants",
        "short_label": "Kerala Rent Control 11",
        "act": "Kerala Buildings (Lease and Rent Control) Act",
        "text_kind": "official_summary",
        "require_any": [
            "rent", "tenant", "tenancy", "landlord", "evict", "eviction", "vacate",
            "deposit", "advance", "lease", "sublet", "sub-let", "house owner",
            "paying guest", "pg", "premises",
        ],
        "official_text": (
            "Notwithstanding anything to the contrary contained in any other law or contract, a "
            "tenant shall not be evicted except in accordance with the provisions of this "
            "section. A landlord who seeks to evict his tenant shall apply to the Rent Control "
            "Court, and the Court may order eviction only if satisfied of one or more of the "
            "grounds in section 11, which include—the tenant has not paid or tendered the rent "
            "due within fifteen days after the expiry of the time fixed in the agreement or, in "
            "the absence of such agreement, by the last day of the month next following that for "
            "which the rent is payable; the tenant has, after the commencement of the Act and "
            "without the landlord's written consent, transferred his right under the lease or "
            "sub-let the building; the tenant has used the building in such a manner as to reduce "
            "its value or utility materially and permanently; the tenant has ceased to occupy the "
            "building continuously for six months without reasonable cause; and the building is "
            "bona fide required by the landlord for his own occupation, or for reconstruction, or "
            "the tenant has secured other suitable accommodation.\n"
            "Where the ground is arrears of rent, the Rent Control Court shall, before ordering "
            "eviction, give the tenant a reasonable time to pay or tender the arrears with "
            "interest and costs, and where the tenant complies the application shall be rejected."
        ),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/14542",
        "verified_at": "2026-06-01",
        "scope_note": (
            "In Kerala only the Rent Control Court can evict you, and only on a listed ground. "
            "For rent arrears the Court must first give you time to pay with interest and costs — "
            "if you pay, the eviction petition is rejected."
        ),
        "keywords": [
            "kerala rent", "kochi rent", "ernakulam rent", "kerala tenant", "kerala landlord",
            "kerala eviction", "rent control court kerala", "landlord evicting me kerala",
            "thiruvananthapuram rent", "kozhikode rent", "kerala vacate notice",
        ],
    },
]

# ---------------------------------------------------------------------------
# Jurisdiction gating.
#
# Rent control, liquor/excise, traffic compounding amounts, police conduct rules
# and stamp duty are STATE subjects — the central corpus can only give half the
# answer. When a question falls in one of these buckets we must say so plainly
# instead of pretending the central position is the whole law. Where we hold a
# verified entry for the user's state we show it; where we do not, we name the
# authority the user should check, and we NEVER guess an amount.
# ---------------------------------------------------------------------------
STATE_SENSITIVE_TOPICS = {
    "rent_tenancy": {
        "label": "rent and tenancy",
        "keywords": [
            "rent", "rental", "landlord", "tenant", "tenancy", "eviction", "evict",
            "vacate", "security deposit", "advance rent", "rent agreement", "sublet",
            "subletting", "rent control", "house owner", "paying guest", "pg accommodation",
            "lease", "leave and licence", "rent increase", "rent receipt", "deposit refund",
        ],
        "authority": "your State Rent Authority or Rent Controller",
    },
    "traffic_compounding": {
        "label": "traffic fine amounts",
        "keywords": [
            "challan", "traffic fine", "compounding", "fine amount", "spot fine",
            "e challan", "echallan", "traffic police fine", "pay challan",
            "virtual court challan", "lok adalat challan",
        ],
        "authority": "your State Transport Department / traffic police e-challan portal",
    },
    "liquor_excise": {
        "label": "liquor and excise rules",
        "keywords": [
            "liquor", "alcohol", "daru", "sharab", "drinking age", "dry state",
            "liquor permit", "excise", "bar licence", "beer shop",
        ],
        "authority": "your State Excise Department",
    },
    "stamp_registration": {
        "label": "stamp duty and registration charges",
        "keywords": [
            "stamp duty", "stamp paper", "registration charges", "sub registrar",
            "property registration fee", "e stamp",
        ],
        "authority": "your State Registration & Stamps Department",
    },
}

