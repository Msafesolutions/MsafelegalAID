"""
Unification-build verification (guards preserved after refactor).

Reproduces server.py's EXACT corpus_context assembly (dead-law + judicial
warnings prepended BEFORE statutory text) for the two required queries and
prints the literal output.

  1. §66A IT Act        → "Struck down" warning must precede any statutory text.
  2. IPC §377 (or BNS   → judicial_invalidations warning must fire before any
     marital rape excn.)   statutory text.

Usage: python3 verify_unification.py
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from motor.motor_asyncio import AsyncIOMotorClient
from corpus_db import retrieve_db, check_query_for_orphan_warnings

MONGO_URL = os.environ["MONGO_URL"]
CORPUS_DB_NAME = os.environ.get("CORPUS_DB_NAME", "dhara")


def build_block(db_hits, db_orphan):
    """Verbatim copy of server.py lines 894-932: warnings BEFORE text."""
    corpus_context = ""
    if db_hits:
        db_parts = []
        for hit in db_hits:
            lines = []
            if hit.get("dead_warning"):
                lines.append(f"SAFETY WARNING (DEAD LAW): {hit['dead_warning']}")
            if hit.get("judicial_flag"):
                lines.append(f"JUDICIAL ALERT: {hit['judicial_flag']}")
            sec_heading = hit.get("section_heading", "")
            act_label = f"{hit.get('act_name', '')}, Section {hit.get('section_number', '')}"
            if sec_heading:
                act_label += f" — {sec_heading}"
            lines.append(f"Source: {act_label}")
            if hit.get("no_current_text"):
                lines.append(
                    "NOTE: Current statutory text for this section is not available "
                    "in the corpus — the act may have been repealed or replaced."
                )
            else:
                sec_text = (hit.get("section_text") or "")[:600]
                if sec_text:
                    lines.append(f"Text: {sec_text}")
            db_parts.append("\n".join(lines))
        corpus_context = "\n---\n".join(db_parts)

    if db_orphan:
        orphan_line = (
            f"JUDICIAL ALERT [{db_orphan.get('status', '')}]: {db_orphan.get('user_warning', '')}\n"
            f"Note: '{db_orphan.get('act_name', '')}' may no longer be in force in its original form."
        )
        corpus_context = (corpus_context + "\n---\n" + orphan_line) if corpus_context else orphan_line
    return corpus_context


async def run(db, label, question):
    print("=" * 72)
    print(f"{label}")
    print(f"Query: {question!r}")
    print("-" * 72)
    db_hits = await retrieve_db(db, question, limit=3)
    db_orphan = None
    if not db_hits:
        db_orphan = await check_query_for_orphan_warnings(db, question)
    block = build_block(db_hits, db_orphan)
    print(block if block else "(no verified source found)")
    print("-" * 72)

    # Ordering assertion: first warning index must precede first text/source.
    lower = block.lower()
    warn_markers = [m for m in ("struck down", "safety warning", "judicial alert") if m in lower]
    warn_pos = min((lower.find(m) for m in warn_markers), default=-1)
    text_pos = lower.find("text:")
    if warn_pos == -1:
        print("RESULT: no warning present")
    elif text_pos == -1:
        print(f"RESULT: warning present, no statutory text served (warning at char {warn_pos})")
    else:
        ok = warn_pos < text_pos
        print(f"RESULT: warning@{warn_pos} {'BEFORE' if ok else 'AFTER'} text@{text_pos} → {'PASS' if ok else 'FAIL'}")
    print()


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[CORPUS_DB_NAME]
    await run(db, "VERIFICATION 1 — §66A IT Act (Shreya Singhal, struck down)",
              "Information Technology Act section 66A")
    await run(db, "VERIFICATION 2 — IPC §377 (judicial invalidation)",
              "IPC section 377")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
