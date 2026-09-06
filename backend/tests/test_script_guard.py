"""
Unit tests for backend/script_guard.py — the Whisper mis-transcription
script-mismatch detector (Telugu <-> Kannada bug fix).

These are pure unit tests (no network / no server) since real audio ->
Whisper mis-transcription cannot be reproduced in this environment.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from script_guard import check_script_mismatch, detect_script  # noqa: E402


class TestDetectScript:
    def test_telugu_text(self):
        assert detect_script("నమస్కారం") == "telugu"

    def test_kannada_text(self):
        assert detect_script("ನಮಸ್ಕಾರ") == "kannada"

    def test_hindi_text(self):
        assert detect_script("नमस्ते कैसे हैं आप") == "devanagari"

    def test_english_text(self):
        assert detect_script("hello how are you") == "latin"

    def test_empty_text_returns_none(self):
        assert detect_script("123 !!! ") is None


class TestCheckScriptMismatch:
    def test_telugu_selected_kannada_detected_is_mismatch(self):
        # Simulates the exact reported bug: Telugu selected, Whisper
        # mis-transcribes into Kannada script.
        kannada_text = "ನಮಸ್ಕಾರ ಹೇಗಿದ್ದೀರಿ ಸ್ವಾಗತ"
        result = check_script_mismatch(kannada_text, "te")
        assert result["mismatch"] is True
        assert result["detected_script"] == "kannada"
        assert result["expected_script"] == "telugu"

    def test_telugu_selected_telugu_detected_no_mismatch(self):
        telugu_text = "నమస్కారం మీరు ఎలా ఉన్నారు స్వాగతం"
        result = check_script_mismatch(telugu_text, "te")
        assert result["mismatch"] is False
        assert result["detected_script"] == "telugu"
        assert result["expected_script"] == "telugu"

    def test_hindi_selected_hindi_detected_no_mismatch(self):
        hindi_text = "नमस्ते आप कैसे हैं आपका स्वागत है"
        result = check_script_mismatch(hindi_text, "hi")
        assert result["mismatch"] is False
        assert result["detected_script"] == "devanagari"

    def test_hindi_selected_english_detected_is_mismatch(self):
        result = check_script_mismatch("hello how are you doing today", "hi")
        assert result["mismatch"] is True
        assert result["detected_script"] == "latin"
        assert result["expected_script"] == "devanagari"

    def test_english_selected_english_detected_no_mismatch(self):
        result = check_script_mismatch("hello how are you doing today", "en")
        assert result["mismatch"] is False
        assert result["detected_script"] == "latin"

    def test_short_transcript_never_flagged_even_if_wrong_script(self):
        # < 6 script-bearing chars — should never be flagged, avoid
        # false positives on short utterances like "no"/"ok".
        short_kannada = "ಹಾಯ್"  # 4 chars
        result = check_script_mismatch(short_kannada, "te")
        assert result["mismatch"] is False
        assert result["detected_script"] is None

    def test_empty_text_no_mismatch(self):
        result = check_script_mismatch("", "te")
        assert result["mismatch"] is False
        assert result["detected_script"] is None

    def test_unmapped_language_code_no_mismatch(self):
        result = check_script_mismatch("ನಮಸ್ಕಾರ ಹೇಗಿದ್ದೀರಿ ಸ್ವಾಗತ", "xx")
        assert result["mismatch"] is False
        assert result["expected_script"] is None

    def test_none_language_code_no_mismatch(self):
        result = check_script_mismatch("ನಮಸ್ಕಾರ ಹೇಗಿದ್ದೀರಿ ಸ್ವಾಗತ", None)
        assert result["mismatch"] is False

    def test_tamil_selected_malayalam_detected_is_mismatch(self):
        malayalam_text = "നമസ്കാരം സുഖമാണോ സ്വാഗതം"
        result = check_script_mismatch(malayalam_text, "ta")
        assert result["mismatch"] is True
        assert result["detected_script"] == "malayalam"

    def test_marathi_and_hindi_share_devanagari_no_mismatch(self):
        # Marathi and Hindi both map to devanagari — should not falsely
        # flag even though they're different languages.
        devanagari_text = "नमस्कार तुम्ही कसे आहात"
        result = check_script_mismatch(devanagari_text, "mr")
        assert result["mismatch"] is False
        assert result["detected_script"] == "devanagari"

    def test_urdu_arabic_script_no_mismatch(self):
        urdu_text = "السلام علیکم آپ کیسے ہیں"
        result = check_script_mismatch(urdu_text, "ur")
        assert result["mismatch"] is False
        assert result["detected_script"] == "arabic"

    def test_boundary_exactly_min_letters_is_judged(self):
        # Exactly 6 telugu chars selected as kannada expectation -> should judge
        telugu_text = "నమస్కా"  # 6 chars
        result = check_script_mismatch(telugu_text, "kn")
        assert result["detected_script"] == "telugu"
        assert result["mismatch"] is True

    def test_five_chars_below_threshold_not_judged(self):
        telugu_text = "నమస్క"  # 5 chars
        result = check_script_mismatch(telugu_text, "kn")
        assert result["mismatch"] is False
        assert result["detected_script"] is None
