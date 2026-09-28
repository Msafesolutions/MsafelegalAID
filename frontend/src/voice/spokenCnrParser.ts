/**
 * Spoken CNR / case-reference parser.
 *
 * Converts a raw speech transcript like:
 *   "case number four two seven of twenty twenty-four"
 * into structured digits:
 *   { caseNumber: "427", year: "2024", ... }
 *
 * Design goal: NEVER fabricate data. If the speaker only said a case number
 * and a year (no state/court letters), we surface exactly that — we do not
 * invent a court-running-number or state code to force a "complete" 16-char
 * CNR. The caller (Lookup screen) fills whatever was heard into the
 * editable CNR box and lets the user finish it manually.
 *
 * Pure function, zero React Native dependencies — trivially unit-testable.
 */

type Chunk = { digits: string; section: 'case' | 'year' };

const UNITS: Record<string, number> = {
  zero: 0, oh: 0, o: 0, nought: 0,
  one: 1, two: 2, three: 3, four: 4, five: 5,
  six: 6, seven: 7, eight: 8, nine: 9,
};

const TEENS: Record<string, number> = {
  ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14,
  fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
};

const TENS: Record<string, number> = {
  twenty: 20, thirty: 30, forty: 40, fifty: 50,
  sixty: 60, seventy: 70, eighty: 80, ninety: 90,
};

// Words that flip which "section" subsequent numbers belong to. Anything
// heard before the first YEAR_KEYWORD is treated as the case number;
// anything after is the year. CASE_KEYWORDS are recognised but don't force
// a flip (the default section is already 'case').
const CASE_KEYWORDS = new Set(['case', 'number', 'no', 'numero', 'reference']);
const YEAR_KEYWORDS = new Set(['of', 'in', 'year', 'dated', 'slash']);
const FILLER = new Set(['the', 'is', 'a', 'an', 'my', 'this', 'please', 'and', 'for']);

export type ParsedCaseRef = {
  /** Uppercase letters heard, in order (e.g. spoken "D L H C" -> "DLHC"). */
  letters: string;
  /** Case-number digits heard, unpadded (e.g. "427"). Null if none heard. */
  caseNumber: string | null;
  /** 4-digit year heard, if the year section produced exactly 4 digits. */
  year: string | null;
  /** All digits heard, concatenated in original spoken order (fallback). */
  rawDigits: string;
  /** Best-effort fill for the CNR box: letters + rawDigits, capped at 16 chars. */
  bestGuessCnr: string;
  /** True only if bestGuessCnr is already a full, valid-shape 16-char CNR. */
  isFullCnr: boolean;
  /** Human-readable "Heard: ..." feedback line for the UI. */
  heardSummary: string;
  /** Nothing recognisable was heard at all. */
  isEmpty: boolean;
};

function normalizeWords(transcript: string): string[] {
  return (transcript || '')
    .toLowerCase()
    // "twenty-four" -> "twenty four"; strip other punctuation entirely.
    .replace(/[-–—]/g, ' ')
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);
}

export function parseSpokenCaseRef(transcript: string): ParsedCaseRef {
  const words = normalizeWords(transcript);

  let letters = '';
  const chunks: Chunk[] = [];
  let section: 'case' | 'year' = 'case';
  let pendingTens: number | null = null;
  let sawAnyCaseDigit = false;

  const flushTens = () => {
    if (pendingTens !== null) {
      chunks.push({ digits: String(pendingTens).padStart(2, '0'), section });
      pendingTens = null;
    }
  };

  for (const raw of words) {
    const w = raw.trim();
    if (!w) continue;

    // Single spoken letter (STT usually renders "d", "el", "dee" oddly —
    // we only reliably catch the plain single-character form here).
    if (w.length === 1 && /[a-z]/.test(w)) {
      flushTens();
      letters += w.toUpperCase();
      continue;
    }

    if (YEAR_KEYWORDS.has(w)) {
      flushTens();
      if (sawAnyCaseDigit) section = 'year';
      continue;
    }
    if (CASE_KEYWORDS.has(w) || FILLER.has(w)) {
      flushTens();
      continue;
    }

    if (w in TENS) {
      flushTens();
      pendingTens = TENS[w];
      continue;
    }
    if (w in UNITS) {
      if (pendingTens !== null) {
        chunks.push({ digits: String(pendingTens + UNITS[w]).padStart(2, '0'), section });
        pendingTens = null;
      } else {
        chunks.push({ digits: String(UNITS[w]), section });
      }
      if (section === 'case') sawAnyCaseDigit = true;
      continue;
    }
    if (w in TEENS) {
      flushTens();
      chunks.push({ digits: String(TEENS[w]), section });
      if (section === 'case') sawAnyCaseDigit = true;
      continue;
    }
    // A bare digit string already (STT sometimes emits "427" directly
    // rather than spelling it out as words).
    if (/^\d+$/.test(w)) {
      flushTens();
      if (w.length === 4) {
        // A standalone 4-digit run heard as a single token is almost always
        // a year (e.g. STT returning "2024" literally) — but only treat it
        // as the year section if we haven't already started one.
        chunks.push({ digits: w, section: sawAnyCaseDigit ? 'year' : section });
      } else {
        chunks.push({ digits: w, section });
        if (section === 'case') sawAnyCaseDigit = true;
      }
      continue;
    }
    // Unrecognised word — ignore (e.g. "of the court", "please", stray STT noise).
    flushTens();
  }
  flushTens();

  const caseDigitsStr = chunks.filter(c => c.section === 'case').map(c => c.digits).join('');
  const yearDigitsStr = chunks.filter(c => c.section === 'year').map(c => c.digits).join('');
  const rawDigits = chunks.map(c => c.digits).join('');

  const caseNumber = caseDigitsStr.length > 0 ? caseDigitsStr : null;
  const year = yearDigitsStr.length === 4 ? yearDigitsStr : null;

  const bestGuessCnr = (letters + rawDigits).slice(0, 16).toUpperCase();
  const isFullCnr = /^[A-Z]{4}\d{12}$/.test(bestGuessCnr);

  const parts: string[] = [];
  if (letters) parts.push(`Letters: ${letters}`);
  if (caseNumber) parts.push(`Case no. ${caseNumber}`);
  if (year) parts.push(`Year ${year}`);
  else if (yearDigitsStr) parts.push(`Year (heard "${yearDigitsStr}")`);

  const isEmpty = !letters && !caseNumber && !yearDigitsStr;
  const heardSummary = isEmpty
    ? 'Could not make out any case details — please try again or type manually.'
    : `Heard: ${parts.join(' · ')}`;

  return {
    letters,
    caseNumber,
    year,
    rawDigits,
    bestGuessCnr,
    isFullCnr,
    heardSummary,
    isEmpty,
  };
}
