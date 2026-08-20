"""
Iteration 14 backend tests (Dhara / MSafe Legal Aid)
- Labour code retrieval (Wage Code 17/18/45, IR Code 70, SS Code 53, SAMADHAN)
- State rent for new states (TG, WB, KL)
- Drafts quota endpoint POST /api/drafts/consume + /api/auth/me fields
- Citation-integrity guard (no "Section", "Article", act names, section numbers)
  in the model reply text (short_label chips are OK)
- Regression: cheque bounce, cyber fraud, MV 194D, Article 22, bookmarks, states
"""
import os
import json
import re
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    except Exception:
        pass
    return ""

BASE_URL = _load_backend_url()
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL missing"

PROTEST_EMAIL = "protest@gandhikar.in"
PROTEST_PASS = "test1234"

BANNED_TERMS = [
    "Section ", "Article ",
    "Code on Wages", "Industrial Relations Code", "Code on Social Security",
    "Rent Control Act", "Negotiable Instruments Act",
    "Motor Vehicles Act",
    "IPC ", "BNS ",
]


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(api):
    r = api.post(f"{BASE_URL}/api/auth/login",
                 json={"email": PROTEST_EMAIL, "password": PROTEST_PASS})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _chat_collect(api, headers, message, timeout=90):
    """Call /api/chat SSE and collect the message payload + citations."""
    r = api.post(
        f"{BASE_URL}/api/chat/stream",
        json={
            "message": message, "mode": "basic",
            "session_id": None, "language": "en", "language_name": "English",
        },
        headers=headers, stream=True, timeout=timeout,
    )
    assert r.status_code == 200, f"chat failed: {r.status_code} {r.text[:400]}"
    text_buf = []
    citations = []
    frames = []
    for raw in r.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8", errors="ignore")
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            evt = json.loads(payload)
        except Exception:
            continue
        frames.append(evt)
        t = evt.get("type")
        if t == "delta":
            text_buf.append(evt.get("content", ""))
        elif t == "citation":
            c = evt.get("citation")
            if c:
                citations.append(c)
        elif t == "citations":
            citations.extend(evt.get("citations", []))
        elif t == "final":
            # replace text with final sanitized content
            text_buf = [evt.get("content", "")]
        elif t == "done":
            break
    return "".join(text_buf), citations, frames


def _short_labels(citations):
    return [c.get("short_label", "") for c in citations]


def _assert_no_banned(text):
    for term in BANNED_TERMS:
        assert term.lower() not in text.lower(), f"reply leaked '{term}': {text[:400]}"
    # also no bare section numbers like 'Section 138' or standalone patterns
    assert not re.search(r"\bSection\s+\d+", text, re.I)
    assert not re.search(r"\bArticle\s+\d+", text, re.I)


# ------------------ labour retrieval ------------------
class TestLabourRetrieval:
    def test_unpaid_salary(self, api, auth_headers):
        text, cits, _ = _chat_collect(
            api, auth_headers,
            "My employer has not paid my salary for two months, where do I complain?",
        )
        labels = _short_labels(cits)
        # Expect Wage Code 17 / 45 or SAMADHAN portal (at least one)
        assert any(l in labels for l in ("Wage Code 17", "Wage Code 45", "SAMADHAN portal")), labels
        _assert_no_banned(text)

    def test_fired_without_notice(self, api, auth_headers):
        text, cits, _ = _chat_collect(api, auth_headers, "I was fired from my job without any notice")
        labels = _short_labels(cits)
        assert "IR Code 70" in labels, labels
        _assert_no_banned(text)

    def test_gratuity_5_years(self, api, auth_headers):
        text, cits, _ = _chat_collect(api, auth_headers, "Am I entitled to gratuity after 5 years")
        labels = _short_labels(cits)
        assert "SS Code 53" in labels, labels
        _assert_no_banned(text)

    def test_illegal_deduction(self, api, auth_headers):
        text, cits, _ = _chat_collect(api, auth_headers, "My salary was deducted illegally by my employer")
        labels = _short_labels(cits)
        assert "Wage Code 18" in labels, labels
        _assert_no_banned(text)


# ------------------ state rent for TG/WB/KL ------------------
def _set_state(api, headers, code):
    r = api.patch(f"{BASE_URL}/api/auth/state",
                  json={"state": code}, headers=headers)
    assert r.status_code == 200, r.text


class TestStateRent:
    def teardown_method(self, method):
        # Restore DL after each test
        pass

    def test_telangana_rent(self, api, auth_headers):
        _set_state(api, auth_headers, "TG")
        text, cits, _ = _chat_collect(api, auth_headers, "My landlord is evicting me for rent arrears")
        labels = _short_labels(cits)
        assert "Telangana Rent Control 10" in labels, labels
        # Verify state + text_kind fields present
        tg = next((c for c in cits if c.get("short_label") == "Telangana Rent Control 10"), None)
        assert tg and tg.get("state") == "TG"
        assert tg.get("text_kind")
        _assert_no_banned(text)

    def test_west_bengal_rent(self, api, auth_headers):
        _set_state(api, auth_headers, "WB")
        _, cits, _ = _chat_collect(api, auth_headers, "My landlord is evicting me for rent arrears")
        labels = _short_labels(cits)
        assert "WB Premises Tenancy 6-7" in labels, labels

    def test_kerala_rent(self, api, auth_headers):
        _set_state(api, auth_headers, "KL")
        _, cits, _ = _chat_collect(api, auth_headers, "My landlord is evicting me for rent arrears")
        labels = _short_labels(cits)
        assert "Kerala Rent Control 11" in labels, labels

    def test_restore_dl(self, api, auth_headers):
        _set_state(api, auth_headers, "DL")


# ------------------ drafts endpoint ------------------
class TestDraftsQuota:
    def test_no_token(self, api):
        r = requests.post(f"{BASE_URL}/api/drafts/consume",
                          json={"draft_type": "cheque_bounce"})
        assert r.status_code in (401, 403), r.status_code

    def test_unknown_type(self, api, auth_headers):
        r = api.post(f"{BASE_URL}/api/drafts/consume",
                     json={"draft_type": "unknown"}, headers=auth_headers)
        assert r.status_code == 400

    def test_reset_drafts_then_consume_and_exhaust(self, api, auth_headers):
        # Reset drafts_used to 0 via direct login refresh isn't available; use a helper endpoint if exists.
        # Since we can't call DB, we'll only verify the second-call paywall on a fresh non-Pro user.
        # Use protest user (non-Pro, drafts_used reset per credentials).
        me1 = api.get(f"{BASE_URL}/api/auth/me", headers=auth_headers).json()
        assert "drafts_used" in me1
        assert "drafts_free_limit" in me1
        assert "drafts_remaining" in me1

        # If user already exhausted, the first call should already return 402 — accept both scenarios
        r1 = api.post(f"{BASE_URL}/api/drafts/consume",
                      json={"draft_type": "cheque_bounce"}, headers=auth_headers)

        if r1.status_code == 200:
            data1 = r1.json()
            assert data1["ok"] is True
            assert "drafts_used" in data1 and "drafts_remaining" in data1
            # Now second call should paywall (unless the user is Pro)
            me2 = api.get(f"{BASE_URL}/api/auth/me", headers=auth_headers).json()
            if not me2.get("is_pro"):
                r2 = api.post(f"{BASE_URL}/api/drafts/consume",
                              json={"draft_type": "deposit_refund"}, headers=auth_headers)
                assert r2.status_code == 402, r2.status_code
                body = r2.json()
                detail = body.get("detail", body)
                assert detail.get("reason") == "drafts_exhausted", detail
        elif r1.status_code == 402:
            body = r1.json()
            detail = body.get("detail", body)
            assert detail.get("reason") == "drafts_exhausted", detail
        else:
            pytest.fail(f"Unexpected drafts/consume status: {r1.status_code} {r1.text}")


# ------------------ regression ------------------
class TestRegression:
    def test_cheque_bounce_ni_138(self, api, auth_headers):
        _, cits, _ = _chat_collect(api, auth_headers,
                                   "my cheque bounced, what is the notice deadline")
        labels = _short_labels(cits)
        assert "NI 138" in labels, labels

    def test_cyber_upi_fraud(self, api, auth_headers):
        _, cits, _ = _chat_collect(api, auth_headers, "money taken in UPI fraud")
        labels = _short_labels(cits)
        # Expect at least one cyber-related chip
        assert any(x in " ".join(labels).lower() for x in ("it 66d", "1930", "rbi", "cyber")), labels

    def test_helmet_fine(self, api, auth_headers):
        _, cits, _ = _chat_collect(api, auth_headers, "helmet fine india")
        labels = _short_labels(cits)
        assert any("194D" in l or "194" in l for l in labels), labels

    def test_arrest_rights(self, api, auth_headers):
        _, cits, _ = _chat_collect(api, auth_headers, "what are my rights when arrested")
        labels = _short_labels(cits)
        assert any("22" in l for l in labels), labels

    def test_states_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/reference/states")
        assert r.status_code == 200
        data = r.json()
        states = data if isinstance(data, list) else data.get("states", [])
        assert len(states) == 36, len(states)

    def test_bookmarks_roundtrip(self, api, auth_headers):
        # PUT
        bk = {"client_id": "test-iter14-1", "question": "TEST_q", "answer": "TEST_a",
              "citations": []}
        r = api.put(f"{BASE_URL}/api/bookmarks", json=bk, headers=auth_headers)
        assert r.status_code in (200, 201), r.text
        # GET
        r2 = api.get(f"{BASE_URL}/api/bookmarks", headers=auth_headers)
        assert r2.status_code == 200
        items = r2.json() if isinstance(r2.json(), list) else r2.json().get("bookmarks", [])
        assert any(b.get("client_id") == "test-iter14-1" for b in items)
        # DELETE
        r3 = api.delete(f"{BASE_URL}/api/bookmarks/test-iter14-1", headers=auth_headers)
        assert r3.status_code in (200, 204)
