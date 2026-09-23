const en = {
  ageHeading: 'Confirm your age',
  termsLink: 'Read Terms & Conditions',
  termsTitle: 'Terms & Conditions',
  termsLanguage: 'Full legal text is currently available in English.',
  back: 'Back to consent',
  retry: 'Try again',
  loading: 'Loading Terms & Conditions…',
  termsError: 'Could not load the terms. Check your connection and try again.',
  ageRequired: 'To continue, select your age above.',
  termsRequired: 'To continue, agree to the Terms of Use.',
  dataRequired: 'To continue, agree to the required use of your information.',
  ready: 'Ready to continue. Both optional choices can stay off.',
  under18: 'Accounts are only available to people aged 18 or older. You can still access emergency help and read about your rights without an account.',
  emergency: 'Emergency help',
  rights: 'Know your rights',
  saveError: 'We could not save your consent. Please try again. Your selections have been kept.',
};

const hi: typeof en = {
  ageHeading: 'अपनी उम्र की पुष्टि करें', termsLink: 'नियम और शर्तें पढ़ें', termsTitle: 'नियम और शर्तें',
  termsLanguage: 'पूरा कानूनी पाठ अभी अंग्रेज़ी में उपलब्ध है।', back: 'सहमति पर वापस जाएँ', retry: 'फिर कोशिश करें',
  loading: 'नियम और शर्तें लोड हो रही हैं…', termsError: 'शर्तें लोड नहीं हो सकीं। इंटरनेट जाँचें और फिर कोशिश करें।',
  ageRequired: 'आगे बढ़ने के लिए ऊपर अपनी उम्र चुनें।', termsRequired: 'आगे बढ़ने के लिए उपयोग की शर्तों से सहमत हों।',
  dataRequired: 'आगे बढ़ने के लिए अपनी जानकारी के आवश्यक उपयोग की सहमति दें।',
  ready: 'अब आगे बढ़ सकते हैं। दोनों वैकल्पिक विकल्प बंद रह सकते हैं।',
  under18: 'खाता बनाने के लिए उम्र कम से कम 18 साल होनी चाहिए। आप बिना खाते के आपातकालीन मदद और अपने अधिकारों की जानकारी पा सकते हैं।',
  emergency: 'आपातकालीन मदद', rights: 'अपने अधिकार जानें', saveError: 'आपकी सहमति सहेजी नहीं जा सकी। फिर कोशिश करें। आपके चयन सुरक्षित हैं।',
};

const mr: typeof en = {
  ageHeading: 'तुमच्या वयाची पुष्टी करा', termsLink: 'नियम आणि अटी वाचा', termsTitle: 'नियम आणि अटी',
  termsLanguage: 'संपूर्ण कायदेशीर मजकूर सध्या इंग्रजीत उपलब्ध आहे.', back: 'संमतीकडे परत जा', retry: 'पुन्हा प्रयत्न करा',
  loading: 'नियम आणि अटी लोड होत आहेत…', termsError: 'अटी लोड झाल्या नाहीत. इंटरनेट तपासा आणि पुन्हा प्रयत्न करा.',
  ageRequired: 'पुढे जाण्यासाठी वर तुमचे वय निवडा.', termsRequired: 'पुढे जाण्यासाठी वापराच्या अटी मान्य करा.',
  dataRequired: 'पुढे जाण्यासाठी तुमच्या माहितीच्या आवश्यक वापरास संमती द्या.',
  ready: 'आता पुढे जाऊ शकता. दोन्ही ऐच्छिक पर्याय बंद ठेवू शकता.',
  under18: 'खाते तयार करण्यासाठी वय किमान 18 वर्षे असणे आवश्यक आहे. खात्याशिवाय आपत्कालीन मदत आणि तुमच्या हक्कांची माहिती मिळवू शकता.',
  emergency: 'आपत्कालीन मदत', rights: 'तुमचे हक्क जाणा', saveError: 'तुमची संमती जतन झाली नाही. पुन्हा प्रयत्न करा. तुमच्या निवडी कायम आहेत.',
};

export const consentCopy: Record<string, typeof en> = { en, hi, mr };
export type ConsentCopy = typeof en;