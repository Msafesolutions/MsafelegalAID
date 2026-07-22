"""Gandhikar backend API tests."""
import os
import json
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://bns-know-your-rights.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

TEST_EMAIL = "testuser@gandhikar.in"
TEST_PASSWORD = "test1234"
TEST_NAME = "Test User"


@pytest.fixture(scope="session")
def token():
    # Try login first; register if not present
    r = requests.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=30)
    if r.status_code == 200:
        return r.json()["token"]
    r = requests.post(f"{API}/auth/register", json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}, timeout=30)
    assert r.status_code == 200, f"register failed {r.status_code}: {r.text}"
    return r.json()["token"]


@pytest.fixture()
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- Health ---
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# --- Auth ---
def test_login_wrong_password():
    r = requests.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": "WRONG_pass"}, timeout=15)
    assert r.status_code == 401


def test_auth_me(auth_headers):
    r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == TEST_EMAIL
    assert "password_hash" not in data


def test_register_new_user_returns_token():
    email = f"TEST_new_{int(time.time()*1000)}@gandhikar.in"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "test1234", "name": "TEST New"}, timeout=15)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "token" in j and "user" in j
    assert j["user"]["email"].lower() == email.lower()


# --- Reference ---
def test_languages_23():
    r = requests.get(f"{API}/reference/languages", timeout=15)
    assert r.status_code == 200
    langs = r.json()
    assert isinstance(langs, list) and len(langs) == 23
    codes = [l["code"] for l in langs]
    assert "en" in codes and "hi" in codes


def test_models_3():
    r = requests.get(f"{API}/reference/models", timeout=15)
    assert r.status_code == 200
    models = r.json()
    assert len(models) == 3
    providers = sorted([m["provider"] for m in models])
    assert providers == ["anthropic", "gemini", "openai"]


def test_topics_8():
    r = requests.get(f"{API}/reference/topics", timeout=15)
    assert r.status_code == 200
    topics = r.json()
    assert len(topics) == 8
    for t in topics:
        assert t.get("title") and t.get("law") and isinstance(t.get("points"), list)


# --- Chat SSE ---
def _read_sse(resp, max_seconds=90):
    events = []
    start = time.time()
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        if raw.startswith("data:"):
            payload = raw[5:].strip()
            try:
                events.append(json.loads(payload))
            except Exception:
                pass
            if events and events[-1].get("type") in ("done", "error"):
                break
        if time.time() - start > max_seconds:
            break
    return events


def test_chat_stream_and_persistence(auth_headers):
    payload = {
        "message": "What are my rights during a police stop? Answer briefly.",
        "language": "en",
        "language_name": "English",
        "model_provider": "anthropic",
        "model_name": "claude-sonnet-4-5-20250929",
    }
    with requests.post(f"{API}/chat/stream", json=payload, headers=auth_headers, stream=True, timeout=120) as r:
        assert r.status_code == 200
        events = _read_sse(r)
    assert any(e.get("type") == "session" for e in events), events[:3]
    assert any(e.get("type") == "delta" for e in events), events[:3]
    assert events[-1].get("type") == "done", events[-3:]
    session_id = next(e["session_id"] for e in events if e.get("type") == "session")

    # List sessions
    r = requests.get(f"{API}/chat/sessions", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    assert any(s["id"] == session_id for s in r.json())

    # Messages in order
    r = requests.get(f"{API}/chat/sessions/{session_id}/messages", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    data = r.json()
    roles = [m["role"] for m in data["messages"]]
    assert roles[0] == "user" and "assistant" in roles

    # Delete session
    r = requests.delete(f"{API}/chat/sessions/{session_id}", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    r = requests.get(f"{API}/chat/sessions/{session_id}/messages", headers=auth_headers, timeout=15)
    assert r.status_code == 404


# --- Voice TTS ---
def test_tts_returns_audio(auth_headers):
    r = requests.post(f"{API}/voice/tts", json={"text": "You have the right to remain silent.", "language": "en"}, headers=auth_headers, timeout=60)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("audio/")
    assert len(r.content) > 1000
