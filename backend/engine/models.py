"""Shared Pydantic models for the 7-layer reasoning pipeline."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Jurisdiction(BaseModel):
    country: str = "India"
    state: Optional[str] = None
    district: Optional[str] = None


class LegalQuery(BaseModel):
    """Output of Layer A — Query Parser.  Persisted in session as CaseState."""
    original_query: str = ""
    normalized_query: str = ""
    language: str = "en"
    jurisdiction: Jurisdiction = Field(default_factory=Jurisdiction)
    event_date: Optional[str] = None          # ISO date string
    actions: List[str] = Field(default_factory=list)
    actors: List[str] = Field(default_factory=list)
    actor_roles: List[str] = Field(default_factory=list)
    objects: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    location_types: List[str] = Field(default_factory=list)
    intent: List[str] = Field(default_factory=list)
    harm: List[str] = Field(default_factory=list)
    candidate_issues: List[str] = Field(default_factory=list)
    missing_material_facts: List[str] = Field(default_factory=list)
    urgency: str = "standard"           # immediate | standard | informational
    requested_outcome: str = ""
    # ACTOR-CONDUCT LOCK (structural invariant — see README_DEPLOYMENT.md).
    # The role the USER explicitly identifies as (e.g. "tenant", "bystander",
    # "journalist", "employee", "victim") — DISTINCT from `actor_roles`, which
    # is who PERFORMS the regulated conduct described in the query (e.g.
    # "landlord", "police", "employer"). These two are often different
    # people; conflating them is exactly the bug this invariant prevents.
    asking_as_role: Optional[str] = None

    def merge_update(self, new: "LegalQuery") -> "LegalQuery":
        """Merge a CLARIFICATION turn into existing state.

        Rules:
        - New non-empty actions / actors / objects REPLACE old values.
        - New jurisdiction fields REPLACE only if not None.
        - Original query keeps the FIRST query's wording.
        - Missing material facts are refreshed from new query.
        """
        merged = self.model_copy()
        if new.actions:
            merged.actions = new.actions
        if new.actors:
            merged.actors = new.actors
        if new.actor_roles:
            merged.actor_roles = new.actor_roles
        if new.objects:
            merged.objects = new.objects
        if new.locations:
            merged.locations = new.locations
        if new.location_types:
            merged.location_types = new.location_types
        if new.intent:
            merged.intent = new.intent
        if new.harm:
            merged.harm = new.harm
        if new.jurisdiction.state:
            merged.jurisdiction.state = new.jurisdiction.state
        if new.jurisdiction.district:
            merged.jurisdiction.district = new.jurisdiction.district
        if new.event_date:
            merged.event_date = new.event_date
        merged.missing_material_facts = new.missing_material_facts
        merged.normalized_query = new.normalized_query or merged.normalized_query
        return merged


class ClassifyResult(BaseModel):
    """Output of Layer B — Conduct Classifier."""
    primary_domain: str = "unknown"
    secondary_domains: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    action_basis: str = ""
    excluded_domains: List[str] = Field(default_factory=list)
    exclusion_reasons: Dict[str, str] = Field(default_factory=dict)
    # ACTOR-CONDUCT LOCK fields (see README_DEPLOYMENT.md > Engine Architecture).
    regulated_actor: Optional[str] = None      # WHO is regulated by this conduct
    regulated_conduct: Optional[str] = None    # WHAT conduct is regulated
    user_role: Optional[str] = None            # who the USER says they are
    actor_mismatch: bool = False               # True => user is asking about
                                                # someone ELSE's obligations


class FactCheckResult(BaseModel):
    """Output of Layer C — Material Fact Detector."""
    answer_mode: str = "DIRECT"     # DIRECT | CONDITIONAL | ESCALATE
    missing_facts: List[str] = Field(default_factory=list)
    follow_up_question: Optional[str] = None
    conditional_branches: List[Dict[str, str]] = Field(default_factory=list)


class ApplicabilityScore(BaseModel):
    """Output of Layer H — Irrelevance Filter, per provision."""
    provision: str = ""
    act: str = ""
    section: str = ""
    classification: str = "IRRELEVANT"  # APPLICABLE | BACKGROUND | IRRELEVANT | SUPERSEDED
    reason: str = ""
    guard_triggered: Optional[str] = None


class StatusRecord(BaseModel):
    """One record from law_status_registry.json, post-load."""
    act_id: str
    short_name: str
    status: str            # ACTIVE | REPEALED | SUPERSEDED | etc.
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    successor_act: Optional[str] = None
    successor_act_id: Optional[str] = None
    status_reason: str = ""
    source_url: str = ""
    source_type: str = ""
    verified_at: Optional[str] = None


class VerifiedClaim(BaseModel):
    """Output of Layer V — Claim-to-Source Verification, per claim."""
    claim_text: str
    claim_type: str = "UNKNOWN"   # VERIFIED_LEGAL_RULE | VERIFIED_PROCEDURE | VERIFIED_RIGHT |
                                   # VERIFIED_DEADLINE | VERIFIED_PENALTY | VERIFIED_REMEDY |
                                   # USER_PROVIDED_FACT | MODEL_EXPLANATION | UNKNOWN
    source_provision: Optional[str] = None
    source_act: Optional[str] = None
    is_supported: bool = False
    confidence: float = 0.0


class CaseState(BaseModel):
    """Full conversation state persisted in MongoDB per session."""
    session_id: str = ""
    turn_count: int = 0
    legal_query: Optional[LegalQuery] = None
    classify_result: Optional[ClassifyResult] = None
    turn_type_history: List[str] = Field(default_factory=list)
    # Extra semantic fields accumulated from clarification turns
    religion: Optional[str] = None
    relationship_type: Optional[str] = None
    asset_type: Optional[str] = None
    marriage_status: Optional[str] = None
    custom_facts: Dict[str, Any] = Field(default_factory=dict)

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, d: dict) -> "CaseState":
        return cls.model_validate(d)
