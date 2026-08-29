"""
SSE endpoint test for §66A (dead law + JI warning) and §377 (JI-only, no text).
Uses real HTTP calls against the running backend via the same connection path as
the mobile app.

Usage: python3 test_sse_guards.py
"""
import json
import requests
import sys

BASE = "http://localhost:8001"

def get_token():
    resp = requests.post(
        f"{BASE}/api/auth/login",
        json={"email": "protest@gandhikar.in", "password": "test1234"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def stream_query(token: str, message: str, label: str):
    """Send a chat query and parse the SSE stream. Returns list of frames."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"Query: {message!r}")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    payload = {
        "message": message,
        "mode": "basic",
        "language": "en",
        "language_name": "English",
        "session_id": None,
    }

    frames = []
    citation_frames = []
    delta_text = ""
    final_text = ""

    with requests.post(
        f"{BASE}/api/chat/stream",
        headers=headers,
        json=payload,
        stream=True,
        timeout=60,
    ) as resp:
        resp.raise_for_status()
        buffer = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            buffer += chunk
            while "\n\n" in buffer:
                event, buffer = buffer.split("\n\n", 1)
                for line in event.splitlines():
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        try:
                            obj = json.loads(raw)
                            frames.append(obj)
                            t = obj.get("type", "")
                            if t == "citation":
                                citation_frames.append(obj["citation"])
                            elif t == "delta":
                                delta_text += obj.get("content", "")
                            elif t == "final":
                                final_text = obj.get("content", "")
                        except json.JSONDecodeError:
                            pass

    display_text = final_text or delta_text

    # ── Print SSE frame summary ──────────────────────────────────────────────
    frame_types = [f.get("type") for f in frames]
    print(f"\nSSE frames in order: {frame_types}")

    print(f"\n── CITATION frames ({len(citation_frames)}) ──")
    for i, c in enumerate(citation_frames):
        print(f"\n  [{i+1}] key:          {c.get('key')}")
        print(f"       short_label:  {c.get('short_label')}")
        print(f"       verified_at:  {c.get('verified_at')}")
        print(f"       is_dead_law:  {c.get('is_dead_law')}")
        print(f"       no_current_text: {c.get('no_current_text', False)}")
        ot = c.get("official_text", "")
        print(f"       official_text (first 300):")
        print(f"       {ot[:300]!r}")

    # Guard check: in citation SSE, warning must come BEFORE statutory text
    print(f"\n── GUARD CHECK ──")
    for i, c in enumerate(citation_frames):
        ot = c.get("official_text") or ""
        dw = c.get("dead_warning") or ""
        jf = c.get("judicial_flag") or ""

        has_warning = bool(dw or jf)
        warning_in_ot = bool(dw and dw in ot) or bool(jf and jf in ot)
        
        # For §66A: dead_warning + judicial_flag must appear before the law text
        # For §377: judicial_flag must appear with no_current_text notice
        if c.get("is_dead_law") or c.get("judicial_flag") or c.get("no_current_text"):
            if warning_in_ot:
                print(f"  ✅ [{i+1}] Warning present in official_text (prepended before statutory text)")
            elif has_warning:
                print(f"  ⚠️  [{i+1}] Warning in citation fields but NOT in official_text")
            else:
                print(f"  ❌ [{i+1}] No safety warning found in citation")

    print(f"\n── LLM RESPONSE (first 400 chars) ──")
    print(repr(display_text[:400]))

    print(f"\n── STREAM ORDER CHECK ──")
    # Citations must appear before any 'delta' frame
    first_citation_idx = next((i for i, f in enumerate(frames) if f.get("type") == "citation"), None)
    first_delta_idx = next((i for i, f in enumerate(frames) if f.get("type") == "delta"), None)
    if first_citation_idx is not None and first_delta_idx is not None:
        if first_citation_idx < first_delta_idx:
            print(f"  ✅ Citations (frame #{first_citation_idx}) arrive BEFORE first delta (frame #{first_delta_idx})")
        else:
            print(f"  ❌ Citations (frame #{first_citation_idx}) arrive AFTER first delta (frame #{first_delta_idx})")
    elif first_citation_idx is None:
        print("  ❌ No citation frames received")
    elif first_delta_idx is None:
        print("  (No delta frames — may be a refusal)")
        refusal_deltas = [f for f in frames if f.get("type") == "delta"]
        if refusal_deltas:
            print(f"  Refusal text: {refusal_deltas[0].get('content','')[:200]}")

    return frames


if __name__ == "__main__":
    print("Getting auth token...")
    try:
        token = get_token()
        print(f"✅ Token obtained")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)

    # Test 1: IT Act §66A — dead law + STRUCK_DOWN
    frames_66a = stream_query(token, "What is IT Act section 66A", "IT Act §66A (dead law + STRUCK_DOWN)")

    # Test 2: IPC §377 — no section text, READ_DOWN JI
    frames_377 = stream_query(token, "Tell me about IPC section 377", "IPC §377 (no corpus text, READ_DOWN JI)")

    print("\n\n══ P0 SSE VERIFICATION COMPLETE ══")
