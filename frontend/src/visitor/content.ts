/**
 * Visitor Mode — Static content for Emergency and Lost Passport workflows.
 * Each step has: title (tourist's language key), body, speak_hi (Hindi phrase
 * for "Speak For Me" — read aloud to Indian officials).
 */

export type WorkflowStep = {
  id: string;
  icon: string;
  title: Record<string, string>;  // keyed by lang code, fallback 'en'
  body: Record<string, string>;
  speak_hi?: string;  // Hindi phrase for Speak For Me
  callNumber?: string;
  callLabel?: Record<string, string>;
};

export const EMERGENCY_STEPS: WorkflowStep[] = [
  {
    id: 'call_112',
    icon: 'call',
    title: {
      en: 'Call Emergency: 112',
      fr: 'Appeler le 112',
      de: 'Notruf: 112',
      es: 'Llamar al 112',
      pt: 'Ligar 112',
      it: 'Chiama il 112',
      ja: '112に電話する',
      ko: '112 전화하기',
      zh: '拨打112',
      ar: 'اتصل بـ 112',
      ru: 'Позвонить 112',
      hi: '112 पर कॉल करें',
    },
    body: {
      en: 'India\'s single emergency number. Works for police, fire, and ambulance. Free from any mobile.',
      fr: 'Numéro d\'urgence unique en Inde. Gratuit depuis tout mobile.',
      de: 'Indiens einheitliche Notrufnummer. Kostenlos von jedem Mobiltelefon.',
      es: 'Número de emergencia único de India. Gratis desde cualquier móvil.',
      hi: 'भारत का एकीकृत आपातकालीन नंबर। किसी भी मोबाइल से मुफ्त।',
    },
    speak_hi: 'मुझे तुरंत मदद चाहिए। मैं एक विदेशी पर्यटक हूँ। कृपया 112 पर कॉल करें।',
    callNumber: '112',
    callLabel: { en: 'Call 112 now', hi: '112 पर कॉल करें' },
  },
  {
    id: 'nearest_police',
    icon: 'shield-checkmark-outline',
    title: {
      en: 'Locate Nearest Police Station',
      fr: 'Trouver le commissariat le plus proche',
      de: 'Nächste Polizeiwache finden',
      es: 'Encontrar la comisaría más cercana',
      hi: 'निकटतम पुलिस थाना खोजें',
    },
    body: {
      en: 'Tell the officer: "I am a foreign tourist. I need assistance." Show this screen if needed.',
      fr: 'Dites à l\'agent : "Je suis un touriste étranger. J\'ai besoin d\'aide."',
      de: 'Sagen Sie dem Beamten: "Ich bin ein ausländischer Tourist. Ich brauche Hilfe."',
      es: 'Diga al agente: "Soy un turista extranjero. Necesito ayuda."',
      hi: 'अधिकारी से कहें: "मैं एक विदेशी पर्यटक हूँ। मुझे सहायता चाहिए।"',
    },
    speak_hi: 'मैं एक विदेशी पर्यटक हूँ। मुझे तत्काल सहायता की आवश्यकता है। कृपया मेरी मदद करें।',
  },
  {
    id: 'embassy',
    icon: 'flag-outline',
    title: {
      en: 'Contact Your Embassy',
      fr: 'Contacter votre ambassade',
      de: 'Botschaft kontaktieren',
      es: 'Contactar su embajada',
      hi: 'अपना दूतावास संपर्क करें',
    },
    body: {
      en: 'Your embassy can provide emergency travel documents, interpreter services, and legal assistance. See contacts on the next screen.',
      fr: 'Votre ambassade peut fournir des documents de voyage d\'urgence et une assistance.',
      de: 'Ihre Botschaft kann Notreisedokumente und Rechtshilfe bereitstellen.',
      es: 'Su embajada puede proporcionar documentos de viaje de emergencia y asistencia.',
      hi: 'आपका दूतावास आपातकालीन यात्रा दस्तावेज़ और कानूनी सहायता प्रदान कर सकता है।',
    },
    speak_hi: 'मुझे मेरे दूतावास से संपर्क करने में मदद चाहिए। मैं एक विदेशी पर्यटक हूँ।',
  },
];

export const LOST_PASSPORT_STEPS: WorkflowStep[] = [
  {
    id: 'file_fir',
    icon: 'document-text-outline',
    title: {
      en: 'File a Police Report (FIR)',
      fr: 'Déposer une plainte (FIR)',
      de: 'Polizeibericht erstatten (FIR)',
      es: 'Presentar denuncia policial (FIR)',
      hi: 'पुलिस रिपोर्ट (FIR) दर्ज करें',
    },
    body: {
      en: 'Go to the nearest police station and request an FIR for lost passport. The FIR copy is required by your embassy. You can file at ANY police station in India (Zero FIR right).',
      fr: 'Rendez-vous au commissariat le plus proche pour un FIR pour passeport perdu.',
      de: 'Gehen Sie zur nächsten Polizeiwache für einen FIR wegen verlorenem Reisepass.',
      es: 'Vaya a la comisaría más cercana para presentar un FIR por pérdida de pasaporte.',
      hi: 'निकटतम पुलिस थाने पर जाएँ और खोए हुए पासपोर्ट के लिए FIR दर्ज करवाएँ।',
    },
    speak_hi: 'मेरा पासपोर्ट खो गया है। मैं एक विदेशी पर्यटक हूँ। मुझे FIR दर्ज करवानी है। कृपया मेरी मदद करें।',
  },
  {
    id: 'embassy_contact',
    icon: 'flag-outline',
    title: {
      en: 'Contact Your Embassy / Consulate',
      fr: 'Contacter votre ambassade / consulat',
      de: 'Botschaft / Konsulat kontaktieren',
      es: 'Contactar su embajada / consulado',
      hi: 'अपने दूतावास / वाणिज्य दूतावास से संपर्क करें',
    },
    body: {
      en: 'Report the loss to your embassy with the FIR copy. They will issue an Emergency Travel Document (ETD). Most embassies in India are in New Delhi; check for consulates in major cities.',
      fr: 'Signalez la perte à votre ambassade avec la copie du FIR.',
      de: 'Melden Sie den Verlust Ihrer Botschaft mit der FIR-Kopie.',
      es: 'Informe la pérdida a su embajada con la copia del FIR.',
      hi: 'FIR की कॉपी के साथ अपने दूतावास को सूचित करें।',
    },
    speak_hi: 'मेरा पासपोर्ट खो गया है। मुझे अपने दूतावास से संपर्क करना है। क्या आप मेरी मदद कर सकते हैं?',
  },
  {
    id: 'frro',
    icon: 'business-outline',
    title: {
      en: 'Register with FRRO',
      fr: 'S\'enregistrer auprès du FRRO',
      de: 'Bei der FRRO registrieren',
      es: 'Registrarse con el FRRO',
      hi: 'FRRO के साथ पंजीकरण करें',
    },
    body: {
      en: 'The Foreigners Regional Registration Office (FRRO) handles visa extensions and emergency documentation. Apply online at indianfrro.gov.in or visit in person. Required documents: FIR copy, passport photos, embassy letter.',
      fr: 'Le FRRO gère les prolongations de visa. Demandez en ligne sur indianfrro.gov.in.',
      de: 'Das FRRO bearbeitet Visaverlängerungen. Online-Antrag auf indianfrro.gov.in.',
      es: 'El FRRO gestiona extensiones de visa. Solicite en línea en indianfrro.gov.in.',
      hi: 'FRRO वीज़ा विस्तार और आपातकालीन दस्तावेज़ीकरण संभालता है। indianfrro.gov.in पर ऑनलाइन आवेदन करें।',
    },
    speak_hi: 'मुझे FRRO से मिलना है। मेरा पासपोर्ट खो गया है और मैं एक विदेशी पर्यटक हूँ।',
    callNumber: 'https://indianfrro.gov.in',
    callLabel: { en: 'Open FRRO website', hi: 'FRRO वेबसाइट खोलें' },
  },
  {
    id: 'tourist_helpline',
    icon: 'headset-outline',
    title: {
      en: 'Tourist Helpline: 1800-111-363',
      fr: 'Ligne d\'assistance touriste: 1800-111-363',
      de: 'Touristen-Hotline: 1800-111-363',
      es: 'Línea de ayuda turística: 1800-111-363',
      hi: 'पर्यटक हेल्पलाइन: 1800-111-363',
    },
    body: {
      en: 'India Tourism\'s 24/7 free helpline for foreign tourists. Staff speak multiple languages. They can assist with lost documents, safety issues, and general guidance.',
      fr: 'Ligne d\'assistance touristique gratuite 24h/24. Disponible en plusieurs langues.',
      de: '24/7 kostenlose Touristen-Hotline. Mehrsprachig verfügbar.',
      es: 'Línea gratuita 24/7 para turistas extranjeros. Disponible en varios idiomas.',
      hi: 'विदेशी पर्यटकों के लिए 24/7 मुफ्त हेल्पलाइन।',
    },
    speak_hi: 'मैं एक विदेशी पर्यटक हूँ। मेरा पासपोर्ट खो गया है। कृपया पर्यटक हेल्पलाइन 1800-111-363 पर कॉल करें।',
    callNumber: '1800111363',
    callLabel: { en: 'Call Tourist Helpline', hi: 'हेल्पलाइन पर कॉल करें' },
  },
];

export const EMBASSY_CONTACTS: Record<string, { name: string; phone: string; city: string }> = {
  en:  { name: 'British High Commission',     phone: '+91-11-24192100', city: 'New Delhi' },
  fr:  { name: 'French Embassy',               phone: '+91-11-24196100', city: 'New Delhi' },
  de:  { name: 'German Embassy',               phone: '+91-11-44199199', city: 'New Delhi' },
  es:  { name: 'Spanish Embassy',              phone: '+91-11-46004071', city: 'New Delhi' },
  pt:  { name: 'Portuguese Embassy',           phone: '+91-11-26115539', city: 'New Delhi' },
  it:  { name: 'Italian Embassy',              phone: '+91-11-26114355', city: 'New Delhi' },
  ja:  { name: 'Embassy of Japan',             phone: '+91-11-26876564', city: 'New Delhi' },
  ko:  { name: 'Embassy of Korea',             phone: '+91-11-26884793', city: 'New Delhi' },
  zh:  { name: 'Embassy of China',             phone: '+91-11-26112345', city: 'New Delhi' },
  ar:  { name: 'Saudi Embassy (regional)',      phone: '+91-11-26112447', city: 'New Delhi' },
  ru:  { name: 'Embassy of Russia',            phone: '+91-11-26873799', city: 'New Delhi' },
  hi:  { name: 'India (Domestic)',              phone: '112',             city: 'Any city' },
};
