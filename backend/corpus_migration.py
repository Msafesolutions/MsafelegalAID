"""
Idempotent startup corpus migration.

WHY THIS EXISTS: production's Atlas database has never had the legal corpus
loaded into it (per Support's diagnosis) — this codebase's dev/preview
sandbox has its own local-only MongoDB, and a freshly deployed production
backend has no way to reach that local database. So the corpus data itself
is bundled INTO the repo (corpus_seed/*.jsonl.gz, exported from the sandbox's
`dhara` database) and this module loads it into whatever database
CORPUS_DB_NAME resolves to, automatically, the first time the app boots
against an empty database.

WHEN IT RUNS: kicked off from server.py's FastAPI startup event as a
background asyncio task — see run_corpus_migration() being wrapped in
asyncio.create_task(...), not awaited directly. That means:
  - It starts automatically the instant the process boots. No manual
    endpoint call, no separate script to run.
  - It does NOT block the app from serving requests / passing platform
    health checks while it inserts tens of thousands of documents.

IDEMPOTENCY: per-collection, not a single all-or-nothing flag. Before
touching a collection, its current document COUNT in the target database is
checked — if it's already > 0, that collection is skipped entirely (assumed
already migrated, from this run or an earlier one). This means:
  - Every restart/redeploy after the first successful run is a fast no-op
    (four count() calls, nothing else).
  - If the process crashes partway through (e.g. after seeding
    legal_sections but before acts), the NEXT boot resumes by seeding only
    the collections still at 0 — no duplicate inserts, no data loss.

OBSERVABILITY: every step is logged through the standard `logging` module
with a "[CORPUS_MIGRATION]" prefix, so `grep CORPUS_MIGRATION` finds it in
whatever log viewer the deploy platform provides. A best-effort status
document is also upserted into `_migration_status` (db-internal, never
exposed over any API) purely so a human with direct DB/log access has a
timestamped record — it is NOT required for the idempotency check itself,
which relies only on collection counts.
"""
import gzip
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from bson import json_util

logger = logging.getLogger("corpus_migration")

SEED_DIR = Path(__file__).parent / "corpus_seed"
COLLECTIONS = ["legal_sections", "acts", "judicial_invalidations", "review_queue"]
BATCH_SIZE = 1000


async def _seed_collection(db, name: str) -> dict:
    coll = db[name]
    try:
        existing = await coll.estimated_document_count()
    except Exception as e:
        logger.error(f"[CORPUS_MIGRATION] {name}: could not read count — {type(e).__name__}: {e}")
        return {"collection": name, "action": "error", "error": f"count check failed: {type(e).__name__}"}

    if existing > 0:
        logger.info(f"[CORPUS_MIGRATION] {name}: already has {existing} docs — skipping (idempotent no-op).")
        return {"collection": name, "action": "skipped", "existing": existing}

    seed_path = SEED_DIR / f"{name}.jsonl.gz"
    if not seed_path.exists():
        logger.error(f"[CORPUS_MIGRATION] {name}: seed file missing at {seed_path} — cannot seed.")
        return {"collection": name, "action": "error", "error": "seed file missing"}

    t0 = time.monotonic()
    inserted = 0
    batch = []
    try:
        with gzip.open(seed_path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                batch.append(json_util.loads(line))
                if len(batch) >= BATCH_SIZE:
                    await coll.insert_many(batch, ordered=False)
                    inserted += len(batch)
                    batch = []
        if batch:
            await coll.insert_many(batch, ordered=False)
            inserted += len(batch)
    except Exception as e:
        logger.error(
            f"[CORPUS_MIGRATION] {name}: FAILED after inserting {inserted} docs "
            f"— {type(e).__name__}: {e}"
        )
        return {
            "collection": name, "action": "error",
            "error": f"{type(e).__name__}: {e}", "inserted_before_failure": inserted,
        }

    elapsed = round(time.monotonic() - t0, 1)
    logger.info(f"[CORPUS_MIGRATION] {name}: seeded {inserted} docs in {elapsed}s.")
    return {"collection": name, "action": "seeded", "inserted": inserted, "elapsed_s": elapsed}


async def _ensure_indexes(db) -> dict:
    """Idempotently (re)create the indexes retrieval depends on.

    WHY THIS EXISTS: a plain document copy (mongodump/restore or a raw
    insert_many seed, as _seed_collection does above) carries NO index
    definitions with it — MongoDB indexes are a property of the collection
    on the destination server, not of the documents. `corpus_db.py`'s
    situational search (`retrieve_db`) runs a `$text` query against
    `legal_sections`; without a text index that query doesn't return zero
    rows, it *throws* `OperationFailure: text index required for $text
    query` — which every call site there wraps in `except Exception: pass`,
    so the failure is silent and looks exactly like "no verified source
    exists" to the end user. Any future restore of this corpus into a new
    database (Atlas migration, disaster recovery, a fresh preview DB) would
    reproduce the exact same silent outage unless index creation is part of
    the same idempotent startup path as the data itself.

    `create_index(...)` is a no-op (fast, checks existing definition) when
    the same index already exists, so this is safe to call on every boot —
    not just the first one — unlike `_seed_collection`'s count-gated skip.
    """
    results: dict = {}
    try:
        await db.legal_sections.create_index(
            [("section_heading", "text"), ("act_name", "text"), ("section_text", "text")],
            weights={"section_heading": 10, "act_name": 5, "section_text": 1},
            name="legal_sections_text_idx",
            default_language="english",
        )
        await db.legal_sections.create_index(
            [("section_number", 1), ("act_name", 1)], name="section_act_idx"
        )
        await db.legal_sections.create_index(
            [("act_id", 1), ("section_num_int", 1)], name="act_sections_idx"
        )
        await db.legal_sections.create_index(
            [("jurisdiction", 1), ("is_dead_law", 1)], name="jurisdiction_dead_idx"
        )
        await db.judicial_invalidations.create_index(
            [("act_name", 1), ("section_number", 1)], name="ji_act_section_idx"
        )
        results["action"] = "ensured"
        logger.info("[CORPUS_MIGRATION] Indexes ensured on legal_sections + judicial_invalidations.")
    except Exception as e:
        results["action"] = "error"
        results["error"] = f"{type(e).__name__}: {e}"
        logger.error(f"[CORPUS_MIGRATION] Index creation FAILED — {type(e).__name__}: {e}")
    return results


async def run_corpus_migration(db, corpus_db_name: str) -> list:
    """Entry point. Called once at startup as a background task (see server.py)."""
    logger.info(f"[CORPUS_MIGRATION] Starting. Target database: '{corpus_db_name}'.")
    t0 = time.monotonic()
    results = []
    for name in COLLECTIONS:
        try:
            results.append(await _seed_collection(db, name))
        except Exception as e:
            logger.error(f"[CORPUS_MIGRATION] {name}: unexpected top-level error — {type(e).__name__}: {e}")
            results.append({"collection": name, "action": "error", "error": f"{type(e).__name__}: {e}"})

    index_result = await _ensure_indexes(db)
    results.append({"collection": "_indexes", **index_result})

    elapsed = round(time.monotonic() - t0, 1)
    seeded = [r["collection"] for r in results if r.get("action") == "seeded"]
    errors = [r for r in results if r.get("action") == "error"]
    if errors:
        logger.error(f"[CORPUS_MIGRATION] COMPLETED WITH ERRORS in {elapsed}s. Full results: {results}")
    elif seeded:
        logger.info(f"[CORPUS_MIGRATION] COMPLETED in {elapsed}s — seeded: {seeded}.")
    else:
        logger.info(f"[CORPUS_MIGRATION] COMPLETED in {elapsed}s — nothing to do, all 4 collections already populated.")

    try:
        await db["_migration_status"].update_one(
            {"_id": "corpus_seed_v1"},
            {"$set": {
                "last_run_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_s": elapsed,
                "results": results,
            }},
            upsert=True,
        )
    except Exception as e:
        # Non-fatal — the log lines above are the source of truth.
        logger.error(f"[CORPUS_MIGRATION] Could not write status doc — {type(e).__name__}: {e}")

    return results
