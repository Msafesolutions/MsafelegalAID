"""
retrieval_logic.py — Shared retrieval scoring + corroboration primitives.

Single source of truth for DHARA's retrieval math, extracted so it is defined
ONCE and imported by both retrieval backends:

  • corpus.py    — in-memory hand-verified keyword corpus (token/IDF scorer).
  • corpus_db.py — MongoDB $text full-text corpus (significant-word corroboration).

The "≥ 2 significant-word corroboration" rule (MIN_COROBORATION_WORDS) is the
core anti-noise gate both paths rely on: a fuzzy text/keyword hit must prove
real topical overlap (an explicit Act-label match, OR at least two significant
words in common) before it is trusted.

Two corpora → two stopword vocabularies, both defined here:
  • BASE_STOPWORDS — function words + meta-legislation words, for the keyword
                     corpus token scorer.
  • SIG_STOPWORDS  — the wider set that ALSO strips legal-boilerplate machinery
                     ("fine", "penalty", "shall"...), for the MongoDB corpus.

SAFETY-GUARD NOTE
-----------------
This module contains NO safety-guard logic. The is_dead_law guard (G1) and the
judicial_invalidations join (G2) live — unchanged — in corpus_db.py. Nothing
here removes, bypasses, or alters their trigger conditions.
"""

from __future__ import annotations

import re

# ── Shared corroboration threshold ────────────────────────────────────────────
# A fuzzy hit needs at least this many significant words in common with the
# query (unless the query names the Act by label) to count as corroborated.
MIN_COROBORATION_WORDS = 2

# Keyword-corpus confidence floor (corpus.py). A single moderately-common token
# (weight 3) matching is not enough evidence on its own.
RETRIEVAL_MIN_SCORE = 4


# ── Tokenization (keyword corpus) ─────────────────────────────────────────────
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def _tokens(s: str) -> set:
    """Split a normalized string into a set of tokens (words)."""
    return {t for t in _norm(s).split() if len(t) > 1}


# ── Stopwords: keyword-corpus vocabulary (corpus.py) ──────────────────────────
# Words too common to give retrieval signal (would over-match). Includes
# meta-legislation words ("act", "section", "code"...) which appear in nearly
# every real query yet, being rare in the hand-written keyword lists, would
# otherwise score as high-weight tokens (poor-man's-IDF inverting itself).
BASE_STOPWORDS: set = {
    "the", "a", "an", "is", "are", "was", "were", "of", "and", "or", "for",
    "in", "on", "at", "to", "by", "my", "me", "i", "we", "you", "your",
    "can", "may", "do", "does", "did", "have", "has", "had", "be", "been",
    "will", "would", "should", "could", "shall", "any", "all", "some",
    "what", "why", "how", "when", "where", "who", "which", "this", "that",
    "without", "with", "not", "no", "from", "than", "then", "into", "about",
    "if", "as", "but", "so", "there", "their", "them", "his", "her", "its",
    "am", "get", "got", "make", "made", "tell", "know", "want", "need",
    "please", "sir", "madam", "hai", "kya", "mera", "meri",
    "act", "acts", "section", "sections", "rule", "rules", "code", "codes",
    "law", "laws", "sanhita", "adhiniyam", "under",
}

# ── Stopwords: MongoDB significant-word vocabulary (corpus_db.py) ──────────────
# Adds legal-boilerplate machinery words on top of the function words. These
# appear in the vast majority of Bare Act sections regardless of subject matter
# ("fine", "penalty", "shall", "rupees", "manner as prescribed"...) so two
# documents sharing ONLY these words are not actually on the same topic.
SIG_STOPWORDS: set = {
    "the", "a", "an", "is", "are", "was", "were", "of", "and", "or", "for",
    "in", "on", "at", "to", "by", "my", "me", "i", "we", "you", "your",
    "can", "may", "do", "does", "did", "have", "has", "had", "be", "been",
    "will", "would", "should", "could", "shall", "any", "all", "some",
    "what", "why", "how", "when", "where", "who", "which", "this", "that",
    "without", "with", "not", "no", "from", "than", "then", "into", "about",
    "if", "as", "but", "so", "there", "their", "them", "his", "her", "its",
    "am", "get", "got", "make", "made", "tell", "know", "want", "need",
    "please", "sir", "madam", "against", "per", "under",
    "act", "acts", "section", "sections", "rule", "rules", "code", "codes",
    "law", "laws", "sanhita", "adhiniyam",
    # Legal-boilerplate machinery words — appear across the vast majority of
    # Bare Act sections regardless of subject matter.
    "fine", "fines", "penalty", "penalties", "punishment", "punishable",
    "imprisonment", "extend", "extending", "extended", "liable", "liability",
    "rupees", "amount", "payment", "pay", "paid", "notice", "prescribed",
    "provided", "government", "authority", "officer", "officers", "court",
    "courts", "person", "persons", "such", "said", "aforesaid", "thereof",
    "herein", "thereto", "shall", "whoever", "confiscation", "lieu",
    "option", "compensation", "offence", "offences", "contravention",
    "contravenes", "regard", "respect", "matter", "matters", "case", "cases",
    "name", "names", "address", "addresses", "give", "giving", "given",
    "arrested", "arrest",
    # Generic time/manner connectors — near-zero topical signal on their own.
    "time", "times", "period", "periods", "date", "dates", "days", "month",
    "months", "year", "years", "limit", "limits", "manner", "necessary",
    "reasonable", "required", "specified", "concerned", "applicable",
    "otherwise", "accordance", "force", "forthwith", "immediately",
    # Structural/administrative headings repeated verbatim across thousands of
    # unrelated Acts ("Procedure on application", "Application of Act").
    "procedure", "procedures", "application", "applications", "provisions",
    "provision", "general", "particular", "purposes", "purpose",
}


# ── Keyword-corpus scoring (used by corpus.py) ────────────────────────────────
def build_token_df(items: list) -> dict:
    """Token document-frequency table (poor-man's IDF input). Counts, per token,
    how many corpus entries mention it across their keywords + short_label."""
    df: dict = {}
    for item in items:
        toks: set = set()
        for kw in item["keywords"]:
            toks |= _tokens(kw)
        toks |= _tokens(item["short_label"])
        for t in toks:
            df[t] = df.get(t, 0) + 1
    return df


def make_token_weight(token_df: dict):
    """Return a token-weight function bound to `token_df`. Rare tokens carry up
    to 4x the weight of tokens that appear across many entries."""
    def _token_weight(tok: str) -> int:
        n = token_df.get(tok, 1)
        if n <= 1:
            return 4      # unique to one section — very strong signal
        if n <= 3:
            return 3
        if n <= 6:
            return 2
        return 1          # appears everywhere — weak signal
    return _token_weight


def score_items(
    question: str,
    items: list,
    token_weight,
    stop: set = BASE_STOPWORDS,
) -> list[tuple[int, dict]]:
    """Score every item against the question. Returns ALL entries scoring > 0,
    sorted descending — WITHOUT any minimum-score cutoff.

    Score per entry:
      +12 if the entry's short_label appears in the question
      +6  per multi-word keyword appearing as a contiguous substring
      +   weighted token overlap (rare tokens 4 ... common tokens 1);
          bare numerals are skipped (a section number floating free of its Act
          context is weak evidence).
    """
    q_norm = _norm(question)
    if not q_norm:
        return []
    q_tokens = _tokens(question) - stop

    scored: list[tuple[int, dict]] = []
    for item in items:
        req = item.get("require_any")
        if req and not any(_norm(r) in q_norm for r in req):
            continue
        score = 0
        if _norm(item["short_label"]) in q_norm:
            score += 12
        kw_tokens: set = set()
        for kw in item["keywords"]:
            kw_norm = _norm(kw)
            if " " in kw_norm and kw_norm in q_norm:
                score += 6
            kw_tokens |= _tokens(kw)
        kw_tokens -= stop
        for t in kw_tokens & q_tokens:
            if t.isdigit():
                continue
            score += token_weight(t)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def corroborated(question: str, item: dict, stop: set = BASE_STOPWORDS) -> bool:
    """≥ 2 significant-word corroboration for the keyword corpus.

    PASS if EITHER
      (a) the entry's short_label appears in the question (a strong label
          match — e.g. "bnss 35", "article 21"), OR
      (b) the question shares >= MIN_COROBORATION_WORDS significant words with
          the entry's keyword tokens.
    """
    ql = question.lower()
    label = item.get("short_label", "").lower()
    if label in ql:
        return True
    kw_tokens = set().union(
        *[_tokens(kw) for kw in item.get("keywords", [])]
    ) - stop
    return len(set(_tokens(question)) & kw_tokens) >= MIN_COROBORATION_WORDS


# ── MongoDB significant-word corroboration (used by corpus_db.py) ─────────────
def significant_words(text: str, stopwords: set = SIG_STOPWORDS) -> set:
    """Lowercased alphabetic tokens (len>=3) minus stopwords — the real topical
    signal in a string, stripped of function words and generic legal-domain
    filler that would otherwise over-match everything."""
    words = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    return {w for w in words if w not in stopwords}


def _act_name_leads_with(doc_act_name: str, act_hint: str) -> bool:
    """True when `doc_act_name`, once its leading article is stripped, STARTS
    WITH `act_hint`.

    Was previously a bare substring check (`act_hint in doc_act_name`), which
    let "Information Technology" match "The INDIAN INSTITUTES OF Information
    Technology Act, 2014" — a completely unrelated Act about educational
    institutes that merely happens to contain those two words. That bug gave
    such docs a guaranteed corroboration_score of 9999 ("always surfaces,
    sorted first"), so a query about the real IT Act's §66A came back with
    two Indian Institutes of Information Technology Act sections outranking
    it. Real Act names always lead with their own proper name (at most after
    "The"/"An"/"A"), so anchoring to the start is a safe, general fix.
    """
    norm = (doc_act_name or "").lower().strip()
    for article in ("the ", "an ", "a "):
        if norm.startswith(article):
            norm = norm[len(article):]
            break
    return norm.startswith(act_hint.lower())


def corroboration_score(question_sig: set, doc: dict, act_hint: str | None) -> int:
    """Numeric corroboration score used to RE-RANK $text candidates.

    Returns 9999  → act-label match (doc's act_name LEADS WITH act_hint, i.e.
                     it IS that Act, not merely an Act whose longer name
                     happens to contain those words — see
                     `_act_name_leads_with`). Always surfaces; sorted first
                     regardless of text-index score.
    Returns N ≥ 0 → count of significant-word overlap between query and the
                     doc's act_name + section_heading + section_text[:800].

    Threshold for inclusion (applied by callers): score >= MIN_COROBORATION_WORDS.

    Why this beats raw textScore for ranking: MongoDB's textScore weights
    section_heading (×10) and act_name (×5) far above section_text (×1), so a
    section whose topic appears only in body text can fall outside a narrow
    candidate window entirely. Corroboration scoring looks at the full
    section_text so those sections bubble back up.
    """
    doc_act_name = doc.get("act_name") or ""
    if act_hint and _act_name_leads_with(doc_act_name, act_hint):
        return 9999  # Explicit act-label match → always surface
    doc_sig = significant_words(
        doc_act_name + " " + (doc.get("section_heading") or "") + " "
        + (doc.get("section_text") or "")[:800]
    )
    return len(question_sig & doc_sig)


def corroborates(question_sig: set, doc: dict, act_hint: str | None) -> bool:
    """Corroboration Rule gate — boolean version (kept for external callers)."""
    return corroboration_score(question_sig, doc, act_hint) >= MIN_COROBORATION_WORDS
