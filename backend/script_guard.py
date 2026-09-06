"""
Voice transcription script guard — catches the specific failure mode where
Whisper mislabels one Indian language's audio as a visually-similar sister
script (most commonly Telugu <-> Kannada, both derived from the old
Kadamba/Chalukya script and structurally similar to a speech model), so the
"We heard" confirmation always shows the WRONG language's text and the
legal search then runs against the wrong words — a silent wrong-citation
risk, not just a transcription inconvenience.

This does NOT block anything — Whisper's raw transcript is always returned.
It only ANNOTATES the response with a mismatch flag so the frontend's
existing "We heard" confirmation modal (the user already has to tap
"Correct — send" before anything is searched) can surface a clear warning
instead of silently letting a wrong-script transcript through unnoticed.

Applies to all 22 supported languages, not just Telugu/Kannada — mapped by
each language's actual Unicode script block.
"""
from __future__ import annotations

# (script_name, [(low, high), ...]) — Unicode code point ranges for each
# script block actually used by the app's 22 supported languages.
_SCRIPT_RANGES: dict[str, list[tuple[int, int]]] = {
    "devanagari": [(0x0900, 0x097F)],   # Hindi, Marathi, Nepali, Sanskrit, Konkani, Maithili, Dogri, Bodo, Kashmiri (as displayed in-app)
    "bengali": [(0x0980, 0x09FF)],       # Bengali, Assamese, Manipuri (as displayed in-app)
    "gurmukhi": [(0x0A00, 0x0A7F)],      # Punjabi
    "gujarati": [(0x0A80, 0x0AFF)],
    "oriya": [(0x0B00, 0x0B7F)],
    "tamil": [(0x0B80, 0x0BFF)],
    "telugu": [(0x0C00, 0x0C7F)],
    "kannada": [(0x0C80, 0x0CFF)],
    "malayalam": [(0x0D00, 0x0D7F)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F)],  # Urdu, Sindhi
    "olchiki": [(0x1C50, 0x1C7F)],       # Santali
    "latin": [(0x0041, 0x005A), (0x0061, 0x007A)],   # English
}

# Language code -> the script its transcript SHOULD be in.
LANGUAGE_EXPECTED_SCRIPT: dict[str, str] = {
    "en": "latin", "hi": "devanagari", "bn": "bengali", "ta": "tamil",
    "te": "telugu", "mr": "devanagari", "gu": "gujarati", "kn": "kannada",
    "ml": "malayalam", "pa": "gurmukhi", "or": "oriya", "as": "bengali",
    "ur": "arabic", "sd": "arabic", "ks": "devanagari", "ne": "devanagari",
    "sa": "devanagari", "kok": "devanagari", "mai": "devanagari",
    "mni": "bengali", "sat": "olchiki", "doi": "devanagari", "brx": "devanagari",
}

# Below this many script-bearing characters there's too little signal to
# judge reliably — a 2-3 character transcript (e.g. "no", "ok" mis-heard)
# would otherwise produce noisy false-positive warnings.
_MIN_LETTERS_TO_JUDGE = 6


def _script_of_char(ch: str) -> str | None:
    cp = ord(ch)
    for script, ranges in _SCRIPT_RANGES.items():
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return script
    return None


def detect_script(text: str) -> str | None:
    """Returns the script with the most characters in `text`, or None if no
    characters matched any known script (digits/punctuation/emoji only)."""
    counts: dict[str, int] = {}
    for ch in text:
        script = _script_of_char(ch)
        if script:
            counts[script] = counts.get(script, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def check_script_mismatch(text: str, language_code: str | None) -> dict:
    """Returns {mismatch, detected_script, expected_script}. `mismatch` is
    only ever True when there's enough text to judge AND the language has a
    known expected script AND the detected script actively disagrees —
    never flags on ambiguous/too-short transcripts or languages we can't
    map, so this can only add a helpful warning, never a false alarm on
    thin evidence."""
    expected = LANGUAGE_EXPECTED_SCRIPT.get((language_code or "").lower())
    if not expected or not text:
        return {"mismatch": False, "detected_script": None, "expected_script": expected}

    letter_count = sum(1 for ch in text if _script_of_char(ch))
    if letter_count < _MIN_LETTERS_TO_JUDGE:
        return {"mismatch": False, "detected_script": None, "expected_script": expected}

    detected = detect_script(text)
    mismatch = bool(detected and detected != expected)
    return {"mismatch": mismatch, "detected_script": detected, "expected_script": expected}
