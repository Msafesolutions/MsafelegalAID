"""
Backend tests for POST /api/voice/tts — OpenAI cloud TTS endpoint.

Fixes user report "speaker not working": on-device expo-speech silently failed on
many Android OEMs (Samsung/Xiaomi with non-Google TTS engines). We now route ALL
speaker requests through cloud TTS (OpenAI tts-1 via Emergent LLM key) so it
works on every device with zero OS settings changes.

Endpoint contract:
    Request:  POST /api/voice/tts   Bearer auth   body: {text, language, voice}
    Response: 200  Content-Type: audio/mpeg  body: raw MP3 bytes
              (the frontend calls resp.arrayBuffer() → File.write(cachePath) →
               createAudioPlayer(cachePath).play())

Cases covered:
  1) English text → 200 + non-empty MP3 (Content-Type audio/mpeg).
  2) Hindi text (Devanagari) with language='hi' → 200 + non-empty MP3.
  3) Tamil text (Tamil script) with language='ta' → 200 + non-empty MP3.
  4) Missing auth → 401.
  5) Empty text → either 200 (empty/near-empty MP3) or clean 4xx, NEVER a 500.
  6) Response Content-Type is exactly audio/mpeg (frontend's arrayBuffer() must
     receive raw audio bytes, not a JSON error).
  7) Regression: /api/voice/transcribe still handles a supported hint (en) so we
     haven't broken the mic while adding the speaker fix.
"""
import os
import io
import pytest
import requests

# The frontend uses EXPO_PUBLIC_BACKEND_URL — accept either name.
BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or ""
).rstrip("/")

if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL not configured"

TEST_EMAIL = "protest@gandhikar.in"
TEST_PASSWORD = "test1234"

# MP3 (MPEG audio) files typically start with either an ID3 tag (b"ID3") or an
# MPEG frame sync (0xFF Ex) — we assert one of these so a JSON error page can't
# masquerade as audio.
def _looks_like_mp3(data: bytes) -> bool:
    if not data or len(data) < 4:
        return False
    if data[:3] == b"ID3":
        return True
    # MPEG frame sync: 11 bits set → 0xFF followed by 0xE0..0xFF
    return data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and data["token"]
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- 1) English happy path ----------
class TestTTSEnglish:
    def test_english_returns_mp3(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers=auth_headers,
            json={"text": "This is a test", "language": "en", "voice": "alloy"},
            timeout=60,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
        ct = r.headers.get("Content-Type", "")
        assert "audio/mpeg" in ct, f"Content-Type should be audio/mpeg, got: {ct}"
        assert len(r.content) > 500, f"MP3 body suspiciously small: {len(r.content)} bytes"
        assert _looks_like_mp3(r.content), (
            f"Body does not look like MP3 (first 8 bytes: {r.content[:8]!r})"
        )


# ---------- 2) Hindi ----------
class TestTTSHindi:
    def test_hindi_returns_mp3(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers=auth_headers,
            json={"text": "यह एक परीक्षण है", "language": "hi", "voice": "alloy"},
            timeout=60,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
        assert "audio/mpeg" in r.headers.get("Content-Type", "")
        assert len(r.content) > 500, f"MP3 too small: {len(r.content)} bytes"
        assert _looks_like_mp3(r.content), (
            f"Not an MP3 (first bytes: {r.content[:8]!r})"
        )


# ---------- 3) Tamil ----------
class TestTTSTamil:
    def test_tamil_returns_mp3(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers=auth_headers,
            json={"text": "இது ஒரு சோதனை", "language": "ta", "voice": "alloy"},
            timeout=60,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
        assert "audio/mpeg" in r.headers.get("Content-Type", "")
        assert len(r.content) > 500, f"MP3 too small: {len(r.content)} bytes"
        assert _looks_like_mp3(r.content), (
            f"Not an MP3 (first bytes: {r.content[:8]!r})"
        )


# ---------- 4) Auth ----------
class TestTTSAuth:
    def test_missing_auth_returns_401(self):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            json={"text": "hello", "language": "en", "voice": "alloy"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text[:200]}"


# ---------- 5) Empty text — must not crash with 500 ----------
class TestTTSEmptyText:
    def test_empty_text_no_500_crash(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers=auth_headers,
            json={"text": "", "language": "en", "voice": "alloy"},
            timeout=30,
        )
        # Per spec: 200 (empty/near-empty MP3) OR clean 4xx are both acceptable.
        # A 500 with raw stack means the frontend arrayBuffer() will get an
        # HTML/JSON error page and the app breaks silently.
        assert r.status_code in (200, 400, 422), (
            f"Empty text should return 200 or 4xx, got {r.status_code}: {r.text[:250]}"
        )


# ---------- 6) Content-Type contract for frontend arrayBuffer() ----------
class TestTTSContentType:
    def test_content_type_is_audio_mpeg(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/voice/tts",
            headers=auth_headers,
            json={"text": "Content type check", "language": "en", "voice": "alloy"},
            timeout=60,
        )
        assert r.status_code == 200
        ct = r.headers.get("Content-Type", "").lower()
        # Must be audio/mpeg — NOT application/json — else the frontend's
        # arrayBuffer() call in speak() will still succeed but write a JSON blob
        # to disk which createAudioPlayer will silently fail to play.
        assert "audio/mpeg" in ct, (
            f"Frontend expects audio/mpeg (writes bytes directly to cache MP3), "
            f"got: {ct}. This will break the speaker."
        )
        assert "application/json" not in ct


# ---------- 7) Regression — /api/voice/transcribe still works with hint ----------
class TestTranscribeRegression:
    def test_transcribe_with_en_hint_still_200(self, auth_headers):
        """From iteration_9: language-hint fallback (with silent retry when the
        Emergent Whisper proxy rejects unsupported codes). Confirm the STT
        endpoint hasn't regressed while we added the TTS endpoint."""
        headers = {"Authorization": auth_headers["Authorization"]}
        # A silent MP3-ish blob works; we just want the endpoint to accept and
        # forward. Use a tiny generated buffer that Whisper will reject with a
        # graceful 4xx/5xx — the key regression is that the endpoint itself
        # returns a well-formed response, not the specific transcribed text.
        # We use the existing /tmp fixture if present; else use empty bytes.
        audio_path = "/tmp/test_audio.m4a"
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
        except FileNotFoundError:
            pytest.skip("test_audio.m4a fixture not present in this env")

        files = {"audio": ("audio.m4a", io.BytesIO(audio_bytes), "audio/m4a")}
        data = {"language": "en"}
        r = requests.post(
            f"{BASE_URL}/api/voice/transcribe",
            headers=headers,
            files=files,
            data=data,
            timeout=60,
        )
        assert r.status_code == 200, (
            f"transcribe(en) regression: expected 200, got {r.status_code}: {r.text[:250]}"
        )
        body = r.json()
        assert "text" in body and isinstance(body["text"], str)
