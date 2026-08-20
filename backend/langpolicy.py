"""
Reply-language enforcement.

The prompt already SHOUTS the reply language, but a model still occasionally
answers a Hindi or Tamil question in English. For a user who does not read
English that is a total failure, so the server verifies the script of the
finished reply and repairs it deterministically instead of trusting the prompt.

Only script coverage is checked (cheap, offline, no model call). A repair
translation is attempted at most once, and only when the check fails — so the
normal path costs nothing extra.
"""

# Unicode ranges of the script each language is written in.
SCRIPT_RANGES = {
    "devanagari": [(0x0900, 0x097F)],
    "bengali": [(0x0980, 0x09FF)],
    "gurmukhi": [(0x0A00, 0x0A7F)],
    "gujarati": [(0x0A80, 0x0AFF)],
    "odia": [(0x0B00, 0x0B7F)],
    "tamil": [(0x0B80, 0x0BFF)],
    "telugu": [(0x0C00, 0x0C7F)],
    "kannada": [(0x0C80, 0x0CFF)],
    "malayalam": [(0x0D00, 0x0D7F)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
    "ol_chiki": [(0x1C50, 0x1C7F)],
    "meetei": [(0xABC0, 0xABFF)],
    "latin": [(0x0041, 0x005A), (0x0061, 0x007A)],
}

# ISO code (as used by LANGUAGES in server.py) → script
LANG_SCRIPT = {
    "en": "latin",
    "hi": "devanagari",
    "mr": "devanagari",
    "ne": "devanagari",
    "sa": "devanagari",
    "kok": "devanagari",
    "doi": "devanagari",
    "mai": "devanagari",
    "brx": "devanagari",
    "bn": "bengali",
    "as": "bengali",
    "mni": "bengali",  # Manipuri is published in Bengali script by the Government of India
    "pa": "gurmukhi",
    "gu": "gujarati",
    "or": "odia",
    "ta": "tamil",
    "te": "telugu",
    "kn": "kannada",
    "ml": "malayalam",
    "ur": "arabic",
    "ks": "arabic",
    "sd": "arabic",
    "sat": "ol_chiki",
}

# Below this share of target-script letters the reply is treated as "wrong
# language". Acronyms (FIR, RTI, PIO) and numbers are allowed to stay in Latin,
# so the bar is deliberately not near 1.0.
MIN_SCRIPT_RATIO = 0.35


def _in_ranges(ch: str, ranges) -> bool:
    o = ord(ch)
    return any(lo <= o <= hi for lo, hi in ranges)


def script_ratio(text: str, script: str) -> float:
    """Share of alphabetic characters that belong to `script`."""
    ranges = SCRIPT_RANGES.get(script)
    if not ranges or not text:
        return 1.0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    hits = sum(1 for c in letters if _in_ranges(c, ranges))
    return hits / len(letters)


def needs_language_repair(text: str, lang_code: str) -> bool:
    """True when a non-English reply came back in the wrong script."""
    code = (lang_code or "en").split("-")[0].lower()
    if code == "en":
        return False
    script = LANG_SCRIPT.get(code)
    if not script or script == "latin":
        # Unknown or Latin-script language (e.g. Konkani in Roman) — the script
        # test cannot tell us anything, so do not spend a repair call.
        return False
    if not text or len(text.strip()) < 20:
        return False
    return script_ratio(text, script) < MIN_SCRIPT_RATIO


def repair_prompt(language_display: str) -> str:
    """System prompt for the one-shot repair translation."""
    return (
        f"You are a translator. Rewrite the user's text COMPLETELY in {language_display}, "
        f"using the {language_display} script, keeping the same meaning, the same line breaks "
        "and the same bullet structure. Keep widely-used acronyms (FIR, RTI, PIO, POSH, SP) and "
        "numbers as they are. Do NOT add section numbers, article numbers or any statutory "
        "citation. Do NOT add commentary. Output only the rewritten text."
    )
