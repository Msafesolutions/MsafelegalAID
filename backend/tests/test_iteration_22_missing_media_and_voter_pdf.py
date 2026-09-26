"""
Iteration 22 backend tests
- Missing-person private photo APIs (/api/missing/{draftId}/photos)
- Owner isolation + auth guards + payload validation + 5MB cap + max-3 constraint
- Voter PDF regression smoke check (/api/voter/pdf)
"""

import io
import os
import time
import uuid

import pytest
import requests
from PIL import Image


def _load_base_url() -> str:
    # Use preview host first (what users see), then backend URL fallback.
    for key in ("EXPO_PACKAGER_HOSTNAME", "EXPO_PACKAGER_PROXY_URL", "EXPO_PUBLIC_BACKEND_URL", "EXPO_BACKEND_URL"):
        value = os.environ.get(key)
        if value:
            return value.strip().strip('"').rstrip("/")
    try:
        with open("/app/frontend/.env", "r", encoding="utf-8") as f:
            env = {}
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
        for key in ("EXPO_PACKAGER_HOSTNAME", "EXPO_PACKAGER_PROXY_URL", "EXPO_PUBLIC_BACKEND_URL", "EXPO_BACKEND_URL"):
            if env.get(key):
                return env[key].rstrip("/")
    except Exception:
        pass
    return ""


BASE_URL = _load_base_url()
assert BASE_URL, "Missing base URL configuration"

USER1_EMAIL = "voicetest2026@example.com"
USER1_PASS = "TestPass123!"
USER2_EMAIL = "fir-test-user2@example.com"
USER2_PASS = "TestPass456!"


def _make_png_bytes(size=(32, 32), color=(20, 140, 220)) -> bytes:
    image = Image.new("RGB", size, color)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    assert body.get("token"), f"Token missing for {email}"
    return body["token"]


@pytest.fixture(scope="module")
def auth_tokens():
    token1 = _login(USER1_EMAIL, USER1_PASS)
    try:
        token2 = _login(USER2_EMAIL, USER2_PASS)
    except AssertionError:
        token2 = None
    return {"u1": token1, "u2": token2}


@pytest.fixture(scope="module")
def draft_id():
    return f"testmissing{int(time.time())}{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def created_photo_ids():
    return []


class TestMissingPhotosApi:
    def test_anonymous_list_is_401(self, draft_id):
        r = requests.get(f"{BASE_URL}/api/missing/{draft_id}/photos", timeout=30)
        assert r.status_code == 401, r.text

    def test_anonymous_post_is_401(self, draft_id):
        files = {"file": ("sample.png", io.BytesIO(_make_png_bytes()), "image/png")}
        r = requests.post(f"{BASE_URL}/api/missing/{draft_id}/photos", files=files, timeout=30)
        assert r.status_code == 401, r.text

    def test_upload_png_success_and_response_shape(self, auth_tokens, draft_id, created_photo_ids):
        files = {"file": ("sample.png", io.BytesIO(_make_png_bytes()), "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/missing/{draft_id}/photos",
            headers=_auth_headers(auth_tokens["u1"]),
            files=files,
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body.get("file_id"), str) and body["file_id"]
        assert isinstance(body.get("filename"), str) and body["filename"]
        assert isinstance(body.get("size"), int) and body["size"] > 0
        assert "storage_path" not in body
        created_photo_ids.append(body["file_id"])

    def test_owner_list_includes_uploaded_photo(self, auth_tokens, draft_id, created_photo_ids):
        r = requests.get(
            f"{BASE_URL}/api/missing/{draft_id}/photos",
            headers=_auth_headers(auth_tokens["u1"]),
            timeout=30,
        )
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert any(it.get("file_id") in created_photo_ids for it in items), items

    def test_owner_read_photo_returns_image_bytes(self, auth_tokens, draft_id, created_photo_ids):
        file_id = created_photo_ids[0]
        r = requests.get(
            f"{BASE_URL}/api/missing/{draft_id}/photos/{file_id}",
            headers=_auth_headers(auth_tokens["u1"]),
            timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.headers.get("Content-Type", "").startswith("image/")
        assert len(r.content) > 100

    def test_cross_user_cannot_read_private_photo(self, auth_tokens, draft_id, created_photo_ids):
        if not auth_tokens["u2"]:
            pytest.skip("Second test account unavailable in this environment")
        file_id = created_photo_ids[0]
        list_resp = requests.get(
            f"{BASE_URL}/api/missing/{draft_id}/photos",
            headers=_auth_headers(auth_tokens["u2"]),
            timeout=30,
        )
        assert list_resp.status_code == 200, list_resp.text
        assert list_resp.json() == []
        read_resp = requests.get(
            f"{BASE_URL}/api/missing/{draft_id}/photos/{file_id}",
            headers=_auth_headers(auth_tokens["u2"]),
            timeout=30,
        )
        assert read_resp.status_code == 404, read_resp.text

    def test_cross_user_delete_returns_404(self, auth_tokens, draft_id, created_photo_ids):
        if not auth_tokens["u2"]:
            pytest.skip("Second test account unavailable in this environment")
        file_id = created_photo_ids[0]
        delete_resp = requests.delete(
            f"{BASE_URL}/api/missing/{draft_id}/photos/{file_id}",
            headers=_auth_headers(auth_tokens["u2"]),
            timeout=30,
        )
        assert delete_resp.status_code == 404, delete_resp.text

    def test_invalid_bytes_rejected(self, auth_tokens, draft_id):
        bad_bytes = io.BytesIO(b"this-is-not-an-image")
        files = {"file": ("bad.jpg", bad_bytes, "image/jpeg")}
        r = requests.post(
            f"{BASE_URL}/api/missing/{draft_id}/photos",
            headers=_auth_headers(auth_tokens["u1"]),
            files=files,
            timeout=30,
        )
        assert r.status_code == 415, r.text

    def test_oversize_over_5mb_rejected(self, auth_tokens, draft_id):
        payload = io.BytesIO(b"0" * (5 * 1024 * 1024 + 4))
        files = {"file": ("large.jpg", payload, "image/jpeg")}
        r = requests.post(
            f"{BASE_URL}/api/missing/{draft_id}/photos",
            headers=_auth_headers(auth_tokens["u1"]),
            files=files,
            timeout=60,
        )
        assert r.status_code == 413, r.text

    def test_max_three_files_then_conflict(self, auth_tokens):
        draft = f"max3test{int(time.time())}{uuid.uuid4().hex[:6]}"
        headers = _auth_headers(auth_tokens["u1"])
        for i in range(3):
            files = {"file": (f"ok{i}.png", io.BytesIO(_make_png_bytes(color=(40 + i, 40, 200))), "image/png")}
            r = requests.post(f"{BASE_URL}/api/missing/{draft}/photos", headers=headers, files=files, timeout=60)
            assert r.status_code == 200, f"upload {i} failed: {r.status_code} {r.text}"
        files = {"file": ("overflow.png", io.BytesIO(_make_png_bytes(color=(255, 10, 10))), "image/png")}
        overflow = requests.post(f"{BASE_URL}/api/missing/{draft}/photos", headers=headers, files=files, timeout=60)
        assert overflow.status_code == 409, overflow.text

    def test_detach_photo_then_read_404(self, auth_tokens, draft_id, created_photo_ids):
        file_id = created_photo_ids[0]
        delete_resp = requests.delete(
            f"{BASE_URL}/api/missing/{draft_id}/photos/{file_id}",
            headers=_auth_headers(auth_tokens["u1"]),
            timeout=30,
        )
        assert delete_resp.status_code == 204, delete_resp.text

        read_again = requests.get(
            f"{BASE_URL}/api/missing/{draft_id}/photos/{file_id}",
            headers=_auth_headers(auth_tokens["u1"]),
            timeout=30,
        )
        assert read_again.status_code == 404, read_again.text


class TestVoterPdfEndpoint:
    def test_voter_pdf_form6_smoke(self):
        payload = {
            "form_type": "form6",
            "language": "en",
            "answers": {
                "applicant_name_en": "TEST Jane Citizen",
                "father_husband_name": "TEST Parent",
                "date_of_birth": "1998-01-15",
                "gender": "Female",
                "house_number": "12A",
                "street_area": "Test Street",
                "district_state": "Mumbai, MH",
                "pin_code": "400001",
                "mobile_number": "9999999999",
                "declaration": "I confirm the above information is true.",
            },
        }
        r = requests.post(f"{BASE_URL}/api/voter/pdf", json=payload, timeout=60)
        assert r.status_code == 200, r.text
        assert "application/pdf" in r.headers.get("Content-Type", "")
        assert len(r.content) > 1000
