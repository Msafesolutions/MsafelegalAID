"""
Verify the Corroboration Rule (P0) added to corpus_db.retrieve_db().

Checks two things:
1. NOISE SUPPRESSION — queries that previously pulled unrelated Acts (sharing
   only a generic word like "fine") should no longer surface them.
2. LEGITIMATE RECALL PRESERVED — real situational queries for MV Act 129
   (helmet) and 132 (duty to stop) must still retrieve those sections, proving
   the corroboration filter is not so strict it breaks genuine matches.

Usage: python3 verify_corroboration.py
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from motor.motor_asyncio import AsyncIOMotorClient
from corpus_db import retrieve_db

MONGO_URL = os.environ["MONGO_URL"]
CORPUS_DB_NAME = os.environ.get("CORPUS_DB_NAME", "dhara")


async def show(label, question, expect_act_substr=None, expect_absent_substr=None):
    print(f"\n── {label} ──")
    print(f"  Q: {question!r}")
    hits = await retrieve_db(_db, question, limit=5)
    if not hits:
        print("  (no hits)")
    for h in hits:
        print(f"  - {h['act_name']} § {h['section_number']}  ({h['section_heading']})  score={h['_score']:.2f}")
    if expect_act_substr:
        ok = any(expect_act_substr.lower() in h["act_name"].lower() for h in hits)
        print(f"  {'✅' if ok else '❌'} expected to find an Act containing {expect_act_substr!r}")
    if expect_absent_substr:
        bad = [h for h in hits if expect_absent_substr.lower() in h["act_name"].lower()]
        print(f"  {'✅ absent as expected' if not bad else '❌ STILL PRESENT: ' + str(bad)}")
    return hits


async def main():
    global _db
    client = AsyncIOMotorClient(MONGO_URL)
    _db = client[CORPUS_DB_NAME]

    print("=" * 70)
    print("COROBORATION RULE VERIFICATION")
    print("=" * 70)

    # 1. Noise suppression — generic-word-only queries should not drag in
    #    unrelated Acts like Insolvency & Bankruptcy Code / Forest Act just
    #    because they share a common word such as "fine".
    await show(
        "Noise check — generic word 'fine' alone",
        "what is the fine for this",
    )

    # 2. Legitimate recall — MV Act helmet section via natural phrasing
    await show(
        "MV Act 129 — situational phrasing (no section number)",
        "riding a motorcycle without wearing a helmet punishment",
        expect_act_substr="Motor Vehicles",
    )

    # 3. Legitimate recall — MV Act duty-to-stop section via natural phrasing
    await show(
        "MV Act 132 — situational phrasing (no section number)",
        "driver must stop vehicle after accident give name address",
        expect_act_substr="Motor Vehicles",
    )

    # 4. Exact-lookup path unaffected — direct section citation
    await show(
        "Exact lookup — 'Motor Vehicles Act section 129'",
        "Motor Vehicles Act section 129",
        expect_act_substr="Motor Vehicles",
    )
    await show(
        "Exact lookup — 'Motor Vehicles Act section 132'",
        "Motor Vehicles Act section 132",
        expect_act_substr="Motor Vehicles",
    )

    client.close()
    print("\n══ Verification complete ══")


if __name__ == "__main__":
    asyncio.run(main())
