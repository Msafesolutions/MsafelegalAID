"""
migrate_users.py — One-time migration for DHARA user collection.

What this does:
  1. is_grandfathered = True  → set for every user that is missing the field.
  2. is_pro = False           → set for every user that is missing the field.
  3. state_jurisdiction       → derive from existing `state` code using
                                STATE_CODE_TO_JURISDICTION.  Only sets the field
                                if it is not already present and `state` is known.

Run:
    python3 migrate_users.py

Safe to re-run — uses $set only on missing fields, never overwrites existing values.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME   = os.environ.get("DB_NAME", "dhara")

# Must match corpus_db.STATE_CODE_TO_JURISDICTION exactly.
STATE_CODE_TO_JURISDICTION = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DH": "Dadra and Nagar Haveli and Daman and Diu",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TG": "Telangana",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
}


async def run():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    users = db.users

    total = await users.count_documents({})
    print(f"Total users in DB: {total}")

    if total == 0:
        print("No users to migrate — schema is ready for new registrations.")
        client.close()
        return

    # ── 1. Set is_grandfathered = True where missing ──────────────────────────
    r1 = await users.update_many(
        {"is_grandfathered": {"$exists": False}},
        {"$set": {"is_grandfathered": True}},
    )
    print(f"is_grandfathered set to True:    {r1.modified_count} users updated")

    # ── 2. Set is_pro = False where missing ───────────────────────────────────
    r2 = await users.update_many(
        {"is_pro": {"$exists": False}},
        {"$set": {"is_pro": False}},
    )
    print(f"is_pro set to False:             {r2.modified_count} users updated")

    # ── 3. Set state_jurisdiction from state code where missing ───────────────
    updated_jurisdiction = 0
    async for user in users.find(
        {"state_jurisdiction": {"$exists": False}, "state": {"$exists": True, "$ne": None, "$ne": ""}},
        {"id": 1, "state": 1},
    ):
        code = (user.get("state") or "").upper()
        jurisdiction = STATE_CODE_TO_JURISDICTION.get(code, "")
        if jurisdiction:
            await users.update_one(
                {"id": user["id"]},
                {"$set": {"state_jurisdiction": jurisdiction}},
            )
            updated_jurisdiction += 1

    # For users with no state set, store empty string so field always exists
    r3 = await users.update_many(
        {"state_jurisdiction": {"$exists": False}},
        {"$set": {"state_jurisdiction": ""}},
    )
    print(f"state_jurisdiction set from code:{updated_jurisdiction} users")
    print(f"state_jurisdiction set to '':    {r3.modified_count} users (no state on profile)")

    # ── 4. Verify ─────────────────────────────────────────────────────────────
    gf_count    = await users.count_documents({"is_grandfathered": True})
    pro_count   = await users.count_documents({"is_pro": True})
    no_jur      = await users.count_documents({"state_jurisdiction": {"$exists": False}})

    print("")
    print("=== Post-migration verification ===")
    print(f"Total users:                     {total}")
    print(f"is_grandfathered=True:           {gf_count}")
    print(f"is_pro=True:                     {pro_count}")
    print(f"state_jurisdiction missing:      {no_jur}  (expect 0)")
    print("")
    if no_jur == 0:
        print("✅ Migration complete — schema ready for data upload.")
    else:
        print("⚠️  Some documents still missing state_jurisdiction. Re-run to fix.")

    client.close()


if __name__ == "__main__":
    asyncio.run(run())
