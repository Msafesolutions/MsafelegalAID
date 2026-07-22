"""Gandhikar backend API tests — Iteration 3 (Pro tier, Terms, phone)."""
import os
import json
import time
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if "EXPO_PUBLIC_BACKEND_URL" in os.environ else "https://bns-know-your-rights.preview.emergentagent.com"
API = f"{BASE_URL}/api"

# fresh email per session
UNIQ = int(time.time() * 1000)
NEW_EMAIL = f"test_iter3_{UNIQ}@gandhikar.in"
NEW_PW = "test1234"
NEW_NAME = "Iter3 Tester"
NEW_PHONE = f"+9198760{UNIQ % 100000:05d}"


# ---------- session token via fresh register (covers new schema) ----------
@pytest.fixture(scope="session")
def register_response():
    r = requests.post(f"{API}/auth/register", json={
        "email": NEW_EMAIL, "password": NEW_PW, "name": NEW_NAME,
        "phone": NEW_PHONE, "terms_accepted": True, "terms_version": "1.0",
    }, timeout=30)
    assert r.status_code == 200, f"register failed {r.status_code}: {r.text}"
    return r.json()


@pytest.fixture(scope="session")
def token(register_response):
    return register_response["token"]


@pytest.fixture()
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Health / legal / pricing ----------
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    assert j["copyright"] == "© Callistus Moses"
    assert j["company"] == "Msafe"
    assert j["terms_version"] == "1.0"


def test_legal_terms():
    r = requests.get(f"{API}/legal/terms", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["version"] == "1.0"
    txt = j["text"]
    for needle in ["Callistus Moses", "Msafe", "NOT a lawyer", "INDEMNITY"]:
        assert needle in txt, f"terms missing '{needle}'"
    assert "disclaimer_short" in j and len(j["disclaimer_short"]) > 20


def test_pricing():
    r = requests.get(f"{API}/billing/pricing", timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["pro_price_label"] == "₹999"
    assert j["billing_type"] == "one_time"
    assert isinstance(j["features"], list) and len(j["features"]) >= 4


# ---------- Register variations ----------
def test_register_without_terms_fails():
    r = requests.post(f"{API}/auth/register", json={
        "email": f"TEST_noterms_{UNIQ}@gandhikar.in", "password": NEW_PW,
        "name": "NoTerms", "phone": "+919999999999",
        "terms_accepted": False, "terms_version": "1.0",
    }, timeout=15)
    assert r.status_code == 400
    assert "Terms" in r.text or "terms" in r.text


def test_register_missing_phone_returns_422():
    r = requests.post(f"{API}/auth/register", json={
        "email": f"TEST_nophone_{UNIQ}@gandhikar.in", "password": NEW_PW,
        "name": "NoPhone", "terms_accepted": True, "terms_version": "1.0",
    }, timeout=15)
    assert r.status_code == 422, r.text


def test_register_success_returns_user_with_phone_terms(register_response):
    j = register_response
    assert "token" in j and "user" in j
    u = j["user"]
    assert u["email"] == NEW_EMAIL
    assert u["phone"] == NEW_PHONE
    assert u["is_pro"] is False
    assert u["terms_accepted"] is True
    assert u["terms_version"] == "1.0"
    assert u.get("terms_accepted_at")


# ---------- /auth/me exposes new fields ----------
def test_auth_me_has_new_fields(auth_headers):
    r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    for k in ["is_pro", "phone", "terms_accepted", "terms_version", "terms_accepted_at"]:
        assert k in j, f"missing key {k} in /auth/me"
    assert j["phone"] == NEW_PHONE
    assert j["terms_accepted"] is True


# ---------- Accept-terms (in-app) ----------
def test_accept_terms_in_app(auth_headers):
    r = requests.post(f"{API}/auth/accept-terms", json={"terms_version": "1.0"},
                     headers=auth_headers, timeout=15)
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["terms_version"] == "1.0"


# ---------- Chat persistence (user + assistant) ----------
def _read_sse(resp, max_seconds=120):
    events = []
    start = time.time()
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        if raw.startswith("data:"):
            try:
                events.append(json.loads(raw[5:].strip()))
            except Exception:
                pass
            if events and events[-1].get("type") in ("done", "error"):
                break
        if time.time() - start > max_seconds:
            break
    return events


def test_chat_stream_persists_both_roles(auth_headers):
    payload = {"message": "What is Article 21? Answer in one line.",
               "language": "en", "language_name": "English",
               "model_provider": "anthropic", "model_name": "claude-sonnet-4-5-20250929"}
    with requests.post(f"{API}/chat/stream", json=payload, headers=auth_headers,
                       stream=True, timeout=120) as r:
        assert r.status_code == 200
        events = _read_sse(r)
    session_id = next((e["session_id"] for e in events if e.get("type") == "session"), None)
    assert session_id, events[:3]
    # Give backend a moment to flush assistant save
    time.sleep(1.5)
    r = requests.get(f"{API}/chat/sessions/{session_id}/messages",
                    headers=auth_headers, timeout=15)
    assert r.status_code == 200
    msgs = r.json()["messages"]
    roles = [m["role"] for m in msgs]
    assert roles[0] == "user"
    assert "assistant" in roles
    # Order: user before assistant
    assert roles.index("user") < roles.index("assistant")


# ---------- Billing: checkout (expected 500 due to placeholder key) ----------
def test_checkout_requires_auth():
    r = requests.post(f"{API}/billing/checkout",
                     json={"return_url": "https://example.com/upgrade"}, timeout=15)
    assert r.status_code == 401


def test_checkout_with_auth_placeholder_key_500(auth_headers):
    r = requests.post(f"{API}/billing/checkout",
                     json={"return_url": "https://example.com/upgrade"},
                     headers=auth_headers, timeout=30)
    # EXPECTED failure — placeholder Stripe key
    assert r.status_code == 500
    assert "Invalid API Key" in r.text or "Checkout failed" in r.text


# ---------- Stripe webhook route exists ----------
def test_stripe_webhook_malformed_returns_400():
    r = requests.post(f"{BASE_URL}/api/webhooks/stripe", data=b"not-json",
                     headers={"stripe-signature": "x"}, timeout=15)
    assert r.status_code == 400


# ---------- Reference: sanity ----------
def test_languages_23():
    r = requests.get(f"{API}/reference/languages", timeout=15)
    assert r.status_code == 200
    assert len(r.json()) == 23


def test_topics_8():
    r = requests.get(f"{API}/reference/topics", timeout=15)
    assert r.status_code == 200
    assert len(r.json()) == 8
