"""
Account deletion — hard-delete a user and every collection that carries a
user_id, in one place so both the in-app path (POST /api/account/delete)
and the public web OTP path (POST /api/account-deletion/verify) call the
exact same logic and can never drift apart.

Scope verified by a full `list_collection_names()` scan of the database
(June 2026): collections WITHOUT a user_id field — refusal_events (aggregate
refusal analytics, deliberately not user-linked, by design a privacy
feature — logs what got refused without recording who asked) and
push_job_runs (job/day bookkeeping only) — are NOT touched here; there is
nothing to delete from them per-user.

usage_daily carries BOTH per-user rows (scope:"user") and app-wide aggregate
rows (scope:"app"); only the former belong to an individual account and are
deleted — the aggregate rows belong to no one and must survive.
"""
import logging

logger = logging.getLogger("account_deletion")

# Collections matched by a plain {"user_id": <id>} filter.
_SIMPLE_USER_ID_COLLECTIONS = [
    "sessions",
    "messages",
    "bookmarks",
    "draft_events",
    "password_resets",
    "terms_acknowledgements",
    "client_error_logs",
    "billing_intents",
]


async def hard_delete_user(db, user_id: str) -> dict:
    """Deletes the user's own account record plus every row across every
    other user-linked collection. Returns a {collection: deleted_count} map
    for verification/audit logging by the caller — never sent to the client.
    """
    counts: dict[str, int] = {}

    for name in _SIMPLE_USER_ID_COLLECTIONS:
        result = await db[name].delete_many({"user_id": user_id})
        counts[name] = result.deleted_count

    # usage_daily — only the per-user rows, never the app-wide aggregate rows.
    usage_result = await db.usage_daily.delete_many({"user_id": user_id, "scope": "user"})
    counts["usage_daily"] = usage_result.deleted_count

    # users — the account record itself, matched by its own "id" field
    # (this codebase's primary key everywhere, not Mongo's _id).
    user_result = await db.users.delete_one({"id": user_id})
    counts["users"] = user_result.deleted_count

    logger.info(f"[account_deletion] hard-deleted user {user_id}: {counts}")
    return counts
