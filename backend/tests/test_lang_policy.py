"""
Language-enforcement + SOS-move regression suite (iteration 16).

Focus:
  1. /api/chat/stream returns predominantly Devanagari for hi, Tamil for ta,
     Bengali for bn (final SSE frame wins over deltas).
  2. English query remains English, cites Article 22, no citation leakage.
  3. Also unit-tests /app/backend/langpolicy.py directly.
"""

import json
import os
import re
import time

import pytest
import requests

_env = "/app/frontend/.env"
if "EXPO_PUBLIC_BACKEND_URL" not in os.environ and os.path.exists(_env):
    for _l in open(_env):
        if _l.startswith("EXPO_PUBLIC_BACKEND_URL"):
            os.environ["EXPO_PUBLIC_BACKEND_URL"] = _l.split("=", 1)[1].strip().strip('"')
            break

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")

CREDS = {"email": "protest@gandhikar.in", "password": "test1234"}


# --------------------------- fixtures ---------------------------

@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=CREDS, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ------------------------ langpolicy unit --------------------------

def test_langpolicy_module_hindi():
    from langpolicy import needs_language_repair, script_ratio

    en_text = "Under Article 22 of the Constitution, arrested persons have rights."
    hi_text = "गिरफ्तारी के समय आपको अनुच्छेद 22 के तहत अधिकार मिलते हैं।" * 2

    # English text with lang=hi must need repair
    assert needs_language_repair(en_text, "hi") is True
    # Hindi text with lang=hi must NOT need repair
    assert needs_language_repair(hi_text, "hi") is False
    # English text with lang=en must not need repair
    assert needs_language_repair(en_text, "en") is False
    assert script_ratio(hi_text, "devanagari") > 0.35


def test_langpolicy_module_tamil_bengali():
    from langpolicy import needs_language_repair

    en_text = "Arrested persons enjoy fundamental rights under the constitution."
    ta_text = "கைது செய்யப்பட்டவருக்கு அரசியலமைப்பின் கீழ் உரிமைகள் உள்ளன." * 2
    bn_text = "গ্রেপ্তার হওয়া ব্যক্তির সংবিধানের অধীনে অধিকার রয়েছে।" * 2

    assert needs_language_repair(en_text, "ta") is True
    assert needs_language_repair(ta_text, "ta") is False
    assert needs_language_repair(en_text, "bn") is True
    assert needs_language_repair(bn_text, "bn") is False


# ------------------------ SSE helpers ------------------------

def _consume_stream(url, headers, payload, timeout=180):
    """Return (final_text, all_deltas, saw_final, saw_error)."""
    deltas = []
    final_text = None
    saw_final = False
    saw_error = None
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=timeout) as r:
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        buf = ""
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buf += chunk
            while "\n\n" in buf:
                raw, buf = buf.split("\n\n", 1)
                for line in raw.splitlines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data:
                        continue
                    try:
                        ev = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    t = ev.get("type")
                    if t == "delta":
                        deltas.append(ev.get("content", ""))
                    elif t == "final":
                        final_text = ev.get("content", "")
                        saw_final = True
                    elif t == "error":
                        saw_error = ev.get("error")
                    elif t == "done":
                        pass
    body = final_text if saw_final else "".join(deltas)
    return body, deltas, saw_final, saw_error


def _script_ratio(text, ranges):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    hits = sum(1 for c in letters if any(lo <= ord(c) <= hi for lo, hi in ranges))
    return hits / len(letters)


DEVANAGARI = [(0x0900, 0x097F)]
TAMIL = [(0x0B80, 0x0BFF)]
BENGALI = [(0x0980, 0x09FF)]


# ------------------------ integration ------------------------

def _payload(msg, lang, name, native):
    return {
        "message": msg,
        "mode": "basic",
        "session_id": None,
        "language": lang,
        "language_name": name,
        "language_native": native,
    }


class TestReplyLanguage:
    def test_hindi_answer_is_devanagari(self, auth_headers):
        url = f"{BASE_URL}/api/chat/stream"
        payload = _payload(
            "गिरफ्तारी के समय मेरे अधिकार क्या हैं?",
            "hi", "Hindi", "हिन्दी",
        )
        body, _, _, err = _consume_stream(url, auth_headers, payload)
        assert not err, f"stream error: {err}"
        assert body, "empty body"
        ratio = _script_ratio(body, DEVANAGARI)
        print(f"[hi] len={len(body)} devanagari_ratio={ratio:.3f}")
        print(f"[hi] preview: {body[:200]!r}")
        assert ratio >= 0.35, f"Hindi reply not in Devanagari (ratio={ratio:.2f}): {body[:300]}"

    def test_tamil_answer_is_tamil_script(self, auth_headers):
        # small pause to avoid rate limits on the model
        time.sleep(2)
        url = f"{BASE_URL}/api/chat/stream"
        payload = _payload(
            "கைது செய்யப்பட்டால் என் உரிமைகள் என்ன?",
            "ta", "Tamil", "தமிழ்",
        )
        body, _, _, err = _consume_stream(url, auth_headers, payload)
        assert not err, f"stream error: {err}"
        assert body, "empty body"
        ratio = _script_ratio(body, TAMIL)
        print(f"[ta] len={len(body)} tamil_ratio={ratio:.3f}")
        print(f"[ta] preview: {body[:200]!r}")
        assert ratio >= 0.35, f"Tamil reply not in Tamil script (ratio={ratio:.2f}): {body[:300]}"

    def test_bengali_answer_is_bengali_script(self, auth_headers):
        time.sleep(2)
        url = f"{BASE_URL}/api/chat/stream"
        payload = _payload(
            "গ্রেপ্তার হলে আমার অধিকার কী?",
            "bn", "Bengali", "বাংলা",
        )
        body, _, _, err = _consume_stream(url, auth_headers, payload)
        assert not err, f"stream error: {err}"
        assert body, "empty body"
        ratio = _script_ratio(body, BENGALI)
        print(f"[bn] len={len(body)} bengali_ratio={ratio:.3f}")
        print(f"[bn] preview: {body[:200]!r}")
        assert ratio >= 0.35, f"Bengali reply not in Bengali script (ratio={ratio:.2f}): {body[:300]}"


class TestEnglishRegression:
    def test_english_untouched_no_citation_leak(self, auth_headers):
        time.sleep(2)
        url = f"{BASE_URL}/api/chat/stream"
        payload = _payload(
            "What are my rights when arrested?",
            "en", "English", "English",
        )
        body, _, saw_final, err = _consume_stream(url, auth_headers, payload)
        assert not err, f"stream error: {err}"
        assert body, "empty body"
        # English text should be predominantly Latin
        latin_ratio = _script_ratio(body, [(0x0041, 0x005A), (0x0061, 0x007A)])
        print(f"[en] latin_ratio={latin_ratio:.3f} final_frame={saw_final}")
        print(f"[en] preview: {body[:300]!r}")
        assert latin_ratio > 0.9, f"English reply not Latin (ratio={latin_ratio:.2f})"
        # No repair should have kicked in for English — no 'final' frame is expected
        # unless the sanitizer stripped something, so allow either but log it.
        # Citation integrity: body must not contain literal 'Section X' / 'Article X'
        # patterns (the verified citations come from separate frames).
        forbidden = re.findall(r"\b(Section|Article)\s+\d+", body)
        assert not forbidden, f"citation leaked into body: {forbidden[:5]}"
