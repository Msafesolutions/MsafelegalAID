"""Layer M — Answer Generator hardening.

The existing `build_system_prompt` in dependencies.py already enforces most
of the sprint-brief's anti-hallucination rules (no verbatim law, no section
numbers, refuse when corpus is empty). This module supplements that with:

  1.  build_cannot_verify_response(lq, language) — used when Layer S filters
      the entire retrieved set down to REPEALED / SUPERSEDED provisions.
      Returns a deterministic string (no LLM call needed) that tells the
      user "we could not verify an active law for this specific fact set".

  2.  all_provisions_dead(hits) — the trigger predicate.

  3.  augment_prompt_with_status_guard(prompt, hits) — appends a plain-language
      instruction to the LLM prompt when at least one cited provision has been
      flagged as SUPERSEDED or REPEALED by Layer S. Prevents the model from
      answering as if the law were still in force.

  4.  strip_leaked_citations(text) — a defence-in-depth post-processor that
      pairs with corpus.sanitize_model_output; called from chat_router.

Every function here is pure (except the class docstring) — no I/O, no DB
access — so it is trivial to test.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional

from engine.models import LegalQuery


# ── Public predicates ─────────────────────────────────────────────────────────

def all_provisions_dead(hits: Iterable[dict]) -> bool:
    """True when every retrieved provision has been annotated as dead/superseded
    by Layer S (Law Status Guard). An empty iterable returns False — that is
    the 'no corpus match' case handled elsewhere by REFUSAL_NO_CORPUS.
    """
    hits = list(hits or [])
    if not hits:
        return False
    for h in hits:
        # Layer S annotations, plus MongoDB-corpus is_dead_law flag.
        if h.get("is_dead_law"):
            continue
        status = (h.get("status") or "").upper()
        if status in _DEAD_STATUSES:
            continue
        if (h.get("dead_warning") or "").strip():
            continue
        return False   # This one is alive → not all dead.
    return True


_DEAD_STATUSES = {
    "REPEALED",
    "SUPERSEDED",
    "STRUCK_DOWN",
    "NOT_YET_IN_FORCE",
    "PARTIALLY_REPEALED",   # Conservative: treat as dead for cannot-verify UX.
}


# ── Public builders ───────────────────────────────────────────────────────────

def build_cannot_verify_response(
    lq: Optional[LegalQuery],
    language: str = "en",
    *,
    dead_hits: Optional[List[dict]] = None,
) -> str:
    """Deterministic 'we cannot verify an active law for this' response.

    Format (per sprint brief §Layer M):
      ANSWER      : one honest sentence
      WHY         : plain reason (all retrieved laws are dead)
      WHAT YOU CAN DO: practical next steps
      VERIFIED SOURCES: list of dead sources with their status

    Kept short and factual — never invents a section number or claim.
    """
    subject = _subject_phrase(lq)
    dead_lines: list[str] = []
    for h in (dead_hits or [])[:5]:
        act = h.get("act_name") or h.get("short_label") or "This provision"
        sec = h.get("section_number")
        status = (h.get("status") or "SUPERSEDED").upper()
        successor = h.get("successor_act") or h.get("successor_act_id")
        line = f"- {act}"
        if sec:
            line += f", Section {sec}"
        line += f" — status: {status}"
        if successor:
            line += f" (replaced by {successor})"
        dead_lines.append(line)
    sources_block = "\n".join(dead_lines) if dead_lines else "- (No active statutory source located for this exact fact set.)"

    body = (
        f"ANSWER\n"
        f"I could not find an ACTIVE Indian law that clearly settles {subject} for the facts you gave.\n\n"
        f"WHY\n"
        f"The provisions our verified corpus surfaced for this question have been REPEALED or "
        f"SUPERSEDED by newer legislation (for example IPC → BNS from 1 July 2024). I will not "
        f"quote a dead law as if it were still in force.\n\n"
        f"WHAT YOU CAN DO\n"
        f"- Rephrase with the event date, state, and the exact action taken — that often unlocks a "
        f"matching current statute.\n"
        f"- Consult a licensed advocate for the current position, especially if the incident is "
        f"post-July 2024 (BNS / BNSS / BSA era).\n"
        f"- If this is urgent, dial 112; women in distress can dial 1091.\n\n"
        f"VERIFIED SOURCES (status shown transparently)\n"
        f"{sources_block}\n\n"
        f"⚠️ Legal information, not legal advice. Consult an advocate. © Callistus Moses · MSafe Solutions."
    )
    # If the user's language is not English, keep the English fallback but tag
    # it so an upstream translator (langpolicy.repair_prompt) can convert if
    # needed. This is safer than emitting broken machine translation here.
    if language and language.lower() != "en":
        return body + f"\n\n[lang_hint:{language}]"
    return body


def augment_prompt_with_status_guard(prompt: str, hits: Iterable[dict]) -> str:
    """Append a plain-language instruction reminding the LLM to flag dead laws.

    Only appends the instruction when at least one hit is dead — otherwise
    the prompt stays untouched (no wasted tokens).
    """
    dead = [h for h in (hits or []) if _is_dead(h)]
    if not dead:
        return prompt
    names = []
    for h in dead[:3]:
        act = h.get("act_name") or h.get("short_label") or "a cited provision"
        sec = h.get("section_number")
        names.append(f"{act}" + (f" §{sec}" if sec else ""))
    guard = (
        "\n\nSTATUS-GUARD NOTICE (Layer S):\n"
        f"The corpus flagged these as dead/superseded: {', '.join(names)}. "
        "In your reply, do NOT describe these as if they were currently enforceable. "
        "If the question is answered by the successor law (e.g. BNS in place of IPC), "
        "answer using the CITIZEN-LEVEL description of the successor rule; if no "
        "successor is available in the VERIFIED SOURCES, tell the user plainly that "
        "the older law no longer applies and ask them to consult an advocate."
    )
    return prompt + guard


# ── Post-processor ────────────────────────────────────────────────────────────

_LEAK_SECTION = re.compile(
    r"\b(BNS|BNSS|BSA|IPC|CrPC|PWDVA|POSH|RTI|MV|MVA|DPDP)\s*(?:Section|Sec\.?)?\s*\d+[A-Za-z]?(?:\(\d+\))?",
    re.IGNORECASE,
)
_LEAK_ARTICLE = re.compile(r"\bArticle\s+\d+[A-Za-z]?\b", re.IGNORECASE)


def strip_leaked_citations(text: str) -> str:
    """Belt-and-braces guard — removes leaked 'Section 43' / 'Article 21' strings
    from the LLM reply. Paired with corpus.sanitize_model_output so a regex
    miss on one side is caught by the other.

    Intentionally conservative: only strips the identifier itself, leaving
    surrounding grammar intact. If the reply reads oddly after stripping, the
    citation chips shown separately in the UI still convey the exact rule.
    """
    if not text:
        return text
    text = _LEAK_SECTION.sub("the law", text)
    text = _LEAK_ARTICLE.sub("the constitutional right", text)
    # Collapse doubled spaces / punctuation left by the substitution.
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text


# ── Helpers ───────────────────────────────────────────────────────────────────

def _subject_phrase(lq: Optional[LegalQuery]) -> str:
    """Short human phrase for the ANSWER line — never invents facts."""
    if not lq:
        return "your question"
    actions = [a for a in (lq.actions or []) if a] or []
    issues = [i for i in (lq.candidate_issues or []) if i] or []
    if actions and issues:
        return f"'{actions[0]} → {issues[0]}'"
    if issues:
        return f"'{issues[0]}'"
    if actions:
        return f"'{actions[0]}'"
    if lq.normalized_query:
        return f"'{lq.normalized_query[:80]}'"
    return "your question"


def _is_dead(h: dict) -> bool:
    if not h:
        return False
    if h.get("is_dead_law"):
        return True
    if (h.get("status") or "").upper() in _DEAD_STATUSES:
        return True
    if (h.get("dead_warning") or "").strip():
        return True
    return False
