"""Layer B — Conduct Classifier.

Maps parsed actions to legal domain taxonomy nodes.
DETERMINISTIC — no LLM call. The taxonomy is the index into the corpus.
ACTION determines the domain, not keywords or location names.
"""
from __future__ import annotations
from typing import Dict, List, Optional
import logging

from engine.models import LegalQuery, ClassifyResult

logger = logging.getLogger("gandhikar")

# ── Legal Domain Taxonomy ─────────────────────────────────────────────────────
# Maps: domain_id → {actions, statutes, notes}
DOMAIN_TAXONOMY: Dict[str, Dict] = {
    "property_access": {
        "actions": {"enter", "trespass", "evict", "restrict_access", "refuse_entry", "damage"},
        "primary_statutes": ["BNS §329 (criminal trespass)", "Transfer of Property Act",
                              "state tenancy acts", "BNSS cognizable offences"],
        "NEVER_include": ["Places of Worship (Special Provisions) Act, 1991"],
        "note": "entry/trespass at a place of worship is property_access, NOT religious_character_change",
    },
    "religious_character_change": {
        "actions": {"change_religious_character", "convert_religion"},
        "primary_statutes": ["Places of Worship (Special Provisions) Act 1991 §3, §4"],
        "trigger_condition": "explicit facts about converting a place from one religion to another",
        "NEVER_triggered_by": ["entering", "visiting", "walking into a place of worship"],
    },
    "religious_offence": {
        "actions": {"defile", "desecrate", "disrupt_worship", "insult", "hate_speech"},
        "primary_statutes": ["BNS §298 (wounding religious feelings)", "BNS §299 (deliberate outraging)",
                              "BNS §302 (promoting enmity)"],
        "note": "entering is NOT a religious offence by default",
    },
    "criminal_hurt_and_assault": {
        "actions": {"hit", "assault", "threaten", "intimidate", "hurt", "kill"},
        "primary_statutes": ["BNS §115–§126 (hurt/grievous hurt)", "BNS §351–§353 (assault/criminal force)"],
    },
    "criminal_procedure": {
        "actions": {"arrest", "detain", "bail", "search", "seize",
                    "file_fir", "file_complaint", "release",
                    "arrest_police", "detain_police", "custody", "remand",
                    "refuse_fir", "refuse_complaint"},  # FIR refusal by police
        "primary_statutes": ["BNSS (Bharatiya Nagarik Suraksha Sanhita)",
                              "BNS", "Constitution Articles 20–22"],
        "_priority": 2,
    },
    "defamation_and_speech": {
        "actions": {"publish", "defame", "broadcast", "incite"},
        "primary_statutes": ["BNS §356 (defamation)", "BNS §196–§197 (promoting enmity)"],
    },
    "data_and_privacy": {
        "actions": {"collect_data", "share_data", "record", "photograph", "surveil"},
        "primary_statutes": ["DPDP Act 2023", "IT Act §43A", "IT Act §72A"],
    },
    "employment": {
        "actions": {"employ", "dismiss", "terminate", "suspend", "discriminate"},
        "primary_statutes": ["Industrial Disputes Act", "Shops and Establishments Acts",
                              "Payment of Wages Act", "POSH Act 2013"],
    },
    "voter_and_elections": {
        "actions": {"vote", "register_voter", "contest_election", "campaign"},
        "primary_statutes": ["Representation of People Act 1951",
                              "BNSS electoral offences", "Election Commission guidelines"],
        "_priority": 3,   # beats criminal_procedure when register_voter matches
    },
    "marriage_and_family": {
        "actions": {"marry", "divorce", "separate", "adopt", "custody", "maintenance"},
        "primary_statutes": ["Hindu Marriage Act 1955", "Special Marriage Act 1954",
                              "Muslim Personal Law", "Parsi Marriage Act",
                              "Adoption and Maintenance Acts"],
    },
    "property_transfer": {
        "actions": {"sell", "buy", "rent", "lease", "transfer", "mortgage", "inherit"},
        "primary_statutes": ["Transfer of Property Act", "Registration Act",
                              "Indian Succession Act", "Hindu Succession Act", "state land laws"],
    },
    "contract_and_fraud": {
        "actions": {"pay", "withhold_payment", "cheat", "fraud", "breach_contract"},
        "primary_statutes": ["Indian Contract Act 1872", "BNS §316–§318 (cheating)"],
    },
    "construction_and_land": {
        "actions": {"construct", "build", "alter", "develop", "encroach"},
        "primary_statutes": ["state municipal acts", "RERA", "land revenue codes"],
    },
    "environment": {
        "actions": {"pollute", "dump_waste", "deforest"},
        "primary_statutes": ["Environment Protection Act 1986", "Water Act 1974", "Forest Conservation Act"],
    },
    "traffic_and_vehicles": {
        "actions": {"drive", "park", "speed", "traffic_violation"},
        "primary_statutes": ["Motor Vehicles Act 1988 (as amended 2019)"],
    },
}

# Actions that explicitly EXCLUDE certain domains
_ENTRY_ACTIONS = {"enter", "trespass", "restrict_access", "refuse_entry", "evict"}
_RELIGIOUS_CHAR_ACTIONS = {"change_religious_character", "convert_religion"}


def classify(lq: LegalQuery) -> ClassifyResult:
    """Map actions → domain taxonomy. Deterministic, no LLM."""
    actions_set = set(lq.actions)
    location_types_set = set(lq.location_types)
    scored: List[tuple] = []  # (domain_id, confidence, action_basis)

    excluded: Dict[str, str] = {}

    # ── CRITICAL GUARD: enter + place_of_worship ≠ religious_character_change ─
    if _ENTRY_ACTIONS & actions_set and "place_of_worship" in location_types_set:
        excluded["religious_character_change"] = (
            "ACTION is 'enter'/'trespass' — this is property_access domain. "
            "religious_character_change only applies when the ACTION is change_religious_character."
        )

    for domain_id, spec in DOMAIN_TAXONOMY.items():
        if domain_id in excluded:
            continue
        matched_actions = actions_set & spec["actions"]
        if matched_actions:
            # Base confidence on how many actions matched + domain priority
            priority_bonus = spec.get("_priority", 0) * 0.05
            confidence = min(0.95, 0.6 + 0.1 * len(matched_actions) + priority_bonus)
            basis = ", ".join(sorted(matched_actions))
            scored.append((domain_id, confidence, basis))

    if not scored:
        # Fallback: look at candidate_issues
        issue_str = " ".join(lq.candidate_issues + lq.objects + lq.actions).lower()
        if any(w in issue_str for w in ("arrest", "police", "custody", "bail", "fir", "cognizable", "refuse")):
            scored.append(("criminal_procedure", 0.5, "candidate_issues"))
        elif any(w in issue_str for w in ("voter", "election", "vote", "ballot", "electoral")):
            scored.append(("voter_and_elections", 0.5, "candidate_issues"))
        elif any(w in issue_str for w in ("property", "land", "tenant", "landlord")):
            scored.append(("property_access", 0.4, "candidate_issues"))
        else:
            scored.append(("unknown", 0.2, "no_action_match"))

    # Sort by confidence desc
    scored.sort(key=lambda x: -x[1])
    primary_domain, primary_conf, action_basis = scored[0]
    secondary = [d for d, _, _ in scored[1:3]]

    regulated_actor, regulated_conduct, user_role, actor_mismatch = extract_actor_conduct(lq)

    result = ClassifyResult(
        primary_domain=primary_domain,
        secondary_domains=secondary,
        confidence=primary_conf,
        action_basis=action_basis,
        excluded_domains=list(excluded.keys()),
        exclusion_reasons=excluded,
        regulated_actor=regulated_actor,
        regulated_conduct=regulated_conduct,
        user_role=user_role,
        actor_mismatch=actor_mismatch,
    )
    logger.info("[classify] domain=%s conf=%.2f basis=%s excl=%s actor_mismatch=%s",
                primary_domain, primary_conf, action_basis, list(excluded.keys()), actor_mismatch)
    return result


# ── ACTOR-CONDUCT LOCK — Layer B extraction ──────────────────────────────────
# Structural invariant (see README_DEPLOYMENT.md > Engine Architecture).
# Before any obligation language (must/required/liable/responsible/duty/
# shall/cannot) reaches the user, the engine answers four questions:
#   1. WHO is regulated by this law/rule?       -> regulated_actor
#   2. WHAT specific conduct does it regulate?   -> regulated_conduct
#   3. Is the user asking about that actor?      -> user_role == regulated_actor ?
#   4. Did the user describe performing it?      -> same check, via actor_roles
# If 3 or 4 is "no", the engine must NOT transfer that obligation to the user
# (enforced downstream in engine/answer_generator.py's prompt augmentation +
# output reframing, wired into chat_router.py).

# Small alias groups so "officer" / "police" / "cop" etc. are recognised as
# the same regulated actor without needing an exhaustive exact-match list.
_ACTOR_ALIASES: List[set] = [
    {"police", "officer", "police officer", "cop", "constable", "sho", "station house officer"},
    {"landlord", "owner", "property owner", "property_owner"},
    {"employer", "company", "management", "organisation", "organization"},
    {"organizer", "organiser", "protest organizer", "protest organiser", "event organizer"},
]


def _normalise_role(role: Optional[str]) -> str:
    return (role or "").strip().lower()


def _roles_match(a: Optional[str], b: Optional[str]) -> bool:
    """True if two role strings plausibly refer to the same actor."""
    na, nb = _normalise_role(a), _normalise_role(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    for group in _ACTOR_ALIASES:
        if any(na == g or na in g for g in group) and any(nb == g or nb in g for g in group):
            return True
    return False


def extract_actor_conduct(lq: LegalQuery) -> tuple:
    """Layer B — actor-conduct extraction (pre-retrieval).

    Returns (regulated_actor, regulated_conduct, user_role, actor_mismatch).

    regulated_actor / regulated_conduct come straight from what the query
    itself says is performing / being done (lq.actor_roles / lq.actions) —
    this is architecture-level, not a per-domain lookup table, so it applies
    uniformly to every domain without needing a maintained action→actor map.

    actor_mismatch is ONLY ever True when the user has EXPLICITLY stated
    their own role (asking_as_role) and it does not match the regulated
    actor — i.e. positive evidence of a mismatch. If the user's role is not
    stated, we default to no-mismatch (preserves existing behaviour for the
    vast majority of queries where this never comes up).
    """
    regulated_actor = (lq.actor_roles[0] if lq.actor_roles else None)
    regulated_conduct = (
        lq.actions[0] if lq.actions
        else (lq.candidate_issues[0] if lq.candidate_issues else None)
    )
    user_role = lq.asking_as_role

    actor_mismatch = bool(
        user_role and regulated_actor and not _roles_match(user_role, regulated_actor)
    )
    return regulated_actor, regulated_conduct, user_role, actor_mismatch


def get_domain_statutes(domain_id: str) -> List[str]:
    """Return primary statutes for a domain."""
    spec = DOMAIN_TAXONOMY.get(domain_id)
    if not spec:
        return []
    return spec.get("primary_statutes", [])
