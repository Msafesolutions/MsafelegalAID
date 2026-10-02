"""Layer A — Query Parser.

Parses every user query into a LegalQuery object before any retrieval.
Uses a fast LLM (Claude Haiku) with structured JSON output.
Falls back to a minimal LegalQuery on timeout or parse error.
"""
from __future__ import annotations
import asyncio
import json
import uuid
import logging
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from engine.models import LegalQuery, Jurisdiction

logger = logging.getLogger("gandhikar")

_CANONICAL_ACTIONS = (
    "enter,exit,refuse_entry,restrict_access,evict,arrest,detain,bail,search,seize,release,"
    "hit,assault,threaten,intimidate,hurt,kill,trespass,damage,demolish,destroy,defile,"
    "desecrate,disrupt_worship,change_religious_character,convert_religion,"
    "publish,broadcast,defame,insult,incite,hate_speech,"
    "record,photograph,surveil,share_data,collect_data,"
    "sell,buy,rent,lease,transfer,mortgage,inherit,"
    "marry,divorce,separate,adopt,custody,maintenance,"
    "employ,dismiss,terminate,suspend,discriminate,"
    "vote,register_voter,contest_election,campaign,"
    "file_complaint,file_fir,file_petition,appeal,"
    "pay,withhold_payment,cheat,fraud,breach_contract,"
    "drive,park,speed,traffic_violation,"
    "construct,build,alter,develop,encroach,"
    "pollute,dump_waste,deforest"
)

_QUERY_PARSER_SYSTEM = f"""You are a legal query parser for an Indian law system.
Parse the user's query into structured JSON. Prioritize ACTIONS above all else.

CANONICAL ACTIONS (use ONLY these; pick the closest match):
{_CANONICAL_ACTIONS}

LOCATION TYPES: place_of_worship, private_property, public_road, workplace,
court, police_station, government_office, hospital, home, market, religious_place

CRITICAL RULE: action "enter" + location_type "place_of_worship" does NOT mean
domain "change_religious_character". Location is context. ACTION determines domain.

Output ONLY valid JSON matching this schema (no prose, no markdown):
{{
  "original_query": "<user's exact words>",
  "normalized_query": "<English restatement in 1 sentence>",
  "language": "<detected: en|hi|mr|ta|te|bn|gu|kn|ml|pa|or|auto>",
  "jurisdiction": {{"country": "India", "state": null, "district": null}},
  "event_date": null,
  "actions": ["<action from canonical list>"],
  "actors": ["<person or entity performing the action>"],
  "actor_roles": ["<e.g. landlord, police, employer, husband — whoever PERFORMS the action above>"],
  "asking_as_role": "<ONLY if the user explicitly frames themselves as a specific party in the situation — e.g. tenant, employee, bystander, journalist, victim, patient, customer, citizen, student. This is the USER's OWN role, which is often DIFFERENT from actor_roles above (e.g. a tenant asking about a LANDLORD's duties). null if not stated or unclear.>",
  "objects": ["<thing acted upon>"],
  "locations": ["<place name>"],
  "location_types": ["<type from list above>"],
  "intent": ["<purpose behind the action>"],
  "harm": ["<type of harm: physical|financial|emotional|legal|religious>"],
  "candidate_issues": ["<legal issue: e.g. trespass, arrest_rights, dowry>"],
  "missing_material_facts": ["<facts that would change the legal answer>"],
  "urgency": "immediate|standard|informational",
  "requested_outcome": "<what the user wants to know or achieve>"
}}"""


async def parse_query(
    query: str,
    language: str = "en",
    llm_key: str = "",
    prior_state: Optional[LegalQuery] = None,
) -> LegalQuery:
    """Run Layer A. Returns a LegalQuery. Never raises — falls back to minimal object."""

    # Build the prompt, including prior context if this is a continuation turn
    prompt = query
    if prior_state and prior_state.candidate_issues:
        prompt = (
            f"[PRIOR CONTEXT: issues={prior_state.candidate_issues}, "
            f"actions={prior_state.actions}, actors={prior_state.actor_roles}]\n"
            f"NEW USER MESSAGE: {query}"
        )

    async def _attempt() -> Optional[LegalQuery]:
        try:
            chat = LlmChat(
                api_key=llm_key,
                session_id=f"qparse-{uuid.uuid4().hex[:8]}",
                system_message=_QUERY_PARSER_SYSTEM,
            ).with_model("anthropic", "claude-haiku-4-5")

            raw = await asyncio.wait_for(
                chat.send_message(UserMessage(text=prompt)),
                timeout=10.0,
            )
            raw_str = str(raw or "").strip()

            # Extract JSON block
            start = raw_str.find("{")
            end = raw_str.rfind("}") + 1
            if start < 0 or end <= start:
                logger.warning("[qparser] no JSON in response: %r", raw_str[:80])
                return None

            data = json.loads(raw_str[start:end])
            # Normalise jurisdiction
            j = data.get("jurisdiction") or {}
            data["jurisdiction"] = {
                "country": j.get("country", "India"),
                "state": j.get("state"),
                "district": j.get("district"),
            }
            lq = LegalQuery.model_validate(data)
            if not lq.language or lq.language == "auto":
                lq.language = language
            logger.info("[qparser] ok | actions=%s | domain_candidates=%s",
                        lq.actions[:3], lq.candidate_issues[:3])
            return lq

        except asyncio.TimeoutError:
            logger.warning("[qparser] timeout(10s) | q=%r", query[:60])
        except json.JSONDecodeError as e:
            logger.warning("[qparser] JSON parse error: %s", e)
        except Exception as e:
            logger.warning("[qparser] error: %s", e)
        return None

    result = await _attempt()
    if result:
        return result

    # Minimal fallback — do not raise
    logger.warning("[qparser] using minimal fallback for q=%r", query[:60])
    return LegalQuery(
        original_query=query,
        normalized_query=query,
        language=language,
        jurisdiction=Jurisdiction(),
        actions=[],
        candidate_issues=[],
        urgency="standard",
        requested_outcome="unknown",
    )
