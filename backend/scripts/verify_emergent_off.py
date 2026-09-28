"""Emergent-Independence smoke test.

Verifies the AI Gateway correctly honours `EMERGENT_OFF=1` + `COMPANY_LLM_KEY`
without needing a real Anthropic key or making a live LLM call.

Usage (from /app/backend):
    # Default (Emergent on):
    python scripts/verify_emergent_off.py

    # Simulate the staging switch:
    EMERGENT_OFF=1 COMPANY_LLM_KEY=sk-anthropic-live-... \
        python scripts/verify_emergent_off.py

    # Broken staging (flag set but no key) — must fall back with a warning:
    EMERGENT_OFF=1 python scripts/verify_emergent_off.py

Exit codes: 0 = all assertions passed, 1 = any assertion failed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure /app/backend on path irrespective of CWD.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force a clean re-import of settings + gateway so env changes take effect.
for mod in ("services.ai_gateway", "config.settings"):
    if mod in sys.modules:
        del sys.modules[mod]

from services.ai_gateway import gateway_status, PRIMARY, FALLBACK, _api_key  # noqa: E402


def _row(label: str, val: object) -> None:
    print(f"  {label:<28} {val}")


def main() -> int:
    print("─── AI Gateway snapshot ───")
    st = gateway_status()
    _row("primary",  f"{st['primary']['provider']} / {st['primary']['model']}")
    _row("fallback", f"{st['fallback']['provider']} / {st['fallback']['model']}")
    _row("emergent_off",     st["emergent_off"])
    _row("api_key_present",  st["api_key_present"])

    emergent_off = os.getenv("EMERGENT_OFF", "").lower() in ("1", "true", "yes")
    company_key  = os.getenv("COMPANY_LLM_KEY") or ""
    emergent_key = os.getenv("EMERGENT_LLM_KEY") or ""
    resolved     = _api_key()

    print("─── Env inputs ───")
    _row("EMERGENT_OFF",     emergent_off)
    _row("COMPANY_LLM_KEY",  f"set ({len(company_key)} chars)" if company_key else "(unset)")
    _row("EMERGENT_LLM_KEY", f"set ({len(emergent_key)} chars)" if emergent_key else "(unset)")

    print("─── Resolution check ───")
    if not emergent_off:
        assert resolved == emergent_key, "Emergent ON should resolve to EMERGENT_LLM_KEY"
        print("  ✅ Emergent ON — resolves to EMERGENT_LLM_KEY")
    elif emergent_off and company_key:
        assert resolved == company_key, "EMERGENT_OFF+COMPANY_LLM_KEY should resolve to COMPANY_LLM_KEY"
        print("  ✅ EMERGENT_OFF + COMPANY_LLM_KEY — resolves to COMPANY_LLM_KEY")
    else:
        assert resolved == emergent_key, "EMERGENT_OFF but no COMPANY_LLM_KEY → soft fallback to EMERGENT_LLM_KEY"
        print("  ⚠️  EMERGENT_OFF set but COMPANY_LLM_KEY missing — soft-fallback to Emergent key (expected warning above)")

    # Every model spec must be non-empty regardless of provider switch.
    assert PRIMARY.provider and PRIMARY.model, "PRIMARY model spec incomplete"
    assert FALLBACK.provider and FALLBACK.model, "FALLBACK model spec incomplete"
    print("  ✅ Primary + fallback model specs are populated")

    print("─── PASS ───")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"─── FAIL — {e} ───", file=sys.stderr)
        sys.exit(1)
