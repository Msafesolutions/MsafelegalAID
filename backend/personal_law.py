"""
Personal-law disambiguation — marriage/divorce/maintenance/custody and
inheritance/succession questions in India are governed by DIFFERENT Acts
depending on the parties' religion (or whether the marriage is civil /
inter-religious). Answering under the wrong one would be a WRONG CITATION —
the one thing this app must never do (see corpus.py's citation-integrity
rule).

This module operates on plain text only — no new SSE frame type, no
frontend changes. It reuses the EXISTING `early_refusal` mechanism already
wired in server.py's chat_stream (a canned message is streamed as a normal
chat bubble, the LLM/retrieval is skipped for that turn) — the same pattern
already used for REFUSAL_NO_CORPUS / REFUSAL_NON_INDIAN / REFUSAL_NOT_LEGAL.

Flow:
  1. classify_personal_law_topic() — is this question about marriage/family
     law, or succession/inheritance law, at all?
  2. detect_context() — did the question already name a religion / Act /
     marriage-type, so we already know which Act applies?
  3. If (1) is true and (2) finds nothing (and the chat session hasn't
     already resolved this topic earlier), chat_stream asks a plain-language
     clarifying question INSTEAD of guessing.
  4. Once a context is known — either from the original question or a
     session-remembered choice — act_hint_phrase() returns a short Act-name
     phrase that server.py silently appends to the retrieval text (never
     shown to the user), so the EXISTING `_ACT_HINTS` matcher in
     corpus_db.py biases retrieval toward the correct Act. No new retrieval
     machinery, no new database, no new SSE frame.

KNOWN SCOPE LIMITATION: the clarifying question text is English-only (it is
passed through `localize_refusal`, which falls back to English for any
string it does not recognise as one of the three built-in refusal
constants) — unlike REFUSAL_NO_CORPUS etc., it is not yet translated into
the other 21 languages.
"""
from __future__ import annotations

import re

# ── Topic detection ──────────────────────────────────────────────────────
_MARRIAGE_TOPIC_RE = re.compile(
    r"register\s+(?:my|our|the)?\s*marriage|marriage\s+registration|"
    r"\bdivorce\b|\balimony\b|maintenance\s+(?:after|from)\s+(?:my\s+)?(?:husband|wife|spouse)|"
    r"child\s+custody|judicial\s+separation|\bannul(?:ment|)\b|"
    r"grounds?\s+for\s+divorce|mutual\s+divorce|file\s+for\s+divorce|"
    r"dissolve\s+(?:my|our|the)?\s*marriage|marriage\s+certificate|"
    r"court\s+marriage|marry\s+(?:legally|officially)",
    re.I,
)
_SUCCESSION_TOPIC_RE = re.compile(
    r"\binheritance\b|\binherit\b|\binherits?\b|\bsuccession\b|ancestral\s+property|"
    r"legal\s+heir|property\s+after\s+(?:death|dying|he\s+dies|she\s+dies)|"
    r"\bwill\b.{0,20}\bproperty\b|intestate|coparcenary|"
    r"share\s+in\s+(?:my\s+)?father|who\s+gets?\s+the\s+property|division\s+of\s+property",
    re.I,
)

# ── Religion / marriage-type context detection ──────────────────────────
# Each context maps to a short Act-name phrase per topic. That phrase is
# what gets silently appended to the retrieval text — it must be a phrase
# the existing corpus_db._ACT_HINTS table already recognises.
_CONTEXTS: dict[str, dict] = {
    "hindu": {
        "pattern": re.compile(r"\bhindu\b|\bbuddhist\b|\bjain\b|\bsikh\b", re.I),
        "marriage_hint": "Hindu Marriage Act",
        "succession_hint": "Hindu Succession Act",
        "label": "Hindu, Buddhist, Jain or Sikh",
    },
    "special": {
        "pattern": re.compile(
            r"inter.?religious|inter.?caste|inter.?faith|civil\s+marriage|"
            r"court\s+marriage|special\s+marriage|different\s+religion",
            re.I,
        ),
        "marriage_hint": "Special Marriage Act",
        "succession_hint": None,  # civil/inter-religious marriage alone doesn't fix succession law
        "label": "inter-religious / civil / court marriage",
    },
    "muslim": {
        "pattern": re.compile(r"\bmuslim\b|\bislam(?:ic)?\b|\bnikah\b|\bshariat?\b|\bshariah\b", re.I),
        "marriage_hint": "Dissolution of Muslim Marriages Act",
        "succession_hint": "Muslim Personal Law",
        "label": "Muslim personal law",
    },
    "christian_parsi": {
        "pattern": re.compile(r"\bchristian\b|\bcatholic\b|\bparsi\b", re.I),
        "marriage_hint": "Indian Christian Marriage Act",
        "succession_hint": "Indian Succession Act",
        "label": "Christian or Parsi",
    },
}


def classify_personal_law_topic(question: str) -> str | None:
    """Returns 'marriage' or 'succession' if the question is about
    marriage/family law or inheritance/succession law, else None."""
    if _MARRIAGE_TOPIC_RE.search(question):
        return "marriage"
    if _SUCCESSION_TOPIC_RE.search(question):
        return "succession"
    return None


def detect_context(question: str) -> str | None:
    """Returns the context id already named in the question
    ('hindu' | 'special' | 'muslim' | 'christian_parsi'), else None."""
    for ctx_id, cfg in _CONTEXTS.items():
        if cfg["pattern"].search(question):
            return ctx_id
    return None


def act_hint_phrase(ctx_id: str | None, topic: str) -> str | None:
    """Short Act-name phrase to silently append to the retrieval text for
    this context + topic. None if this context doesn't determine the
    answer for this topic (e.g. 'special' + succession) or is unknown."""
    cfg = _CONTEXTS.get(ctx_id or "")
    if not cfg:
        return None
    return cfg.get(f"{topic}_hint")


def disambiguation_question(topic: str) -> str:
    """Plain-language clarifying question — no citations, no Act presumed —
    shown INSTEAD OF an answer when the topic is marriage/succession-related
    but no religion/marriage-type context is known yet."""
    if topic == "marriage":
        return (
            "Marriage, divorce and maintenance are governed by different laws "
            "depending on the couple's religion or how they married — the exact "
            "rule (and section) differs under each. To give you the correct one, "
            "could you tell me: are you Hindu, Buddhist, Jain or Sikh; did you "
            "marry (or want to marry) under a civil / inter-religious / court "
            "marriage; are you Muslim; or are you Christian or Parsi?"
        )
    return (
        "Inheritance and succession are governed by different laws depending "
        "on the deceased's religion — the exact rule differs under each. To "
        "give you the correct one, could you tell me: was the person Hindu, "
        "Buddhist, Jain or Sikh; Muslim; or Christian or Parsi?"
    )


def act_disclaimer(ctx_id: str | None, topic: str) -> str:
    """Short note appended after an answer once a context is known, so the
    user always sees which law was applied and that a different situation
    needs a different law."""
    label = _CONTEXTS.get(ctx_id or "", {}).get("label", "your situation")
    return (
        f"(This answer is based on {label} personal law. If your situation is "
        "different, the applicable law — and section — will differ.)"
    )
