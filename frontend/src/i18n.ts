/**
 * Minimal static-UI i18n layer for DHARA.
 *
 * All AI-generated content is already language-aware via the backend.
 * This file covers STATIC chrome: tab labels, Settings headings, disclaimer.
 *
 * Pattern: t('tab.ask', language.code)  →  'पूछें'  (falls back to English)
 */

export type I18nKey =
  | 'tab.ask'
  | 'tab.rights'
  | 'tab.saved'
  | 'tab.lookup'
  | 'tab.advocate'
  | 'tab.settings'
  | 'settings.title'
  | 'settings.subtitle'
  | 'settings.section.preferences'
  | 'settings.language'
  | 'settings.state'
  | 'settings.autoSpeak'
  | 'settings.autoSpeak.desc'
  | 'settings.signout'
  | 'settings.account'
  | 'disclaimer';

type LangMap = Partial<Record<string, string>>;

const TR: Record<I18nKey, LangMap> = {
  'tab.ask':       { en:'Ask',       hi:'पूछें',      mr:'विचारा',    ta:'கேள்',       bn:'জিজ্ঞেস',  te:'అడగండి',   gu:'પૂછો',   kn:'ಕೇಳಿ',   pa:'ਪੁੱਛੋ',   ml:'ചോദിക്കൂ' },
  'tab.rights':    { en:'Rights',    hi:'अधिकार',     mr:'हक्क',      ta:'உரிமை',      bn:'অধিকার',  te:'హక్కులు',  gu:'અધિકાર', kn:'ಹಕ್ಕು',  pa:'ਅਧਿਕਾਰ',  ml:'അവകാശം' },
  'tab.saved':     { en:'Saved',     hi:'सहेजे',      mr:'जतन',       ta:'சேமித்த',    bn:'সংরক্ষিত', te:'సేవ్',     gu:'સાચવ્યા', kn:'ಉಳಿಸಿದ', pa:'ਸੁਰੱਖਿਅਤ', ml:'സേവ്' },
  'tab.lookup':    { en:'Lookup',    hi:'खोज',        mr:'शोध',       ta:'தேடல்',      bn:'খোঁজ',    te:'వెతుకు',   gu:'શોધ',    kn:'ಹುಡುಕು', pa:'ਖੋਜ',     ml:'തിരയൂ' },
  'tab.advocate':  { en:'Advocate',  hi:'अधिवक्ता',   mr:'वकील',      ta:'வழக்கறிஞர்', bn:'উকিল',    te:'న్యాయవాది', gu:'વકીલ',  kn:'ವಕೀಲ',   pa:'ਵਕੀਲ',    ml:'അഭിഭാഷകൻ' },
  'tab.settings':  { en:'Settings',  hi:'सेटिंग',     mr:'सेटिंग',    ta:'அமைப்புகள்', bn:'সেটিং',   te:'సెట్టింగులు', gu:'સેટિંગ', kn:'ಸೆಟ್ಟಿಂಗ್', pa:'ਸੈਟਿੰਗ', ml:'ക്രമീകരണം' },

  'settings.title':    { en:'Settings',             hi:'सेटिंग्स',                 mr:'सेटिंग्स',              ta:'அமைப்புகள்',          bn:'সেটিংস',             te:'సెట్టింగులు',          gu:'સેટિંગ્સ',            kn:'ಸೆಟ್ಟಿಂಗ್ಗಳು',       pa:'ਸੈਟਿੰਗਾਂ',          ml:'ക്രമീകരണങ്ങൾ' },
  'settings.subtitle': { en:'Personalize your Dhara', hi:'अपना धारा अनुकूलित करें', mr:'तुमचा धारा सानुकूल करा', ta:'உங்கள் தாரா தனிப்பயன்', bn:'আপনার ধারা ব্যক্তিগতকরণ', te:'మీ ధారాని వ్యక్తిగతీకరించండి', gu:'તમારા ધારાને વ્યક્તિગત', kn:'ನಿಮ್ಮ ಧಾರಾ ವ್ಯಕ್ತಿಗತ', pa:'ਆਪਣਾ ਧਾਰਾ ਵਿਅਕਤੀਗਤ', ml:'നിങ്ങളുടെ ധാരാ' },
  'settings.section.preferences': { en:'Preferences', hi:'प्राथमिकताएं', mr:'प्राधान्ये', ta:'விருப்பங்கள்', bn:'পছন্দ', te:'ప్రాధాన్యతలు', gu:'પ્રાધાન્યતા', kn:'ಆದ್ಯತೆಗಳು', pa:'ਤਰਜੀਹਾਂ', ml:'മുൻഗണനകൾ' },
  'settings.language': { en:'Language',              hi:'भाषा',                     mr:'भाषा',                  ta:'மொழி',                bn:'ভাষা',               te:'భాష',                  gu:'ભાષા',                kn:'ಭಾಷೆ',               pa:'ਭਾਸ਼ਾ',              ml:'ഭാഷ' },
  'settings.state':    { en:'State / Union Territory', hi:'राज्य / केंद्र शासित प्रदेश', mr:'राज्य / केंद्रशासित प्रदेश', ta:'மாநிலம் / யூனியன் பிரதேசம்', bn:'রাজ্য / কেন্দ্রশাসিত অঞ্চল', te:'రాష్ట్రం / కేంద్ర పాలిత', gu:'રાજ્ય / કેન્દ્ર શાસિત', kn:'ರಾಜ್ಯ / ಕೇಂದ್ರ ಆಡಳಿತ', pa:'ਸੂਬਾ / ਕੇਂਦਰ ਸ਼ਾਸਿਤ', ml:'സംസ്ഥാനം / ഭരണ. ' },
  'settings.autoSpeak':      { en:'Auto-speak answers', hi:'उत्तर स्वतः बोलें', mr:'उत्तरे आपोआप बोला', ta:'விடைகளை தானாக பேசு', bn:'স্বয়ংক্রিয় বক্তব্য', te:'స్వయంచాలకంగా చెప్పు', gu:'સ્વયં-ઉત્તર', kn:'ಸ್ವಯಂ ಮಾತನಾಡು', pa:'ਆਪਣੇ ਆਪ ਬੋਲੋ', ml:'സ്വതഃ ഉത്തരം' },
  'settings.autoSpeak.desc': { en:'Reads each answer aloud after it arrives', hi:'प्रत्येक उत्तर आते ही पढ़ता है', mr:'प्रत्येक उत्तर आल्यावर वाचते', ta:'ஒவ்வொரு பதிலும் வந்தவுடன் படிக்கும்', bn:'প্রতিটি উত্তর পড়ে', te:'సమాధానం వచ్చిన వెంటనే చదువుతుంది', gu:'દરેક ઉત્તર આવ્યા પછી વાંચે', kn:'ಪ್ರತಿ ಉತ್ತರ ಬಂದ ತಕ್ಷಣ ಓದುತ್ತದೆ', pa:'ਹਰ ਜਵਾਬ ਆਉਣ ਤੋਂ ਬਾਅਦ ਪੜ੍ਹਦਾ ਹੈ', ml:'ഉത്തരം വന്നാൽ ഉടൻ വായിക്കും' },
  'settings.signout': { en:'Sign Out', hi:'साइन आउट', mr:'साइन आउट', ta:'வெளியேறு', bn:'সাইন আউট', te:'సైన్ అవుట్', gu:'સાઇન આઉટ', kn:'ಸೈನ್ ಔಟ್', pa:'ਸਾਈਨ ਆਉਟ', ml:'സൈൻ ഔട്ട്' },
  'settings.account': { en:'Account', hi:'खाता', mr:'खाते', ta:'கணக்கு', bn:'অ্যাকাউন্ট', te:'ఖాతా', gu:'એકાઉન્ટ', kn:'ಖಾತೆ', pa:'ਖਾਤਾ', ml:'അക്കൗണ്ട്' },

  'disclaimer': {
    en: 'DHARA provides legal information, not legal advice. This does not create an advocate-client relationship. Verify with a qualified advocate before acting.',
    hi: 'DHARA कानूनी जानकारी देता है, कानूनी सलाह नहीं। यह अधिवक्ता-मुवक्किल संबंध नहीं बनाता। कार्रवाई से पहले किसी अर्हता प्राप्त अधिवक्ता से सत्यापित करें।',
    mr: 'DHARA कायदेशीर माहिती देते, कायदेशीर सल्ला नाही। हे वकील-अशील संबंध निर्माण करत नाही। कार्यवाही करण्यापूर्वी पात्र वकिलाकडून सत्यापित करा।',
    ta: 'DHARA சட்ட தகவல் வழங்குகிறது, சட்ட ஆலோசனை அல்ல. வழக்கறிஞர்-வாடிக்கையாளர் உறவு அல்ல. நடவடிக்கை எடுப்பதற்கு முன் தகுதிவாய்ந்த வழக்கறிஞரிடம் சரிபார்க்கவும்.',
    bn: 'DHARA আইনি তথ্য দেয়, আইনি পরামর্শ নয়। আইনজীবী-মক্কেল সম্পর্ক নয়। পদক্ষেপ নেওয়ার আগে যোগ্য আইনজীবীর সাথে যাচাই করুন।',
    te: 'DHARA చట్టపరమైన సమాచారం అందిస్తుంది, సలహా కాదు. న్యాయవాది-క్లయింట్ సంబంధం కాదు. చర్య తీసుకునే ముందు అర్హత గల న్యాయవాదితో నిర్ధారించండి.',
    gu: 'DHARA કાનૂની માહિતી આપે છે, સલાહ નહીં. વકીલ-ગ્રાહક સંબંધ નથી. પગલાં ભરતા પહેલાં અર્હ વકીલ સાથે ચકાસો.',
    kn: 'DHARA ಕಾನೂನು ಮಾಹಿತಿ ನೀಡುತ್ತದೆ, ಸಲಹೆಯಲ್ಲ. ವಕೀಲ-ಕಕ್ಷಿ ಸಂಬಂಧ ಅಲ್ಲ. ಕ್ರಮ ತೆಗೆದುಕೊಳ್ಳುವ ಮೊದಲು ಅರ್ಹ ವಕೀಲರಿಂದ ಪರಿಶೀಲಿಸಿ.',
    pa: 'DHARA ਕਾਨੂੰਨੀ ਜਾਣਕਾਰੀ ਦਿੰਦਾ ਹੈ, ਸਲਾਹ ਨਹੀਂ। ਵਕੀਲ-ਮੁਵੱਕਿਲ ਸੰਬੰਧ ਨਹੀਂ। ਕਦਮ ਚੁੱਕਣ ਤੋਂ ਪਹਿਲਾਂ ਯੋਗ ਵਕੀਲ ਨਾਲ ਜਾਂਚ ਕਰੋ।',
    ml: 'DHARA നിയമ വിവരങ്ങൾ നൽകുന്നു, ഉപദേശമല്ല. അഭിഭാഷക-കക്ഷി ബന്ധമല്ല. നടപടി എടുക്കുന്നതിന് മുമ്പ് അഭിഭാഷകനുമായി സ്ഥിരീകരിക്കുക.',
  },
};

/**
 * Translate a static UI key to the given language code.
 * Falls back to English, then to the key itself.
 */
export function t(key: I18nKey, langCode: string): string {
  const map = TR[key];
  if (!map) return key;
  return map[langCode] ?? map['en'] ?? key;
}
