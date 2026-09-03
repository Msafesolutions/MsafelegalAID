"""
Branch 1 — LIVE production guard check (run against the DEPLOYED app, not preview).

Confirms the two safety guards still fire end-to-end after the corpus-DB
permission fix + redeploy, by hitting the deployed /api/retrieve endpoint
(which applies G1 dead-law + G2 judicial-invalidation inside corpus_db):

  §66A IT Act   → is_dead_law True, dead_warning present, judicial_flag says
                  "struck down". (Statutory text may be served for historical
                  reference, but ONLY behind the warning.)
  IPC §377      → judicial_flag present (decriminalised), no_current_text True,
                  and NO fabricated section_text.

Usage:
    python3 verify_production_guards.py --base-url https://<live-app-url> --token <BEARER_JWT>
    # or via env:
    DHARA_PROD_URL=https://<live> DHARA_PROD_TOKEN=<jwt> python3 verify_production_guards.py

How to get <BEARER_JWT>: log into the deployed app once, then copy the JWT the
app stores after login (it is sent as the `Authorization: Bearer <token>`
header on every /api call). The token is required because /api/retrieve is an
authenticated endpoint.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def call_retrieve(base_url: str, token: str, body: dict) -> tuple[int, dict]:
    url = base_url.rstrip("/") + "/api/retrieve"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")}


def check_66a(base_url, token):
    print("=" * 72)
    print("VERIFICATION 1 — §66A IT Act (struck down) — LIVE")
    status, payload = call_retrieve(base_url, token, {
        "query": "Information Technology Act section 66A",
        "mode": "exact", "section_number": "66A",
        "act_hint": "Information Technology",
    })
    print(f"HTTP {status}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    results = payload.get("results") or []
    if not results:
        print("RESULT: FAIL — no result returned for §66A")
        return False
    r = results[0]
    dead = bool(r.get("is_dead_law"))
    dead_warn = r.get("dead_warning")
    jflag = (r.get("judicial_flag") or "")
    ok = dead and bool(dead_warn) and ("struck down" in jflag.lower())
    print(f"RESULT: is_dead_law={dead} | dead_warning={'present' if dead_warn else 'MISSING'} | "
          f"'struck down' in judicial_flag={'yes' if 'struck down' in jflag.lower() else 'NO'} "
          f"→ {'PASS' if ok else 'FAIL'}")
    return ok


def check_377(base_url, token):
    print("=" * 72)
    print("VERIFICATION 2 — IPC §377 (judicial invalidation) — LIVE")
    status, payload = call_retrieve(base_url, token, {
        "query": "Indian Penal Code section 377",
        "mode": "exact", "section_number": "377",
        "act_hint": "Indian Penal Code",
    })
    print(f"HTTP {status}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    results = payload.get("results") or []
    if not results:
        print("RESULT: FAIL — no result returned for §377")
        return False
    r = results[0]
    jflag = r.get("judicial_flag")
    no_text = bool(r.get("no_current_text"))
    served_text = r.get("section_text")
    ok = bool(jflag) and no_text and not served_text
    print(f"RESULT: judicial_flag={'present' if jflag else 'MISSING'} | no_current_text={no_text} | "
          f"section_text={'(none)' if not served_text else 'FABRICATED?!'} "
          f"→ {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("DHARA_PROD_URL"))
    ap.add_argument("--token", default=os.environ.get("DHARA_PROD_TOKEN"))
    args = ap.parse_args()
    if not args.base_url or not args.token:
        print("ERROR: provide --base-url and --token (or DHARA_PROD_URL / DHARA_PROD_TOKEN env vars).")
        sys.exit(2)
    print(f"Target: {args.base_url.rstrip('/')}/api/retrieve\n")
    p1 = check_66a(args.base_url, args.token)
    p2 = check_377(args.base_url, args.token)
    print("=" * 72)
    print(f"OVERALL: §66A {'PASS' if p1 else 'FAIL'} | IPC §377 {'PASS' if p2 else 'FAIL'} "
          f"→ {'ALL GUARDS FIRE IN PRODUCTION' if (p1 and p2) else 'INVESTIGATE'}")
    sys.exit(0 if (p1 and p2) else 1)


if __name__ == "__main__":
    main()
