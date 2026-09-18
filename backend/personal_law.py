"""
Personal-law disambiguation — marriage/divorce/maintenance/custody and
inheritance/succession questions in India are governed by DIFFERENT Acts
depending on the parties' religion (or whether the marriage is civil /
inter-religious). Answering under the wrong one would be a WRONG CITATION —
the one thing this app must never do (see corpus.py's citation-integrity
rule).

This module operates on plain text only — no new SSE frame type, no
frontend changes. It reuses the EXISTING `early_refusal` mechanism already
wired in server.py's chat_stream (a canned message is streamed as a normal
chat bubble, the LLM/retrieval is skipped for that turn) — the same pattern
already used for REFUSAL_NO_CORPUS / REFUSAL_NON_INDIAN / REFUSAL_NOT_LEGAL.

Flow:
  1. classify_personal_law_topic() — is this question about marriage/family
     law, or succession/inheritance law, at all?
  2. detect_context() — did the question already name a religion / Act /
     marriage-type, so we already know which Act applies?
  3. If (1) is true and (2) finds nothing (and the chat session hasn't
     already resolved this topic earlier), chat_stream asks a plain-language
     clarifying question INSTEAD of guessing.
  4. Once a context is known — either from the original question or a
     session-remembered choice — act_hint_phrase() returns a short Act-name
     phrase that server.py silently appends to the retrieval text (never
     shown to the user), so the EXISTING `_ACT_HINTS` matcher in
     corpus_db.py biases retrieval toward the correct Act. No new retrieval
     machinery, no new database, no new SSE frame.
"""
from __future__ import annotations

import re

# ── Topic detection ──────────────────────────────────────────────────────
_MARRIAGE_TOPIC_RE = re.compile(
    r"register\s+(?:my|our|the)?\s*marriage|marriage\s+registration|"
    r"\bdivorce\b|\balimony\b|maintenance\s+(?:after|from)\s+(?:my\s+)?(?:husband|wife|spouse)|"
    r"child\s+custody|judicial\s+separation|\bannul(?:ment|)\b|"
    r"grounds?\s+for\s+divorce|mutual\s+divorce|file\s+for\s+divorce|"
    r"dissolve\s+(?:my|our|the)?\s*marriage|marriage\s+certificate|"
    r"court\s+marriage|marry\s+(?:legally|officially)",
    re.I,
)
_SUCCESSION_TOPIC_RE = re.compile(
    r"\binheritance\b|\binherit\b|\binherits?\b|\bsuccession\b|ancestral\s+property|"
    r"legal\s+heir|property\s+after\s+(?:death|dying|he\s+dies|she\s+dies)|"
    r"\bwill\b.{0,20}\bproperty\b|intestate|coparcenary|"
    r"share\s+in\s+(?:my\s+)?father|who\s+gets?\s+the\s+property|division\s+of\s+property",
    re.I,
)

# ── Religion / marriage-type context detection ──────────────────────────
# Each context maps to a short Act-name phrase per topic. That phrase is
# what gets silently appended to the retrieval text — it must be a phrase
# the existing corpus_db._ACT_HINTS table already recognises.
_CONTEXTS: dict[str, dict] = {
    "hindu": {
        "pattern": re.compile(r"\bhindu\b|\bbuddhist\b|\bjain\b|\bsikh\b", re.I),
        "marriage_hint": "Hindu Marriage Act",
        "succession_hint": "Hindu Succession Act",
        "label": "Hindu, Buddhist, Jain or Sikh",
    },
    "special": {
        "pattern": re.compile(
            r"inter.?religious|inter.?caste|inter.?faith|civil\s+marriage|"
            r"court\s+marriage|special\s+marriage|different\s+religion",
            re.I,
        ),
        "marriage_hint": "Special Marriage Act",
        "succession_hint": None,  # civil/inter-religious marriage alone doesn't fix succession law
        "label": "inter-religious / civil / court marriage",
    },
    "muslim": {
        "pattern": re.compile(r"\bmuslim\b|\bislam(?:ic)?\b|\bnikah\b|\bshariat?\b|\bshariah\b", re.I),
        "marriage_hint": "Dissolution of Muslim Marriages Act",
        "succession_hint": "Muslim Personal Law",
        "label": "Muslim personal law",
    },
    "christian_parsi": {
        "pattern": re.compile(r"\bchristian\b|\bcatholic\b|\bparsi\b", re.I),
        "marriage_hint": "Indian Christian Marriage Act",
        "succession_hint": "Indian Succession Act",
        "label": "Christian or Parsi",
    },
}

# ── Translations for disambiguation question and disclaimer ──────────────
# Keyed by ISO language code (matches LANGUAGES list in server.py).
# Each entry: {"marriage": "...", "succession": "...", "disclaimer": "..."}
# {label} in disclaimer is replaced at runtime with the context label.
_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "marriage": (
            "Marriage, divorce and maintenance are governed by different laws "
            "depending on the couple's religion or how they married — the exact "
            "rule (and section) differs under each. To give you the correct one, "
            "could you tell me: are you Hindu, Buddhist, Jain or Sikh; did you "
            "marry (or want to marry) under a civil / inter-religious / court "
            "marriage; are you Muslim; or are you Christian or Parsi?"
        ),
        "succession": (
            "Inheritance and succession are governed by different laws depending "
            "on the deceased's religion — the exact rule differs under each. To "
            "give you the correct one, could you tell me: was the person Hindu, "
            "Buddhist, Jain or Sikh; Muslim; or Christian or Parsi?"
        ),
        "disclaimer": (
            "(This answer is based on {label} personal law. If your situation is "
            "different, the applicable law — and section — will differ.)"
        ),
    },
    "hi": {
        "marriage": (
            "विवाह, तलाक और गुज़ारा-भत्ता अलग-अलग कानूनों से तय होते हैं — यह दंपती के "
            "धर्म या विवाह के प्रकार पर निर्भर करता है। सही कानून बताने के लिए कृपया बताएं: "
            "क्या आप हिन्दू, बौद्ध, जैन या सिख हैं; क्या आपका विवाह अंतर-धार्मिक / सिविल / "
            "कोर्ट मैरिज के तहत हुआ है या होना है; क्या आप मुस्लिम हैं; "
            "या क्या आप ईसाई या पारसी हैं?"
        ),
        "succession": (
            "उत्तराधिकार और विरासत के कानून मृतक के धर्म पर निर्भर करते हैं — हर धर्म के लिए "
            "अलग नियम हैं। सही जानकारी के लिए बताएं: क्या वह व्यक्ति हिन्दू, बौद्ध, जैन या "
            "सिख था; मुस्लिम था; या ईसाई या पारसी था?"
        ),
        "disclaimer": (
            "(यह उत्तर {label} व्यक्तिगत कानून पर आधारित है। यदि आपकी स्थिति अलग है, "
            "तो लागू कानून और धारा भिन्न होगी।)"
        ),
    },
    "bn": {
        "marriage": (
            "বিবাহ, বিবাহ-বিচ্ছেদ ও ভরণপোষণ আলাদা আইন দ্বারা নিয়ন্ত্রিত — দম্পতির ধর্ম বা "
            "বিবাহের ধরনের উপর নির্ভর করে সঠিক বিধান ভিন্ন। সঠিক আইন জানাতে বলুন: আপনি কি "
            "হিন্দু, বৌদ্ধ, জৈন বা শিখ; আন্তঃধর্মীয় / সিভিল / কোর্ট বিবাহ করেছেন বা "
            "করতে চান; আপনি কি মুসলিম; নাকি আপনি খ্রিস্টান বা পার্সি?"
        ),
        "succession": (
            "উত্তরাধিকার ও সম্পত্তি বণ্টনের আইন মৃত ব্যক্তির ধর্মের উপর নির্ভর করে। "
            "সঠিক তথ্যের জন্য জানান: সেই ব্যক্তি কি হিন্দু, বৌদ্ধ, জৈন বা শিখ ছিলেন; "
            "মুসলিম ছিলেন; নাকি খ্রিস্টান বা পার্সি ছিলেন?"
        ),
        "disclaimer": (
            "(এই উত্তরটি {label} ব্যক্তিগত আইনের উপর ভিত্তি করে। আপনার পরিস্থিতি "
            "ভিন্ন হলে প্রযোজ্য আইন ও ধারা আলাদা হবে।)"
        ),
    },
    "ta": {
        "marriage": (
            "திருமணம், விவாகரத்து, ஜீவனாம்சம் — தம்பதியரின் மதம் அல்லது திருமண வகையைப் "
            "பொறுத்து வெவ்வேறு சட்டங்கள் பொருந்தும். சரியான சட்டம் கூற, தெரிவிக்கவும்: "
            "நீங்கள் இந்து, பௌத்தர், ஜைனர் அல்லது சீக்கியரா; சிவில் / இடைமத / நீதிமன்ற "
            "திருமணமா; முஸ்லிமா; அல்லது கிறிஸ்தவர் அல்லது பார்சியா?"
        ),
        "succession": (
            "மரபுரிமை, வாரிசு உரிமை — மறைந்தவரின் மதத்தைப் பொறுத்து சட்டங்கள் மாறுபடும். "
            "சரியான தகவல் தர கூறுங்கள்: அந்த நபர் இந்து, பௌத்தர், ஜைனர் அல்லது சீக்கியரா; "
            "முஸ்லிமா; அல்லது கிறிஸ்தவர் அல்லது பார்சியா?"
        ),
        "disclaimer": (
            "(இந்த பதில் {label} தனிநபர் சட்டத்தை அடிப்படையாகக் கொண்டது. "
            "உங்கள் சூழ்நிலை வேறாக இருந்தால், பொருந்தும் சட்டமும் பிரிவும் மாறுபடும்.)"
        ),
    },
    "te": {
        "marriage": (
            "వివాహం, విడాకులు, భరణం — దంపతుల మతం లేదా వివాహ రకాన్ని బట్టి వేర్వేరు "
            "చట్టాలు వర్తిస్తాయి. సరైన చట్టం చెప్పడానికి తెలపండి: మీరు హిందూ, బౌద్ధ, "
            "జైన లేదా సిక్కా; అంతర్మత / సివిల్ / కోర్టు వివాహమా; ముస్లింనా; "
            "లేదా క్రైస్తవ లేదా పారసీనా?"
        ),
        "succession": (
            "వారసత్వం, ఆస్తి పంపిణీ — మృతుని మతాన్ని బట్టి చట్టాలు మారుతాయి. "
            "సరైన సమాచారం కోసం చెప్పండి: ఆ వ్యక్తి హిందూ, బౌద్ధ, జైన లేదా సిక్కా; "
            "ముస్లింనా; లేదా క్రైస్తవ లేదా పారసీనా?"
        ),
        "disclaimer": (
            "({label} వ్యక్తిగత చట్టం ఆధారంగా ఈ సమాధానం ఉంది. మీ పరిస్థితి "
            "భిన్నంగా ఉంటే, వర్తించే చట్టం మరియు సెక్షన్ భిన్నంగా ఉంటాయి.)"
        ),
    },
    "mr": {
        "marriage": (
            "विवाह, घटस्फोट आणि पोटगी वेगवेगळ्या कायद्यांद्वारे नियंत्रित केली जातात — "
            "हे जोडप्याच्या धर्मावर किंवा विवाहाच्या प्रकारावर अवलंबून असते. योग्य माहिती "
            "देण्यासाठी सांगा: तुम्ही हिंदू, बौद्ध, जैन किंवा शीख आहात का; "
            "आंतरधर्मीय / नागरी / न्यायालयीन विवाह आहे का; तुम्ही मुस्लिम आहात का; "
            "किंवा तुम्ही ख्रिश्चन किंवा पारशी आहात का?"
        ),
        "succession": (
            "वारसाहक्क आणि उत्तराधिकार कायदे मृत व्यक्तीच्या धर्मावर अवलंबून असतात. "
            "अचूक माहितीसाठी सांगा: ती व्यक्ती हिंदू, बौद्ध, जैन किंवा शीख होती का; "
            "मुस्लिम होती का; किंवा ख्रिश्चन किंवा पारशी होती का?"
        ),
        "disclaimer": (
            "(हे उत्तर {label} वैयक्तिक कायद्यावर आधारित आहे. जर तुमची परिस्थिती "
            "वेगळी असेल, तर लागू कायदा आणि कलम वेगळे असतील.)"
        ),
    },
    "gu": {
        "marriage": (
            "લગ્ન, છૂટાછેડા અને ભરણ-પોષણ અલગ-અલગ કાયદા દ્વારા નિયંત્રિત થાય છે — "
            "આ દંપतीના ધર્મ કે લગ્નના પ્રકાર પર આધાર રાખે છે. સાચી જાણકારી આપવા "
            "જણાવો: શું તમે હિન્દુ, બૌદ્ધ, જૈન કે શીખ છો; આંતર-ધર્મીય / સિવિલ / "
            "કોર્ટ મેરેજ છે; શું તમે મુસ્લિમ છો; કે ખ્રિસ્તી અથવા પારસી છો?"
        ),
        "succession": (
            "વારસો અને ઉત્તરાધિકાર અલગ-અલગ કાયદા દ્વારા નિર્ધારિત થાય છે — "
            "આ મૃતકના ધર્મ પર આધારિત છે. સાચી માહિતી માટે જણાવો: "
            "તે વ્યક્તિ હિન્દુ, બૌદ્ધ, જૈન કે શીખ હતી; "
            "મુસ્લિમ હતી; કે ખ્રિસ્તી અથવા પારસી હતી?"
        ),
        "disclaimer": (
            "(આ જવાબ {label} વ્યક્તિગત કાયદા પર આધારિત છે. "
            "જો તમારી પરિસ્થિતિ અલગ હોય, તો લાગુ કાયદો અને કલમ અલગ હશે.)"
        ),
    },
    "kn": {
        "marriage": (
            "ವಿವಾಹ, ವಿಚ್ಛೇದನ ಮತ್ತು ಜೀವನಾಂಶ — ದಂಪತಿಗಳ ಧರ್ಮ ಅಥವಾ ವಿವಾಹದ ವಿಧ "
            "ಅನುಸಾರ ವಿಭಿನ್ನ ಕಾನೂನುಗಳು ಅನ್ವಯಿಸುತ್ತವೆ. ಸರಿಯಾದ ಕಾನೂನು ತಿಳಿಸಲು "
            "ಹೇಳಿ: ನೀವು ಹಿಂದೂ, ಬೌದ್ಧ, ಜೈನ ಅಥವಾ ಸಿಖ್ ಆಗಿದ್ದೀರಾ; "
            "ಅಂತರ-ಧಾರ್ಮಿಕ / ಸಿವಿಲ್ / ಕೋರ್ಟ್ ವಿವಾಹವೇ; ಮುಸ್ಲಿಮರೇ; "
            "ಅಥವಾ ಕ್ರಿಶ್ಚಿಯನ್ ಅಥವಾ ಪಾರ್ಸಿಯೇ?"
        ),
        "succession": (
            "ಉತ್ತರಾಧಿಕಾರ ಮತ್ತು ಆಸ್ತಿ ವಿಭಜನೆ ಕಾನೂನುಗಳು ಮೃತರ ಧರ್ಮವನ್ನು "
            "ಆಧರಿಸಿ ಭಿನ್ನವಾಗಿರುತ್ತವೆ. ಸರಿಯಾದ ಮಾಹಿತಿಗಾಗಿ ಹೇಳಿ: "
            "ಆ ವ್ಯಕ್ತಿ ಹಿಂದೂ, ಬೌದ್ಧ, ಜೈನ ಅಥವಾ ಸಿಖ್ ಆಗಿದ್ದರೇ; "
            "ಮುಸ್ಲಿಮರಾಗಿದ್ದರೇ; ಅಥವಾ ಕ್ರಿಶ್ಚಿಯನ್ ಅಥವಾ ಪಾರ್ಸಿಯಾಗಿದ್ದರೇ?"
        ),
        "disclaimer": (
            "({label} ವೈಯಕ್ತಿಕ ಕಾನೂನನ್ನು ಆಧರಿಸಿ ಈ ಉತ್ತರ ನೀಡಲಾಗಿದೆ. "
            "ನಿಮ್ಮ ಪರಿಸ್ಥಿತಿ ಭಿನ್ನವಾಗಿದ್ದರೆ, ಅನ್ವಯಿಸಬೇಕಾದ ಕಾನೂನು ಮತ್ತು ವಿಭಾಗ ಭಿನ್ನವಾಗಿರುತ್ತದೆ.)"
        ),
    },
    "ml": {
        "marriage": (
            "വിവാഹം, വിവാഹമോചനം, ജീവനാംശം — ദമ്പതികളുടെ മതത്തെ അല്ലെങ്കിൽ "
            "വിവാഹ രീതിയെ ആശ്രയിച്ച് വ്യത്യസ്ത നിയമങ്ങൾ ബാധകമാണ്. "
            "ശരിയായ നിയമം അറിയിക്കാൻ പറയൂ: "
            "നിങ്ങൾ ഹിന്ദു, ബൗദ്ധ, ജൈന അല്ലെങ്കിൽ സിഖ് ആണോ; "
            "ഇന്റർ-റിലിജ്യസ് / സിവിൽ / കോടതി വിവാഹം ആണോ; "
            "മുസ്‌ലിം ആണോ; അതോ ക്രിസ്ത്യൻ അല്ലെങ്കിൽ പാർസി ആണോ?"
        ),
        "succession": (
            "അനന്തരാവകാശം, ഉത്തരാധികാരം — മരിച്ചയാളുടെ മതത്തെ ആശ്രയിച്ച് "
            "നിയമങ്ങൾ വ്യത്യാസപ്പെടും. ശരിയായ ഉത്തരം ലഭിക്കാൻ പറയൂ: "
            "ആ വ്യക്തി ഹിന്ദു, ബൗദ്ധ, ജൈന അല്ലെങ്കിൽ സിഖ് ആണോ; "
            "മുസ്‌ലിം ആണോ; അതോ ക്രിസ്ത്യൻ അല്ലെങ്കിൽ പാർസി ആണോ?"
        ),
        "disclaimer": (
            "({label} വ്യക്തിഗത നിയമത്തെ ആധാരമാക്കിയുള്ളതാണ് ഈ ഉത്തരം. "
            "നിങ്ങളുടെ സ്ഥിതി വ്യത്യസ്തമാണെങ്കിൽ, ബാധകമായ നിയമവും വകുപ്പും വ്യത്യാസപ്പെടും.)"
        ),
    },
    "pa": {
        "marriage": (
            "ਵਿਆਹ, ਤਲਾਕ ਅਤੇ ਗੁਜ਼ਾਰਾ-ਭੱਤਾ ਵੱਖ-ਵੱਖ ਕਾਨੂੰਨਾਂ ਦੁਆਰਾ ਨਿਯੰਤ੍ਰਿਤ ਹੁੰਦੇ ਹਨ — "
            "ਇਹ ਜੋੜੇ ਦੇ ਧਰਮ ਜਾਂ ਵਿਆਹ ਦੀ ਕਿਸਮ 'ਤੇ ਨਿਰਭਰ ਕਰਦਾ ਹੈ। "
            "ਸਹੀ ਜਾਣਕਾਰੀ ਦੇਣ ਲਈ ਦੱਸੋ: ਕੀ ਤੁਸੀਂ ਹਿੰਦੂ, ਬੋਧੀ, ਜੈਨ ਜਾਂ ਸਿੱਖ ਹੋ; "
            "ਕੀ ਅੰਤਰ-ਧਰਮੀ / ਸਿਵਲ / ਕੋਰਟ ਮੈਰਿਜ ਹੈ; "
            "ਕੀ ਤੁਸੀਂ ਮੁਸਲਮਾਨ ਹੋ; ਜਾਂ ਕੀ ਤੁਸੀਂ ਈਸਾਈ ਜਾਂ ਪਾਰਸੀ ਹੋ?"
        ),
        "succession": (
            "ਵਿਰਾਸਤ ਅਤੇ ਉੱਤਰਾਧਿਕਾਰ ਦੇ ਕਾਨੂੰਨ ਮ੍ਰਿਤਕ ਦੇ ਧਰਮ ਅਨੁਸਾਰ ਵੱਖ-ਵੱਖ ਹੁੰਦੇ ਹਨ। "
            "ਸਹੀ ਜਾਣਕਾਰੀ ਲਈ ਦੱਸੋ: ਕੀ ਉਹ ਵਿਅਕਤੀ ਹਿੰਦੂ, ਬੋਧੀ, ਜੈਨ ਜਾਂ ਸਿੱਖ ਸੀ; "
            "ਮੁਸਲਮਾਨ ਸੀ; ਜਾਂ ਈਸਾਈ ਜਾਂ ਪਾਰਸੀ ਸੀ?"
        ),
        "disclaimer": (
            "(ਇਹ ਜਵਾਬ {label} ਨਿੱਜੀ ਕਾਨੂੰਨ 'ਤੇ ਆਧਾਰਿਤ ਹੈ। "
            "ਜੇ ਤੁਹਾਡੀ ਸਥਿਤੀ ਵੱਖਰੀ ਹੈ, ਤਾਂ ਲਾਗੂ ਕਾਨੂੰਨ ਅਤੇ ਧਾਰਾ ਵੱਖਰੀ ਹੋਵੇਗੀ।)"
        ),
    },
    "or": {
        "marriage": (
            "ବିବାହ, ବିବାହ ବିଚ୍ଛେଦ ଏବଂ ଭରଣପୋଷଣ — ଦମ୍ପତୀଙ୍କ ଧର୍ମ ବା ବିବାହ ପ୍ରକାର "
            "ଅନୁଯାୟୀ ଭିନ୍ନ ଆଇନ ଲାଗୁ ହୁଏ। ସଠିକ ତଥ୍ୟ ଦେବା ପାଇଁ ଜଣାନ୍ତୁ: "
            "ଆପଣ ହିନ୍ଦୁ, ବୌଦ୍ଧ, ଜୈନ ବା ଶିଖ ଅଟନ୍ତି କି; "
            "ଅନ୍ତର-ଧର୍ମୀୟ / ସିଭିଲ / କୋର୍ଟ ବିବାହ ହୋଇଛି କି; "
            "ଆପଣ ମୁସଲମାନ ଅଟନ୍ତି କି; ବା ଆପଣ ଖ୍ରୀଷ୍ଟିଆନ ବା ପାର୍ସୀ ଅଟନ୍ତି କି?"
        ),
        "succession": (
            "ଉତ୍ତରାଧିକାର ଏବଂ ସମ୍ପତ୍ତି ବଣ୍ଟନ ଆଇନ ମୃତ ବ୍ୟକ୍ତିଙ୍କ ଧର୍ମ ଉପରେ ନିର୍ଭର କରେ। "
            "ସଠିକ ତଥ୍ୟ ପାଇଁ ଜଣାନ୍ତୁ: ଉକ୍ତ ବ୍ୟକ୍ତି ହିନ୍ଦୁ, ବୌଦ୍ଧ, ଜୈନ ବା ଶିଖ ଥିଲେ କି; "
            "ମୁସଲମାନ ଥିଲେ କି; ବା ଖ୍ରୀଷ୍ଟିଆନ ବା ପାର୍ସୀ ଥିଲେ କି?"
        ),
        "disclaimer": (
            "(ଏହି ଉତ୍ତର {label} ବ୍ୟକ୍ତିଗତ ଆଇନ ଉପରେ ଆଧାରିତ। "
            "ଯଦି ଆପଣଙ୍କ ପରିସ୍ଥିତି ଭିନ୍ନ, ଲାଗୁ ଆଇନ ଏବଂ ଧାରା ଭିନ୍ନ ହେବ।)"
        ),
    },
    "as": {
        "marriage": (
            "বিবাহ, বিবাহ-বিচ্ছেদ আৰু ভৰণপোষণ বেলেগ বেলেগ আইনেৰে নিয়ন্ত্ৰিত হয় — "
            "এই দম্পতিৰ ধৰ্ম বা বিবাহৰ ধৰণৰ ওপৰত নিৰ্ভৰ কৰে। "
            "সঠিক তথ্য দিবলৈ জনাওক: আপুনি হিন্দু, বৌদ্ধ, জৈন বা শিখ নে; "
            "আন্তঃধৰ্মীয় / দেৱানী / আদালত বিবাহ নে; "
            "আপুনি মুছলমান নে; বা আপুনি খ্ৰীষ্টান বা পাৰচি নে?"
        ),
        "succession": (
            "উত্তৰাধিকাৰ আৰু সম্পত্তি বিভাজনৰ আইন মৃত ব্যক্তিৰ ধৰ্মৰ ওপৰত নিৰ্ভৰ কৰে। "
            "সঠিক তথ্যৰ বাবে জনাওক: সেই ব্যক্তিজন হিন্দু, বৌদ্ধ, জৈন বা শিখ আছিল নে; "
            "মুছলমান আছিল নে; বা খ্ৰীষ্টান বা পাৰচি আছিল নে?"
        ),
        "disclaimer": (
            "(এই উত্তৰটো {label} ব্যক্তিগত আইনৰ ওপৰত আধাৰিত। "
            "যদি আপোনাৰ পৰিস্থিতি বেলেগ হয়, তেন্তে প্ৰযোজ্য আইন আৰু ধাৰা বেলেগ হ'ব।)"
        ),
    },
    "ur": {
        "marriage": (
            "نکاح، طلاق اور نفقہ — مختلف مذاہب یا شادی کی نوعیت کے مطابق الگ الگ قانون لاگو ہوتے ہیں۔ "
            "درست قانون بتانے کے لیے بتائیں: کیا آپ ہندو، بدھسٹ، جین یا سکھ ہیں؛ "
            "کیا آنتر مذہبی / سول / کورٹ میریج ہے؛ کیا آپ مسلمان ہیں؛ "
            "یا کیا آپ عیسائی یا پارسی ہیں؟"
        ),
        "succession": (
            "وراثت اور جانشینی کے قوانین مرحوم کے مذہب کے مطابق مختلف ہوتے ہیں۔ "
            "درست معلومات کے لیے بتائیں: کیا وہ شخص ہندو، بدھسٹ، جین یا سکھ تھا؛ "
            "مسلمان تھا؛ یا عیسائی یا پارسی تھا؟"
        ),
        "disclaimer": (
            "(یہ جواب {label} ذاتی قانون پر مبنی ہے۔ "
            "اگر آپ کی صورتحال مختلف ہو تو متعلقہ قانون اور دفعہ مختلف ہوگی۔)"
        ),
    },
    # ── Devanagari-script languages: Nepali, Sanskrit, Konkani, Maithili, Dogri, Bodo ──
    "ne": {
        "marriage": (
            "विवाह, सम्बन्ध-विच्छेद र भरणपोषण — दम्पतीको धर्म वा विवाहको प्रकारअनुसार "
            "फरक-फरक कानून लागू हुन्छन्। सही कानून बताउन भन्नुहोस्: "
            "के तपाईं हिन्दू, बौद्ध, जैन वा सिख हुनुहुन्छ; "
            "अन्तरधार्मिक / नागरिक / अदालती विवाह हो; "
            "के तपाईं मुस्लिम हुनुहुन्छ; वा के तपाईं इसाई वा पारसी हुनुहुन्छ?"
        ),
        "succession": (
            "उत्तराधिकार र सम्पत्ति बाँडफाँटका कानून मृतकको धर्मअनुसार फरक हुन्छन्। "
            "सही जानकारीका लागि भन्नुहोस्: के ती व्यक्ति हिन्दू, बौद्ध, जैन वा सिख थिए; "
            "मुस्लिम थिए; वा इसाई वा पारसी थिए?"
        ),
        "disclaimer": (
            "(यो उत्तर {label} व्यक्तिगत कानूनमा आधारित छ। "
            "यदि तपाईंको अवस्था फरक छ भने, लागू हुने कानून र दफा फरक हुनेछ।)"
        ),
    },
    "sa": {
        "marriage": (
            "विवाहः, विवाहविच्छेदः, पोषणं च — दम्पत्योः धर्मानुसारं विविधाः नियमाः प्रचलन्ति। "
            "उचितं नियमं ज्ञातुं वदतु: भवान् हिन्दुः, बौद्धः, जैनः वा शिखः किम्; "
            "अन्तरधार्मिकः / सिविलः / न्यायालयविवाहः किम्; "
            "भवान् मुस्लिमः किम्; अथवा भवान् ख्रिस्तियनः वा पारसिः किम्?"
        ),
        "succession": (
            "उत्तराधिकारः सम्पत्तिवितरणं च मृतस्य धर्मानुसारं भिन्नाः। "
            "उचितज्ञानाय वदतु: सः जनः हिन्दुः, बौद्धः, जैनः वा शिखः आसीत् किम्; "
            "मुस्लिमः आसीत् किम्; अथवा ख्रिस्तियनः वा पारसिः आसीत् किम्?"
        ),
        "disclaimer": (
            "({label} व्यक्तिगतकानूनाधारितम् इदम् उत्तरम्। "
            "यदि भवतः परिस्थितिः भिन्ना, तर्हि प्रयोज्यकानूनः धाराश्च भिन्नाः भविष्यन्ति।)"
        ),
    },
    # Konkani, Maithili, Dogri, Bodo — Devanagari, use Hindi-close wording
    "kok": {
        "marriage": (
            "लग्न, घटस्फोट आणि पोटगी वेगवेगळ्या कायद्यांनी नियंत्रित होतात — "
            "हे जोडप्याच्या धर्मावर वा लग्नाच्या प्रकारावर अवलंबून असते। "
            "योग्य माहिती दिवपाक सांगात: तुम्ही हिंदू, बौद्ध, जैन वा शीख आसात काय; "
            "आंतरधर्मीय / नागरी / कोर्ट लग्न आसा काय; तुम्ही मुस्लिम आसात काय; "
            "वा तुम्ही ख्रिस्ती वा पारशी आसात काय?"
        ),
        "succession": (
            "वारसाहक्क आनी उत्तराधिकार कायदे मृत व्यक्तीच्या धर्मावर अवलंबून आसतात। "
            "बरोबर माहितीसाठी सांगात: ती व्यक्ती हिंदू, बौद्ध, जैन वा शीख आसली काय; "
            "मुस्लिम आसली काय; वा ख्रिस्ती वा पारशी आसली काय?"
        ),
        "disclaimer": (
            "(हे उत्तर {label} वैयक्तिक कायद्यावर आधारित आसा। "
            "जर तुमची परिस्थिती वेगळी आसा, तर लागू कायदो आनी कलम वेगळे आसतले।)"
        ),
    },
    "mai": {
        "marriage": (
            "विवाह, तलाक आ गुजारा-भत्ता अलग-अलग कानून सँ नियंत्रित होइत अछि — "
            "ई दम्पतीक धर्म वा विवाहक प्रकारपर निर्भर करैत अछि। "
            "सही कानून बतेबाक लेल कहू: की अहाँ हिन्दू, बौद्ध, जैन वा सिख छी; "
            "अन्तर-धार्मिक / सिविल / कोर्ट विवाह अछि; "
            "की अहाँ मुसलमान छी; वा की अहाँ ईसाई वा पारसी छी?"
        ),
        "succession": (
            "उत्तराधिकार आ सम्पत्ति बँटवारा कानून मृत व्यक्तिक धर्मपर निर्भर करैत अछि। "
            "सही जानकारीक लेल कहू: ओ व्यक्ति हिन्दू, बौद्ध, जैन वा सिख छलाह; "
            "मुसलमान छलाह; वा ईसाई वा पारसी छलाह?"
        ),
        "disclaimer": (
            "(ई उत्तर {label} व्यक्तिगत कानूनपर आधारित अछि। "
            "जँ अहाँक परिस्थिति अलग हो, तखन लागू कानून आ धारा अलग हेतइ।)"
        ),
    },
    "doi": {
        "marriage": (
            "विवाह, तलाक ते गुज़ारा-भत्ता वखरे-वखरे कानूनें कनै तय होंदे न — "
            "एह जोड़े दे धर्म जां विवाह दे प्रकार उप्पर निर्भर करदा ऐ। "
            "सही कानून दस्सने लेई दस्सो: की तुस हिंदू, बौद्ध, जैन जां सिख ओ; "
            "अंतर-धार्मिक / सिविल / अदालती विवाह ऐ; "
            "की तुस मुसलमान ओ; जां की तुस ईसाई जां पारसी ओ?"
        ),
        "succession": (
            "विरासत ते जायदाद बंडवारे दे कानून मृतक दे धर्म उप्पर निर्भर करदे न। "
            "सही जानकारी लेई दस्सो: की उह इनसान हिंदू, बौद्ध, जैन जां सिख हा; "
            "मुसलमान हा; जां ईसाई जां पारसी हा?"
        ),
        "disclaimer": (
            "(एह जवाब {label} व्यक्तिगत कानून उप्पर आधारित ऐ। "
            "जेकर तुंदी हालत वखरी ऐ, तां लागू कानून ते धारा वखरे होंगे।)"
        ),
    },
    "brx": {
        "marriage": (
            "बिबाह, बिबाह गोनां आरो गोसोमाइ — नोगोर आरो बिबाहनि बिजाबनाय मोनसे मोनसे "
            "नियामनाव राव जाबायो। सायख़ि नियाम बिनां गोनांनो हो: नि हिन्दू, बौद्ध, जैन "
            "नो सिख आबुं; अंतर-धार्मिक / सिविल / कोर्ट बिबाह; नि मुसलमान; जों नि "
            "ईसाई जों पारसी?"
        ),
        "succession": (
            "सोनार बिजाब आरो सोंखो नियाम गोनांखौ मोनसे मोनसे बादि जाबायो। सायख़ि थांखिनि "
            "थाखाय हो: बे मानसिनि हिन्दू, बौद्ध, जैन जों सिख आसिल; मुसलमान आसिल; "
            "जों ईसाई जों पारसी आसिल?"
        ),
        "disclaimer": (
            "({label} सोम नियामनाव राव बे खोमानि जोबोद जाबायो। "
            "नि सोंखो बेसे जों थांखि जाबोन, नियाम आरो धारा बेसे जाबायो।)"
        ),
    },
    # Manipuri (Bengali script — same as bn/as but Meitei)
    "mni": {
        "marriage": (
            "লাইরেম্বী থৌরাং, থৌরাং পাংথোকপা অমসুং পুকনিং পীবা — "
            "ফম্বাল মীয়ামগী ধর্ম অমদি লাইরেম্বী থৌরাংগী অমত্তানা অমত্তা চেক্লা লোইশিনবা "
            "মপোক মাংদা মাংদনা চংলমগনি। মতম চানা পীনবা হায়বিয়ু: নহা হিন্দু, বৌদ্ধ, "
            "জৈন নত্ত্রগা শিখনি হায়না; সিভিল লাইরেম্বী থৌরাংনি হায়না; নহা মুছলিমনি হায়না; "
            "নত্ত্রগা নহা খ্রিষ্টান অমদি পার্সিনি হায়না?"
        ),
        "succession": (
            "উত্তরাধিকার অমদি খুদম চাউখৎলিবা — মরম মীয়ামগী ধর্মনা চেক্লা লোইশিনগনি। "
            "মতম চানা পীনবা হায়বিয়ু: হেনগৎপা মীয়ামসু হিন্দু, বৌদ্ধ, জৈন নত্ত্রগা "
            "শিখনি হায়না; মুছলিমনি হায়না; নত্ত্রগা খ্রিষ্টান অমদি পার্সিনি হায়না?"
        ),
        "disclaimer": (
            "({label} সোম মপোক লোইশিনবনা থাজবা মওং চানা পীজরে। "
            "নহাগী সনা-থৌবা অমত্তা চাউরবা অমোত্তসি লোইশিনবা মপোকসু চাউরগনি।)"
        ),
    },
    # Santali — Ol Chiki script (use simplified form)
    "sat": {
        "marriage": (
            "ᱵᱤᱵᱟᱦ, ᱵᱤᱵᱟᱦ ᱛᱩᱰᱟᱹᱣ ᱟᱨ ᱯᱚᱥᱚᱱ — ᱢᱤᱴᱷᱟᱹ ᱮᱞ ᱫᱷᱚᱨᱚᱢ ᱟᱨ "
            "ᱵᱤᱵᱟᱦ ᱨᱮᱫ ᱛᱮ ᱵᱮᱵᱷᱟᱨ ᱠᱟᱱᱩᱱ ᱮᱞᱮᱫ। ᱥᱟᱦᱤ ᱠᱟᱱᱩᱱ ᱯᱟᱹᱨᱛᱮ ᱵᱩᱜᱩ: "
            "ᱱᱤᱝ ᱦᱤᱱᱫᱩ, ᱵᱳᱫᱷ, ᱡᱮᱱ ᱵᱟ ᱥᱤᱠᱷ ᱠᱟ; ᱵᱤᱵᱟᱦ ᱠᱚ ᱠᱟ; "
            "ᱱᱤᱝ ᱢᱩᱥᱠᱟᱱ ᱠᱟ; ᱵᱟ ᱱᱤᱝ ᱤᱥᱟᱭ ᱵᱟ ᱯᱟᱨᱥᱤ ᱠᱟ?"
        ),
        "succession": (
            "ᱵᱤᱨᱥᱚᱛ ᱟᱨ ᱥᱚᱢᱯᱚᱛᱛᱤ ᱵᱟᱸᱰᱟᱣ — ᱢᱚᱨᱚᱢ ᱫᱷᱚᱨᱚᱢ ᱛᱮ ᱠᱟᱱᱩᱱ ᱮᱞᱮᱫ। "
            "ᱵᱩᱜᱩ: ᱩᱱ ᱢᱟᱬᱟᱭ ᱦᱤᱱᱫᱩ, ᱵᱳᱫᱷ, ᱡᱮᱱ ᱵᱟ ᱥᱤᱠᱷ ᱠᱟ ᱞᱮᱠᱟ; "
            "ᱢᱩᱥᱠᱟᱱ ᱠᱟ; ᱵᱟ ᱤᱥᱟᱭ ᱵᱟ ᱯᱟᱨᱥᱤ ᱠᱟ?"
        ),
        "disclaimer": (
            "({label} ᱢᱤᱴᱷᱟᱹ ᱠᱟᱱᱩᱱ ᱛᱮ ᱤᱧ ᱡᱚᱣᱟᱵ ᱫᱤᱭᱟᱹᱜᱽ ᱠᱟᱱᱟ। "
            "ᱱᱤᱝ ᱥᱟᱦᱟᱥ ᱵᱮᱞ ᱛᱮ ᱠᱟᱱᱩᱱ ᱟᱨ ᱫᱷᱟᱨᱟ ᱮᱞᱮᱫ ᱦᱚᱭᱤᱧ।)"
        ),
    },
    # Kashmiri and Sindhi — Arabic/Nastaliq script
    "ks": {
        "marriage": (
            "نکاح، طلاق تہِ خرچہ — مذہب یا نکاحُک طریقہ مطابق مُختلف قانون لاگو ہوان۔ "
            "صحیح قانون دَنے وستہِ بٲتاو: کیا اَس ہندو، بدھسٹ، جین یا سکھ چھیو; "
            "کیا آنتر مذہبی / سول / کورٹ نکاح ؤ; کیا اَس مسلمان چھیو; "
            "یا کیا اَس عیسائی یا پارسی چھیو?"
        ),
        "succession": (
            "وارثت تہِ جائداد بانٹ — مرحومُک مذہب مطابق مُختلف قانون لاگو ہوان۔ "
            "صحیح معلومات پیٹھے بٲتاو: کیا سُ مانُو ہندو، بدھسٹ، جین یا سکھ اوس; "
            "مسلمان اوس; یا عیسائی یا پارسی اوس?"
        ),
        "disclaimer": (
            "({label} ذاتی قانون پیٹھے راوُن ییہ جواب دنہ ہیو۔ "
            "یتھ کنہ اَپنہِ حالات بیاکھ ہو، لاگو قانون تہِ دفعہ بیاکھ ہوان۔)"
        ),
    },
    "sd": {
        "marriage": (
            "نڪاح، طلاق ۽ گذارو ڀتو — جوڙي جي مذهب يا شادي جي قسم موجب مختلف قانون لاڳو ٿين ٿا۔ "
            "صحيح قانون ٻڌائڻ لاءِ ٻڌايو: ڇا توهان هندو، ٻڌ، جين يا سک آهيو; "
            "آنٽر-ريليجيئس / سول / ڪورٽ شادي آهي; ڇا توهان مسلمان آهيو; "
            "يا ڇا توهان عيسائي يا پارسي آهيو؟"
        ),
        "succession": (
            "وراثت ۽ جائداد ورڇ جا قانون مرحوم جي مذهب موجب مختلف هوندا آهن۔ "
            "درست معلومات لاءِ ٻڌايو: ڇا اهو ماڻهو هندو، ٻڌ، جين يا سک هو; "
            "مسلمان هو; يا عيسائي يا پارسي هو؟"
        ),
        "disclaimer": (
            "(هي جواب {label} ذاتي قانون تي ٻڌل آهي۔ "
            "جيڪڏهن توهان جي صورتحال مختلف آهي ته لاڳو قانون ۽ دفعو مختلف هوندو۔)"
        ),
    },
}

# Fallback chain: try the exact code, then strip sub-tag (e.g. "hi-IN" → "hi"), then "en"
def _t(lang: str, key: str) -> str:
    code = (lang or "en").split("-")[0].lower()
    bucket = _TRANSLATIONS.get(code) or _TRANSLATIONS["en"]
    return bucket[key]

# ── Topic detection ──────────────────────────────────────────────────────
_MARRIAGE_TOPIC_RE = re.compile(
    r"register\s+(?:my|our|the)?\s*marriage|marriage\s+registration|"
    r"\bdivorce\b|\balimony\b|maintenance\s+(?:after|from)\s+(?:my\s+)?(?:husband|wife|spouse)|"
    r"child\s+custody|judicial\s+separation|\bannul(?:ment|)\b|"
    r"grounds?\s+for\s+divorce|mutual\s+divorce|file\s+for\s+divorce|"
    r"dissolve\s+(?:my|our|the)?\s*marriage|marriage\s+certificate|"
    r"court\s+marriage|marry\s+(?:legally|officially)",
    re.I,
)
_SUCCESSION_TOPIC_RE = re.compile(
    r"\binheritance\b|\binherit\b|\binherits?\b|\bsuccession\b|ancestral\s+property|"
    r"legal\s+heir|property\s+after\s+(?:death|dying|he\s+dies|she\s+dies)|"
    r"\bwill\b.{0,20}\bproperty\b|intestate|coparcenary|"
    r"share\s+in\s+(?:my\s+)?father|who\s+gets?\s+the\s+property|division\s+of\s+property",
    re.I,
)

# ── Religion / marriage-type context detection ──────────────────────────
# Each context maps to a short Act-name phrase per topic. That phrase is
# what gets silently appended to the retrieval text — it must be a phrase
# the existing corpus_db._ACT_HINTS table already recognises.
_CONTEXTS: dict[str, dict] = {
    "hindu": {
        "pattern": re.compile(r"\bhindu\b|\bbuddhist\b|\bjain\b|\bsikh\b", re.I),
        "marriage_hint": "Hindu Marriage Act",
        "succession_hint": "Hindu Succession Act",
        "label": "Hindu, Buddhist, Jain or Sikh",
    },
    "special": {
        "pattern": re.compile(
            r"inter.?religious|inter.?caste|inter.?faith|civil\s+marriage|"
            r"court\s+marriage|special\s+marriage|different\s+religion",
            re.I,
        ),
        "marriage_hint": "Special Marriage Act",
        "succession_hint": None,  # civil/inter-religious marriage alone doesn't fix succession law
        "label": "inter-religious / civil / court marriage",
    },
    "muslim": {
        "pattern": re.compile(r"\bmuslim\b|\bislam(?:ic)?\b|\bnikah\b|\bshariat?\b|\bshariah\b", re.I),
        "marriage_hint": "Dissolution of Muslim Marriages Act",
        "succession_hint": "Muslim Personal Law",
        "label": "Muslim personal law",
    },
    "christian_parsi": {
        "pattern": re.compile(r"\bchristian\b|\bcatholic\b|\bparsi\b", re.I),
        "marriage_hint": "Indian Christian Marriage Act",
        "succession_hint": "Indian Succession Act",
        "label": "Christian or Parsi",
    },
}


def classify_personal_law_topic(question: str) -> str | None:
    """Returns 'marriage' or 'succession' if the question is about
    marriage/family law or inheritance/succession law, else None."""
    if _MARRIAGE_TOPIC_RE.search(question):
        return "marriage"
    if _SUCCESSION_TOPIC_RE.search(question):
        return "succession"
    return None


def detect_context(question: str) -> str | None:
    """Returns the context id already named in the question
    ('hindu' | 'special' | 'muslim' | 'christian_parsi'), else None."""
    for ctx_id, cfg in _CONTEXTS.items():
        if cfg["pattern"].search(question):
            return ctx_id
    return None


def act_hint_phrase(ctx_id: str | None, topic: str) -> str | None:
    """Short Act-name phrase to silently append to the retrieval text for
    this context + topic. None if this context doesn't determine the
    answer for this topic (e.g. 'special' + succession) or is unknown."""
    cfg = _CONTEXTS.get(ctx_id or "")
    if not cfg:
        return None
    return cfg.get(f"{topic}_hint")


def disambiguation_question(topic: str, language: str = "en") -> str:
    """Plain-language clarifying question in the user's language — shown
    INSTEAD OF an answer when the topic is marriage/succession-related
    but no religion/marriage-type context is known yet."""
    return _t(language, topic if topic in ("marriage", "succession") else "marriage")


def act_disclaimer(ctx_id: str | None, topic: str, language: str = "en") -> str:
    """Short note appended after an answer once a context is known, so the
    user always sees which law was applied and that a different situation
    needs a different law."""
    label = _CONTEXTS.get(ctx_id or "", {}).get("label", "your situation")
    return _t(language, "disclaimer").replace("{label}", label)
