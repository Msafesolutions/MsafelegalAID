"""
P0 Verification Script — runs through the same CORPUS_DB_NAME connection that
server.py uses, calling corpus_db.py functions directly.

Usage: python3 verify_p0.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from motor.motor_asyncio import AsyncIOMotorClient
from corpus_db import retrieve_db, lookup_section, check_query_for_orphan_warnings

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
CORPUS_DB_NAME = os.environ.get("CORPUS_DB_NAME", "dhara")

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]           # operational DB (users, sessions…)
    corpus_db = client[CORPUS_DB_NAME]  # corpus DB — same as server.py

    print("=" * 60)
    print(f"Operational DB : {DB_NAME}")
    print(f"Corpus DB      : {CORPUS_DB_NAME}")
    print("=" * 60)

    # ── 1. Five-count check through corpus_db's own connection ───────────────
    print("\n── FIVE-COUNT CHECK (via corpus_db connection) ──")
    counts = {
        "legal_sections":        await corpus_db.legal_sections.count_documents({}),
        "acts":                  await corpus_db.acts.count_documents({}),
        "judicial_invalidations": await corpus_db.judicial_invalidations.count_documents({}),
        "review_queue":          await corpus_db.review_queue.count_documents({}),
    }
    # Distinct jurisdictions
    jurisdictions = await corpus_db.legal_sections.distinct("jurisdiction")
    counts["distinct_jurisdictions"] = len(jurisdictions)

    expected = {
        "legal_sections": 70397,
        "acts": 2120,
        "judicial_invalidations": 16,
        "review_queue": 650,
        "distinct_jurisdictions": 13,
    }
    all_pass = True
    for key, got in counts.items():
        exp = expected[key]
        status = "✅" if got == exp else "❌"
        if got != exp:
            all_pass = False
        print(f"  {status}  {key:30s} got={got:6d}  expect={exp}")
    print(f"\n  Jurisdictions: {sorted(jurisdictions)}")
    print(f"\n  {'ALL COUNTS PASS ✅' if all_pass else 'SOME COUNTS FAILED ❌'}")

    # ── 2. §66A retrieval via corpus_db.retrieve_db ────────────────────────
    print("\n── §66A RETRIEVAL via retrieve_db() ──")
    hits_66a = await retrieve_db(corpus_db, "What is IT Act section 66A", limit=3)
    if hits_66a:
        h = hits_66a[0]
        print(f"  Found {len(hits_66a)} hit(s)")
        print(f"  act_name:     {h.get('act_name')}")
        print(f"  section_num:  {h.get('section_number')}")
        print(f"  is_dead_law:  {h.get('is_dead_law')}")
        print(f"  dead_warning: {h.get('dead_warning')}")
        print(f"  judicial_flag:{h.get('judicial_flag')}")
        print(f"  section_text (first 100): {str(h.get('section_text',''))[:100]}")
        print()
        # Guard check: warning MUST appear before statutory text
        dw = h.get("dead_warning") or ""
        jf = h.get("judicial_flag") or ""
        st = h.get("section_text") or ""
        if (dw or jf) and st:
            print("  ✅ Safety warnings present AND statutory text present")
            print("     Warnings will be prepended to official_text in SSE frames.")
        elif (dw or jf) and not st:
            print("  ⚠️  Warnings present but no section_text — unexpected for §66A")
        else:
            print("  ❌ NO safety warnings — guards not firing")
    else:
        print("  ❌ No hits for §66A — corpus_db retrieval broken")

    # ── 3. §66A via lookup_section (exact path) ───────────────────────────
    print("\n── §66A via lookup_section('66A', 'Information Technology') ──")
    exact_66a = await lookup_section(corpus_db, "66A", "Information Technology")
    if exact_66a:
        print(f"  ✅ lookup_section returned a result")
        print(f"  dead_warning: {exact_66a.get('dead_warning')}")
        print(f"  judicial_flag:{exact_66a.get('judicial_flag')}")
        print(f"  is_dead_law:  {exact_66a.get('is_dead_law')}")
        print(f"  no_current_text: {exact_66a.get('no_current_text', False)}")
    else:
        print("  ❌ lookup_section returned None")

    # ── 4. §377 via lookup_section (JI-decoupling test) ───────────────────
    print("\n── §377 via lookup_section('377', 'Indian Penal Code') [JI DECOUPLE TEST] ──")
    exact_377 = await lookup_section(corpus_db, "377", "Indian Penal Code")
    if exact_377:
        print(f"  ✅ lookup_section returned a result (IPC §377 has JI entry)")
        print(f"  no_current_text: {exact_377.get('no_current_text', False)}")
        print(f"  judicial_flag:   {exact_377.get('judicial_flag')}")
        print(f"  section_text:    {exact_377.get('section_text')}")
        if exact_377.get("no_current_text"):
            print("  ✅ no_current_text=True — will add 'text not available' note")
    else:
        print("  ❌ lookup_section returned None — JI decouple fix NOT working")

    # ── 5. Orphan check for 'IPC section 377' ─────────────────────────────
    print("\n── Orphan check for 'IPC section 377' ──")
    orphan = await check_query_for_orphan_warnings(corpus_db, "IPC section 377")
    if orphan:
        print(f"  ✅ Orphan check found: status={orphan.get('status')}")
        print(f"  user_warning: {orphan.get('user_warning')}")
    else:
        print("  (No orphan — expected since lookup_section now handles it directly)")

    client.close()
    print("\n══ Verification complete ══")

if __name__ == "__main__":
    sys.path.insert(0, '/app/backend')
    asyncio.run(main())
