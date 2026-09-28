"""Golden regression tests for Layer M (Answer Generator) + Layer S (Status Guard).

Pure-python, no LLM calls, no DB — safe to run in CI.

Coverage:
  • all_provisions_dead()                    — 12 cases
  • build_cannot_verify_response()           — 10 cases
  • augment_prompt_with_status_guard()       —  8 cases
  • strip_leaked_citations()                 — 10 cases
                                                ────
                                         Total: 40 cases

Run:
    cd /app/backend
    python -m pytest tests/test_layer_m_golden.py -v
"""
from __future__ import annotations

import pytest

from engine.answer_generator import (
    all_provisions_dead,
    build_cannot_verify_response,
    augment_prompt_with_status_guard,
    strip_leaked_citations,
)
from engine.models import LegalQuery


# ─────────────────────────────────────────────────────────────────────────────
# 1. all_provisions_dead — 12 cases
# ─────────────────────────────────────────────────────────────────────────────

class TestAllProvisionsDead:
    def test_01_empty_returns_false(self):
        # Empty corpus is handled elsewhere (REFUSAL_NO_CORPUS) — not "all dead".
        assert all_provisions_dead([]) is False

    def test_02_none_returns_false(self):
        assert all_provisions_dead(None) is False

    def test_03_single_live_hit_returns_false(self):
        assert all_provisions_dead([{"act_name": "BNS", "section_number": "302", "status": "ACTIVE"}]) is False

    def test_04_single_dead_flag_returns_true(self):
        assert all_provisions_dead([{"is_dead_law": True}]) is True

    def test_05_single_repealed_status_returns_true(self):
        assert all_provisions_dead([{"status": "REPEALED"}]) is True

    def test_06_single_superseded_status_returns_true(self):
        assert all_provisions_dead([{"status": "SUPERSEDED"}]) is True

    def test_07_single_struck_down_status_returns_true(self):
        assert all_provisions_dead([{"status": "STRUCK_DOWN"}]) is True

    def test_08_single_not_yet_in_force_returns_true(self):
        assert all_provisions_dead([{"status": "NOT_YET_IN_FORCE"}]) is True

    def test_09_partially_repealed_treated_as_dead(self):
        # Conservative: PARTIALLY_REPEALED still triggers cannot-verify UX,
        # because we cannot reason about the surviving pieces safely.
        assert all_provisions_dead([{"status": "PARTIALLY_REPEALED"}]) is True

    def test_10_mixed_dead_and_alive_returns_false(self):
        assert all_provisions_dead([
            {"is_dead_law": True},
            {"status": "ACTIVE"},
        ]) is False

    def test_11_all_dead_via_warning_field_returns_true(self):
        assert all_provisions_dead([
            {"dead_warning": "IPC replaced by BNS from 1 Jul 2024"},
            {"status": "REPEALED"},
        ]) is True

    def test_12_status_case_insensitive(self):
        assert all_provisions_dead([{"status": "repealed"}]) is True
        assert all_provisions_dead([{"status": "Superseded"}]) is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. build_cannot_verify_response — 10 cases
# ─────────────────────────────────────────────────────────────────────────────

def _lq(query: str, actions=None, issues=None):
    return LegalQuery(
        original_query=query,
        actions=actions or [],
        candidate_issues=issues or [],
    )


class TestCannotVerifyResponse:
    def test_13_emits_all_required_sections(self):
        msg = build_cannot_verify_response(_lq("q"), "en")
        assert "ANSWER" in msg
        assert "WHY" in msg
        assert "WHAT YOU CAN DO" in msg
        assert "VERIFIED SOURCES" in msg

    def test_14_never_fabricates_an_active_law(self):
        # No section number invented — content must be about NOT finding an active law.
        msg = build_cannot_verify_response(_lq("cheating case IPC 420"), "en")
        assert "could not find an ACTIVE" in msg
        assert "REPEALED or SUPERSEDED" in msg

    def test_15_includes_bns_transition_hint(self):
        # BNS/BNSS/BSA references live in the WHY block for user context.
        msg = build_cannot_verify_response(_lq("q"), "en")
        assert "BNS" in msg or "1 July 2024" in msg

    def test_16_includes_112_emergency_helpline(self):
        msg = build_cannot_verify_response(_lq("q"), "en")
        assert "112" in msg

    def test_17_dead_hits_rendered_with_status(self):
        msg = build_cannot_verify_response(
            _lq("q"), "en",
            dead_hits=[{"act_name": "IPC", "section_number": "420",
                        "status": "SUPERSEDED", "successor_act": "BNS"}],
        )
        assert "IPC" in msg and "420" in msg and "SUPERSEDED" in msg and "BNS" in msg

    def test_18_multiple_dead_hits_all_listed(self):
        msg = build_cannot_verify_response(
            _lq("q"), "en",
            dead_hits=[
                {"act_name": "IPC", "section_number": "302", "status": "SUPERSEDED", "successor_act": "BNS"},
                {"act_name": "CrPC", "section_number": "154", "status": "SUPERSEDED", "successor_act": "BNSS"},
                {"act_name": "Evidence Act", "section_number": "3", "status": "SUPERSEDED", "successor_act": "BSA"},
            ],
        )
        assert "IPC" in msg and "CrPC" in msg and "Evidence Act" in msg
        assert "BNS" in msg and "BNSS" in msg and "BSA" in msg

    def test_19_dead_hits_capped_at_five(self):
        # Guard against unbounded output when Layer S returns dozens of hits.
        hits = [{"act_name": f"Act{i}", "section_number": str(i), "status": "REPEALED"} for i in range(15)]
        msg = build_cannot_verify_response(_lq("q"), "en", dead_hits=hits)
        assert "Act0" in msg
        assert "Act4" in msg
        assert "Act14" not in msg   # Truncated after 5.

    def test_20_no_dead_hits_falls_back_to_placeholder(self):
        msg = build_cannot_verify_response(_lq("q"), "en")
        assert "No active statutory source located" in msg

    def test_21_disclaimer_present(self):
        msg = build_cannot_verify_response(_lq("q"), "en")
        assert "Legal information, not legal advice" in msg

    def test_22_language_hint_for_non_english(self):
        # Non-English requests get a lang_hint marker so upstream localiser
        # can convert without our code emitting broken machine translation.
        msg = build_cannot_verify_response(_lq("q"), "hi")
        assert "[lang_hint:hi]" in msg


# ─────────────────────────────────────────────────────────────────────────────
# 3. augment_prompt_with_status_guard — 8 cases
# ─────────────────────────────────────────────────────────────────────────────

class TestStatusGuardAugmentation:
    BASE = "You are Dhara. Answer the user's Indian legal question."

    def test_23_no_dead_hits_prompt_untouched(self):
        assert augment_prompt_with_status_guard(self.BASE, []) == self.BASE

    def test_24_all_live_hits_prompt_untouched(self):
        hits = [{"act_name": "BNS", "section_number": "302", "status": "ACTIVE"}]
        assert augment_prompt_with_status_guard(self.BASE, hits) == self.BASE

    def test_25_single_dead_hit_appends_guard_notice(self):
        hits = [{"act_name": "IPC", "section_number": "420", "status": "SUPERSEDED"}]
        out = augment_prompt_with_status_guard(self.BASE, hits)
        assert out != self.BASE
        assert "STATUS-GUARD NOTICE" in out
        assert "IPC" in out and "§420" in out

    def test_26_guard_notice_references_layer_s(self):
        hits = [{"is_dead_law": True, "act_name": "CrPC", "section_number": "154"}]
        out = augment_prompt_with_status_guard(self.BASE, hits)
        assert "Layer S" in out

    def test_27_guard_lists_up_to_three_dead_acts(self):
        hits = [
            {"act_name": "IPC", "section_number": "302", "status": "SUPERSEDED"},
            {"act_name": "IPC", "section_number": "420", "status": "SUPERSEDED"},
            {"act_name": "CrPC", "section_number": "154", "status": "SUPERSEDED"},
            {"act_name": "Evidence Act", "section_number": "3", "status": "SUPERSEDED"},
            {"act_name": "POTA", "section_number": "1", "status": "REPEALED"},
        ]
        out = augment_prompt_with_status_guard(self.BASE, hits)
        # 3 of the 5 present, POTA (index 4) truncated.
        listed = [name for name in ("IPC §302", "IPC §420", "CrPC §154") if name in out]
        assert len(listed) == 3
        assert "POTA" not in out

    def test_28_mixed_dead_alive_still_triggers(self):
        hits = [
            {"act_name": "IPC", "section_number": "420", "status": "SUPERSEDED"},
            {"act_name": "BNS", "section_number": "318", "status": "ACTIVE"},
        ]
        out = augment_prompt_with_status_guard(self.BASE, hits)
        assert "STATUS-GUARD NOTICE" in out
        assert "IPC" in out

    def test_29_missing_section_number_still_renders(self):
        hits = [{"act_name": "POTA", "status": "REPEALED"}]
        out = augment_prompt_with_status_guard(self.BASE, hits)
        assert "POTA" in out

    def test_30_original_prompt_preserved_before_guard(self):
        # The user's system prompt must still lead — we only append.
        hits = [{"status": "SUPERSEDED"}]
        out = augment_prompt_with_status_guard(self.BASE, hits)
        assert out.startswith(self.BASE)


# ─────────────────────────────────────────────────────────────────────────────
# 4. strip_leaked_citations — 10 cases
# ─────────────────────────────────────────────────────────────────────────────

class TestStripLeakedCitations:
    def test_31_ipc_section_number_removed(self):
        out = strip_leaked_citations("You may be charged under IPC 420 today.")
        assert "IPC 420" not in out
        assert "the law" in out

    def test_32_bns_section_number_removed(self):
        out = strip_leaked_citations("BNS Section 318 covers cheating.")
        assert "BNS Section 318" not in out
        assert "the law" in out

    def test_33_dpdp_section_number_removed(self):
        out = strip_leaked_citations("The DPDP Section 8 applies here.")
        assert "DPDP Section 8" not in out

    def test_34_article_number_replaced(self):
        out = strip_leaked_citations("Article 21 protects the right to life.")
        assert "Article 21" not in out
        assert "the constitutional right" in out

    def test_35_multiple_citations_all_stripped(self):
        text = "Under IPC 420 and Article 14 you have remedies."
        out = strip_leaked_citations(text)
        assert "IPC 420" not in out
        assert "Article 14" not in out

    def test_36_no_double_space_left_behind(self):
        out = strip_leaked_citations("File under IPC 302  and act fast.")
        assert "  " not in out

    def test_37_no_orphan_comma_left(self):
        out = strip_leaked_citations("File a complaint under BNS 63 , per counsel.")
        assert " ," not in out

    def test_38_empty_string_returns_empty(self):
        assert strip_leaked_citations("") == ""

    def test_39_none_returns_none(self):
        assert strip_leaked_citations(None) is None

    def test_40_plain_text_untouched(self):
        # Reply that carries no section numbers must be returned as-is (minus
        # collapse-whitespace which does nothing here).
        text = "You have the right to consult an advocate before signing anything."
        assert strip_leaked_citations(text) == text


if __name__ == "__main__":
    # Allow `python tests/test_layer_m_golden.py` to run quickly without pytest.
    import sys
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestAllProvisionsDead, TestCannotVerifyResponse,
                TestStatusGuardAugmentation, TestStripLeakedCitations):
        suite.addTests(loader.loadTestsFromTestCase(_pytest_class_to_unittest(cls)))
    runner = unittest.TextTestRunner(verbosity=2)
    sys.exit(0 if runner.run(suite).wasSuccessful() else 1)


def _pytest_class_to_unittest(cls):
    """Very small adapter so the file runs under both pytest and stdlib unittest.
    Only used by the `__main__` shim above — never imported at test-collection time.
    """
    import unittest
    methods = {name: getattr(cls, name) for name in dir(cls) if name.startswith("test_")}
    return type(cls.__name__, (unittest.TestCase,), methods)
