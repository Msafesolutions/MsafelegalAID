"""
Iteration 13 backend tests — Dhara / MSafe Legal Aid.

Covers:
  * /api/reference/states (36 states/UTs)
  * PATCH /api/auth/state (set, invalid, clear) + /api/auth/me shape
  * /api/chat/stream retrieval integrity for:
        - Cheque bounce (NI 138)  — must NOT emit RTI/rent chips
        - Cyber fraud (IT 66D, cyber report 1930, RBI zero-liability)
        - Rent (Delhi Rent Control 14) when state=DL
        - state_prompt SSE frame when user has NO state set
        - state_note SSE frame for traffic-fine-amount when state=DL (no verified local rule)
  * Citation-integrity: model reply text must NOT contain 'Section' / 'Article' / act names / numbers
  * Bookmarks CRUD: idempotent PUT on client_id, GET, soft DELETE, auth (401 without token)
  * Regressions: MV 194D (helmet fine), MV 199A (minor driving), RTI 8 / RTI 18,
        Article 22 arrested rights, /api/auth/me, /api/voice/tts

Run:  pytest tests/test_iteration_13_state_bookmarks_ni_cyber.py -n 0 --tb=short
"""
import json
import os
import re
import uuid
from typing import Optional

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
if not BASE_URL:
    # frontend/.env carries EXPO_PUBLIC_BACKEND_URL — fall back to reading it directly
    envp = "/app/frontend/.env"
    if os.path.exists(envp):
        for line in open(envp):
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1].strip().strip('"')
                break
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL missing"
BASE_URL = BASE_URL.rstrip("/")

USER_WITH_STATE = ("protest@gandhikar.in", "test1234")     # will end this suite with state=DL
USER_NO_STATE = ("testuser@gandhikar.in", "test1234")      # legacy user, we clear state


# ---------- helpers ----------
def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _stream_collect(token: str, message: str, timeout: int = 90) -> dict:
    """POST /api/chat/stream and return {'events':[...], 'text':'..'}.

    Parses SSE frames of the form `data: {json}\n\n`.
    """
    url = f"{BASE_URL}/api/chat/stream"
    payload = {
        "message": message,
        "mode": "basic",
        "session_id": None,
        "language": "en",
        "language_name": "English",
    }
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}
    events, text = [], ""
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=timeout) as r:
        assert r.status_code == 200, f"stream {r.status_code}: {r.text[:200]}"
        buf = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            while "\n\n" in buf:
                frame, buf = buf.split("\n\n", 1)
                for line in frame.splitlines():
                    if line.startswith("data: "):
                        try:
                            ev = json.loads(line[6:])
                        except Exception:
                            continue
                        events.append(ev)
                        if ev.get("type") == "delta":
                            text += ev.get("content") or ""
                        if ev.get("type") == "done":
                            return {"events": events, "text": text}
    return {"events": events, "text": text}


def _citations(events: list) -> list:
    return [e.get("citation", {}) for e in events if e.get("type") == "citation"]


def _short_labels(events: list) -> list:
    return [c.get("short_label", "") for c in _citations(events)]


# citation-integrity regex — the reply must not name acts or section numbers
_FORBIDDEN_RE = re.compile(
    r"\b(Section|Sec\.|Sec\b|Article|Art\.|IPC|BNS|BNSS|BSA|CrPC|PWDVA|RTI Act|Motor Vehicles Act|Negotiable Instruments|IT Act|Information Technology Act|Consumer Protection Act|Rent Control Act|Article \d|section \d)\b",
    re.IGNORECASE,
)


# =====================================================================
# 1. /api/reference/states
# =====================================================================
class TestReferenceStates:
    def test_returns_36_states_and_uts(self):
        r = requests.get(f"{BASE_URL}/api/reference/states", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 36, f"expected 36 entries, got {len(data)}"
        states = [x for x in data if x.get("type") == "state"]
        uts = [x for x in data if x.get("type") == "ut"]
        assert len(states) == 28
        assert len(uts) == 8
        codes = {x["code"] for x in data}
        for expected in ("DL", "MH", "KA", "TN", "UP", "WB"):
            assert expected in codes


# =====================================================================
# 2. PATCH /api/auth/state
# =====================================================================
class TestAuthState:
    @pytest.fixture(scope="class")
    def token(self):
        return _login(*USER_WITH_STATE)

    def test_set_valid_state_dl(self, token):
        r = requests.patch(
            f"{BASE_URL}/api/auth/state",
            headers={"Authorization": f"Bearer {token}"},
            json={"state": "DL"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["state"] == "DL"
        assert j["state_name"] == "Delhi (NCT)"
        # /api/auth/me should reflect the same
        me = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert me.get("state") == "DL"
        assert me.get("state_name") == "Delhi (NCT)"

    def test_set_invalid_state_returns_400(self, token):
        r = requests.patch(
            f"{BASE_URL}/api/auth/state",
            headers={"Authorization": f"Bearer {token}"},
            json={"state": "ZZ"},
            timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_clear_state_then_restore(self, token):
        # clear
        r = requests.patch(
            f"{BASE_URL}/api/auth/state",
            headers={"Authorization": f"Bearer {token}"},
            json={"state": ""},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["state"] in (None, "")
        # restore DL so downstream tests using this account still see DL
        r2 = requests.patch(
            f"{BASE_URL}/api/auth/state",
            headers={"Authorization": f"Bearer {token}"},
            json={"state": "DL"},
        )
        assert r2.status_code == 200


# =====================================================================
# 3. /api/chat/stream — cheque bounce, cyber fraud, rent (DL), traffic-fine (DL)
# =====================================================================
class TestChatRetrievalIntegrity:
    @pytest.fixture(scope="class")
    def token_dl(self):
        tok = _login(*USER_WITH_STATE)
        # make sure state is DL
        requests.patch(
            f"{BASE_URL}/api/auth/state",
            headers={"Authorization": f"Bearer {tok}"},
            json={"state": "DL"},
        )
        return tok

    @pytest.fixture(scope="class")
    def token_nostate(self):
        tok = _login(*USER_NO_STATE)
        # clear state
        requests.patch(
            f"{BASE_URL}/api/auth/state",
            headers={"Authorization": f"Bearer {tok}"},
            json={"state": ""},
        )
        return tok

    def _forbidden_check(self, reply: str, query: str):
        """The model reply text must NEVER contain 'Section', 'Article', act names or numbers.

        Numerals inside a naked money-amount like '₹1,000' are OK — the forbidden regex looks
        for act references and section keywords."""
        m = _FORBIDDEN_RE.search(reply)
        assert not m, f"citation-integrity violation for query '{query}': forbidden token '{m.group()}' in reply -> {reply[:400]}"

    # -- cheque bounce --
    def test_cheque_bounce_returns_ni138_only(self, token_dl):
        out = _stream_collect(token_dl, "My cheque bounced, what is the deadline for the notice?")
        labels = _short_labels(out["events"])
        assert any(re.search(r"NI\s*138|Negotiable Instruments\s*138|N\.?I\.?\s*Act\s*138|138", lb, re.I) for lb in labels), (
            f"expected NI 138 chip, got labels={labels}"
        )
        # no unrelated chips (must not include RTI or Rent Control)
        for lb in labels:
            assert "RTI" not in lb.upper(), f"unrelated RTI chip on cheque-bounce query: {labels}"
            assert "Rent" not in lb, f"unrelated Rent chip on cheque-bounce query: {labels}"
        self._forbidden_check(out["text"], "cheque bounce")

    # -- cyber fraud --
    def test_cyber_fraud_returns_it66d_and_report_channels(self, token_dl):
        out = _stream_collect(token_dl, "Money was taken from my account in a UPI fraud, what do I do?")
        labels = " | ".join(_short_labels(out["events"]))
        # We want at least ONE of the cyber-report chips: IT 66D, 1930 helpline, RBI zero-liability
        matches_it66d = re.search(r"IT\s*66\s*D|66\s*D|IT Act.*66", labels, re.I)
        matches_helpline = re.search(r"1930|cybercrime\.gov\.in|Cyber\s*(Report|Helpline)", labels, re.I)
        matches_rbi = re.search(r"RBI|zero[- ]liability|3\s*(working|business)?\s*day", labels, re.I)
        assert matches_it66d or matches_helpline or matches_rbi, f"expected cyber chips, got labels={labels}"
        self._forbidden_check(out["text"], "cyber fraud")

    # -- rent with state=DL --
    def test_rent_query_with_state_dl_returns_delhi_rent_control_14(self, token_dl):
        out = _stream_collect(token_dl, "Can my landlord evict me without notice?")
        cits = _citations(out["events"])
        labels = [c.get("short_label", "") for c in cits]
        matched = None
        for c in cits:
            if re.search(r"Delhi Rent Control\s*14|Delhi Rent.*14", c.get("short_label", ""), re.I):
                matched = c
                break
        assert matched is not None, f"expected 'Delhi Rent Control 14' chip, got labels={labels}"
        # citation payload must expose the state field
        assert matched.get("state") == "DL" or (matched.get("state") or "").upper() == "DL", (
            f"state field missing in citation: {matched}"
        )

    # -- state_prompt when user has NO state --
    def test_rent_query_without_state_emits_state_prompt(self, token_nostate):
        # Use a state-sensitive rent question — security deposit is a rent/state topic
        out = _stream_collect(token_nostate, "How much security deposit can my landlord ask for?")
        types = [e.get("type") for e in out["events"]]
        assert "state_prompt" in types, f"expected state_prompt SSE frame, got types={types}"

    # -- state_note for traffic-fine amount with DL (no verified local rule) --
    def test_traffic_fine_amount_dl_emits_state_note_and_central_mv(self, token_dl):
        out = _stream_collect(token_dl, "What is the challan amount for jumping a red light?")
        types = [e.get("type") for e in out["events"]]
        assert "state_note" in types, f"expected state_note SSE frame, got types={types}"
        # Should still emit at least one central MV citation
        labels = " | ".join(_short_labels(out["events"]))
        assert re.search(r"MV\s*\d|Motor Vehicles", labels, re.I), f"expected central MV chip, got labels={labels}"


# =====================================================================
# 4. Bookmarks CRUD + auth
# =====================================================================
class TestBookmarks:
    @pytest.fixture(scope="class")
    def token(self):
        return _login(*USER_WITH_STATE)

    def test_auth_required(self):
        r = requests.get(f"{BASE_URL}/api/bookmarks", timeout=10)
        assert r.status_code in (401, 403), f"expected 401 without token, got {r.status_code}"

    def test_put_get_idempotent_and_delete(self, token):
        cid = f"TEST_{uuid.uuid4()}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "client_id": cid,
            "question": "TEST_ q",
            "answer": "TEST_ a",
            "language": "en",
            "citations": [{"short_label": "NI 138", "citation": "test"}],
        }
        # 1st PUT
        r1 = requests.put(f"{BASE_URL}/api/bookmarks", json=payload, headers=headers, timeout=15)
        assert r1.status_code == 200, r1.text
        first_id = r1.json().get("id")
        assert first_id, r1.json()
        # 2nd PUT — must be idempotent, no duplicates in GET
        r2 = requests.put(f"{BASE_URL}/api/bookmarks", json=payload, headers=headers, timeout=15)
        assert r2.status_code == 200, r2.text
        # GET should list exactly ONE with this client_id
        r3 = requests.get(f"{BASE_URL}/api/bookmarks", headers=headers, timeout=15)
        assert r3.status_code == 200
        items = r3.json()
        matching = [i for i in items if i.get("client_id") == cid]
        assert len(matching) == 1, f"expected 1 bookmark for {cid}, found {len(matching)}"
        # DELETE (soft) — should disappear from GET
        r4 = requests.delete(f"{BASE_URL}/api/bookmarks/{cid}", headers=headers, timeout=15)
        assert r4.status_code == 200
        r5 = requests.get(f"{BASE_URL}/api/bookmarks", headers=headers, timeout=15)
        assert r5.status_code == 200
        assert not any(i.get("client_id") == cid for i in r5.json()), "soft-deleted bookmark still visible in GET"


# =====================================================================
# 5. Regression — new MV & RTI retrieval, existing flows
# =====================================================================
class TestRegression:
    @pytest.fixture(scope="class")
    def token(self):
        return _login(*USER_WITH_STATE)

    @pytest.mark.parametrize("query,expected_pat", [
        ("helmet fine",                        r"MV\s*194\s*D|194\s*D"),
        ("minor driving car with parent's permission", r"MV\s*199\s*A|199\s*A"),
        ("my RTI was rejected on privacy grounds", r"RTI\s*8|Section 8"),
        ("how do I complain if my RTI is ignored", r"RTI\s*18|Section 18"),
    ])
    def test_mv_and_rti_retrieval(self, token, query, expected_pat):
        out = _stream_collect(token, query)
        labels = " | ".join(_short_labels(out["events"]))
        assert re.search(expected_pat, labels, re.I), f"query '{query}': expected {expected_pat}, got labels={labels}"

    def test_arrested_returns_article_22(self, token):
        out = _stream_collect(token, "What are my rights when arrested")
        labels = " | ".join(_short_labels(out["events"]))
        assert re.search(r"Article\s*22", labels, re.I), f"expected Article 22, got labels={labels}"

    def test_auth_me_ok(self, token):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert j.get("email") == USER_WITH_STATE[0]
        assert "state" in j and "state_name" in j

    def test_voice_tts(self, token):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": "hello from dhara", "language": "en"},
            timeout=45,
        )
        # tts returns audio; accept 200 with content
        assert r.status_code == 200, f"tts status {r.status_code}: {r.text[:200]}"
        assert len(r.content) > 200, "tts payload suspiciously small"
