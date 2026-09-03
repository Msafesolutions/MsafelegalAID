"""
Branch 1 — LIVE production guard check (Path A: run in the DEPLOYMENT shell).

Self-contained. Uses the SAME throwaway-token pattern proven in preview:
  seed throwaway user -> mint 1-hour token -> run §66A + §377 against the live
  /api/retrieve -> DELETE the throwaway user -> re-hit with the same token and
  confirm it now returns 401 (explicit revocation, not "cleaned up").

Reads production secrets from the environment it runs in (never leaves the pod):
  MONGO_URL, JWT_SECRET  (required)   DB_NAME (default 'gandhikar_db')
Target defaults to the co-located backend; override with --base-url if needed:
  python3 verify_prod_guards_selfcontained.py
  python3 verify_prod_guards_selfcontained.py --base-url http://localhost:8001
"""
import argparse, json, os, sys, uuid, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

import jwt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('/app/backend/.env')

BASE = None  # set in main()


def retrieve(token, body):
    req = urllib.request.Request(BASE.rstrip("/") + "/api/retrieve",
                                 data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")}


def check_66a(token):
    print("=" * 72); print("VERIFICATION 1 — §66A IT Act (struck down) — LIVE")
    st, p = retrieve(token, {"query": "Information Technology Act section 66A",
                             "mode": "exact", "section_number": "66A",
                             "act_hint": "Information Technology"})
    print(f"HTTP {st}"); print(json.dumps(p, indent=2, ensure_ascii=False))
    r = (p.get("results") or [None])[0]
    if not r:
        print("RESULT: FAIL — no result for §66A"); return False
    jflag = (r.get("judicial_flag") or "").lower()
    ok = bool(r.get("is_dead_law")) and bool(r.get("dead_warning")) and ("struck down" in jflag)
    print(f"RESULT: is_dead_law={bool(r.get('is_dead_law'))} | "
          f"dead_warning={'present' if r.get('dead_warning') else 'MISSING'} | "
          f"'struck down' in judicial_flag={'yes' if 'struck down' in jflag else 'NO'} "
          f"→ {'PASS' if ok else 'FAIL'}")
    return ok


def check_377(token):
    print("=" * 72); print("VERIFICATION 2 — IPC §377 (judicial invalidation) — LIVE")
    st, p = retrieve(token, {"query": "Indian Penal Code section 377",
                             "mode": "exact", "section_number": "377",
                             "act_hint": "Indian Penal Code"})
    print(f"HTTP {st}"); print(json.dumps(p, indent=2, ensure_ascii=False))
    r = (p.get("results") or [None])[0]
    if not r:
        print("RESULT: FAIL — no result for §377"); return False
    ok = bool(r.get("judicial_flag")) and bool(r.get("no_current_text")) and not r.get("section_text")
    print(f"RESULT: judicial_flag={'present' if r.get('judicial_flag') else 'MISSING'} | "
          f"no_current_text={bool(r.get('no_current_text'))} | "
          f"section_text={'(none)' if not r.get('section_text') else 'FABRICATED?!'} "
          f"→ {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("DHARA_PROD_URL", "http://localhost:8001"))
    BASE = ap.parse_args().base_url
    secret = os.environ.get("JWT_SECRET")
    mongo = os.environ.get("MONGO_URL")
    dbname = os.environ.get("DB_NAME", "gandhikar_db")
    if not secret or not mongo:
        print("ERROR: JWT_SECRET and MONGO_URL must be present in the environment."); sys.exit(2)

    uid = "guardcheck-throwaway-" + uuid.uuid4().hex[:12]
    client = MongoClient(mongo)
    users = client[dbname].users
    print(f"Target: {BASE.rstrip('/')}/api/retrieve")
    print(f"Throwaway user id: {uid}  (DB: {dbname})\n")

    p1 = p2 = False
    token = jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                       secret, algorithm="HS256")
    try:
        users.update_one({"id": uid}, {"$set": {"id": uid, "email": f"{uid}@throwaway.local",
                                                 "state": None, "throwaway": True}}, upsert=True)
        p1 = check_66a(token)
        p2 = check_377(token)
    finally:
        # ── Explicit revocation: delete the user, then PROVE the token 401s ──
        print("=" * 72); print("REVOCATION")
        users.delete_one({"id": uid})
        st, _ = retrieve(token, {"query": "x", "mode": "exact",
                                 "section_number": "377", "act_hint": "Indian Penal Code"})
        revoked = (st == 401)
        print(f"Throwaway user '{uid}' deleted. Same token re-hit → HTTP {st} "
              f"{'→ REVOKED (no longer authenticates)' if revoked else '→ WARNING: token still authenticates!'}")
        client.close()

    print("=" * 72)
    print(f"OVERALL: §66A {'PASS' if p1 else 'FAIL'} | IPC §377 {'PASS' if p2 else 'FAIL'} | "
          f"token {'REVOKED' if revoked else 'NOT REVOKED'} "
          f"→ {'ALL GUARDS FIRE IN PRODUCTION' if (p1 and p2 and revoked) else 'INVESTIGATE'}")
    sys.exit(0 if (p1 and p2 and revoked) else 1)


if __name__ == "__main__":
    main()
