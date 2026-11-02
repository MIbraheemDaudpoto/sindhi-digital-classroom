"""Sindhi NLP & Unicode Script Normalization Module for SDC.
Implements Perso-Arabic text normalization, 52-character alphabet preservation,
diacritic stripping for robust search indexing, and educational concept tokenization.
Informed by computational linguistics research of Prof. Dr. Dil Nawaz Hakro (Univ of Sindh).
Authored under agency-ai-engineer.
"""

import re
import unicodedata
from typing import Dict, List, Set, Tuple

# Comprehensive Sindhi, Urdu, and English educational stopwords
SINDHI_STOPWORDS: Set[str] = {
    # Sindhi auxiliary verbs & pronouns
    "ڇا", "ڪير", "ڪٿي", "ڪيئن", "ڪڏهن", "ڇو", "ڪهڙو", "ڪهڙي", "ڪهڙا", "ڪهڙيون",
    "آهي", "آهن", "هئي", "هو", "هئا", "هيون", "ٿئي", "ٿيندو", "ٿيندي", "ٿيندا", "ٿينديون",
    "جو", "جي", "جا", "جون", "کي", "تان", "۾", "کان", "سان", "بابت", "طرف", "وٽ",
    "ٻڌايو", "ٻڌاءِ", "سمجهايو", "سمجھايو", "ڄاڻ", "سوال", "جواب", "ڪري", "مهرباني",
    "اسان", "منهنجو", "منهنجي", "پنهنجو", "پنهنجي", "ڪنهن", "انهن", "هن", "هو", "هي",
    # Common conversational adverbs & temporal auxiliaries
    "اڄ", "ڪالهه", "سڀاڻي", "هاڻي", "پوءِ", "ڪئي", "ڪيو", "ڪيا", "ڪيون", "ٿيو", "ٿي", "ٿيا", "ٿيون",
    # Urdu common loan auxiliaries
    "کیا", "کون", "کہاں", "کیسے", "کیوں", "ہے", "ہیں", "تھا", "تھی", "تھے", "سے", "کا", "کی", "کے",
    # English question words
    "what", "who", "where", "when", "why", "how", "is", "are", "was", "were", "the", "a", "an", "of", "in", "to", "for"
}

# Inquiry-intent tokens used by students asking for definitions/meanings
SINDHI_INQUIRY_TOKENS: Set[str] = {
    "معني", "معنيٰ", "معنا", "مطلب", "تعريف", "وصف", "مفهوم", "وضاحت", "سمجهاڻي",
    "meaning", "definition", "define", "concept"
}

# Canonical orthographic & keyboard variant mapping for student inputs
CANONICAL_SINDHI_VARIANTS: Dict[str, str] = {
    "سيت": "سيٽ",
    "سيتن": "سيٽن",
    "سٽ": "سيٽ",
    "سٽن": "سيٽن",
    "سب سيت": "ذيلي سيٽ",
    "سب سيٽ": "ذيلي سيٽ",
    "نل سيت": "خالي سيٽ",
    "نل سيٽ": "خالي سيٽ",
    "سپر سيت": "مٿانهون سيٽ",
    "سپر سيٽ": "مٿانهون سيٽ",
    "ايليمينٽ": "رڪن",
    "ايليمينٽس": "رڪن",
    "فوٽوسنتيسز": "فوٽوسنٿيسز",
    "فوٽوسينٿيسز": "فوٽوسنٿيسز",
    "فوٽوسنتيسس": "فوٽوسنٿيسز",
    "ريسپرئيشن": "ساهه کڻڻ جو عمل",
    "ريسپريشن": "ساهه کڻڻ جو عمل",
    "رڪنن": "رڪن",
    "معنيٰ": "معني",
    "معنا": "معني",
}

# Diacritics to strip during search normalization (Fatha, Damma, Kasra, Sukun, Shadda, etc.)
DIACRITICS_REGEX = re.compile(r'[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]')


def apply_sindhi_variants(text: str) -> str:
    """Normalize student keyboard and orthographic variants to canonical curriculum terms,
    while strictly protecting compound scientific and technological terms like پاڪ سيٽ (PAKSAT).
    """
    if not text:
        return ""
    # Protect compound science satellite entity PAKSAT
    text = text.replace("پاڪسيٽ", "پاڪ سيٽ")
    paksat_marker = "___SDC_PAKSAT_SATELLITE___"
    text = text.replace("پاڪ سيٽ", paksat_marker)

    # Multi-word replacements first
    for var, can in CANONICAL_SINDHI_VARIANTS.items():
        if " " in var:
            text = text.replace(var, can)

    # Single-word replacements on word boundaries
    for var, can in CANONICAL_SINDHI_VARIANTS.items():
        if " " not in var:
            pattern = r'(?<!\w)' + re.escape(var) + r'(?!\w)'
            text = re.sub(pattern, can, text)

    # Restore protected PAKSAT
    text = text.replace(paksat_marker, "پاڪ سيٽ")
    return text


def normalize_sindhi_text(text: str, strip_diacritics: bool = True) -> str:
    """Normalize Sindhi Unicode script while strictly preserving all 52 letters.
    
    Normalizations performed:
    1. Unicode NFC composition.
    2. Kaf normalization: Arabic Kaf (ك, U+0643) -> Sindhi Swash Kaf (ڪ, U+06AA).
    3. Yeh normalization: Persian Yeh (ی, U+06CC) -> Arabic/Sindhi Yeh (ي, U+064A).
    4. Heh normalization: Urdu Goal Heh (ہ, U+06C1) / Teh Marbuta (ة) -> Sindhi Heh (ه, U+0647).
    5. Tatweel / Kashida stripping (ـ, U+0640).
    6. Arabic/Urdu digits conversion to standard numeric representation.
    7. Optional diacritic stripping for search/matching index.
    8. Student keyboard & orthographic variant harmonization.
    """
    if not text:
        return ""

    # NFKC Normalization maps Arabic Presentation Forms (U+FB50-U+FDFF, U+FE70-U+FEFF)
    # into standard base characters while preserving the 52 Sindhi characters
    normalized = unicodedata.normalize("NFKC", text.strip())

    # Tatweel stripping
    normalized = normalized.replace("\u0640", "")

    # Protect canonical Sindhi digraph letters 'جھ' (\u062c\u06be) and 'گھ' (\u06af\u06be)
    # which belong to the canonical 52-letter Sindhi alphabet inventory
    jh_placeholder = "___SD_JH_DIGRAPH___"
    gh_placeholder = "___SD_GH_DIGRAPH___"
    normalized = normalized.replace("\u062c\u06be", jh_placeholder)
    normalized = normalized.replace("\u06af\u06be", gh_placeholder)

    # Letter standardizations
    normalized = normalized.replace("\u0643", "\u06AA")  # ك -> ڪ
    normalized = normalized.replace("\u06CC", "\u064A")  # ی -> ي
    normalized = normalized.replace("\u06BE", "\u0647")  # non-digraph Do-Chashmi Heh -> ه
    normalized = normalized.replace("\u06C1", "\u0647")  # Urdu Goal Heh ہ -> ه
    normalized = normalized.replace("\u06C2", "\u0647")  # ۂ -> ه
    normalized = normalized.replace("\u0629", "\u0647")  # Teh Marbuta ة -> ه

    # Restore canonical digraphs
    normalized = normalized.replace(jh_placeholder, "\u062c\u06be")
    normalized = normalized.replace(gh_placeholder, "\u06af\u06be")

    # Standardize Eastern Arabic / Urdu numerals to Western digits for unified math handling
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    persian_urdu_digits = "۰۱۲۳۴۵۶۷۸۹"
    for i in range(10):
        normalized = normalized.replace(arabic_digits[i], str(i))
        normalized = normalized.replace(persian_urdu_digits[i], str(i))

    # Strip non-phonemic decorative diacritics
    if strip_diacritics:
        normalized = DIACRITICS_REGEX.sub("", normalized)

    # Apply canonical orthographic variants for student keyboard differences
    normalized = apply_sindhi_variants(normalized)

    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def tokenize_sindhi_query(query: str) -> List[str]:
    """Tokenize and filter search terms from a student query."""
    normalized = normalize_sindhi_text(query.lower(), strip_diacritics=True)
    # Replace non-word and non-script symbols with spaces
    cleaned = re.sub(r'[^\w\s]', ' ', normalized)
    all_stop = SINDHI_STOPWORDS | SINDHI_INQUIRY_TOKENS
    tokens = [
        word for word in cleaned.split()
        if len(word) >= 2 and word not in all_stop
    ]
    # If all tokens were filtered (e.g. asking just "معني" or single word), retain cleaned words
    if not tokens:
        tokens = [word for word in cleaned.split() if len(word) >= 2]
    return tokens
    normalized = normalize_sindhi_text(query.lower(), strip_diacritics=True)
    # Replace non-word and non-script symbols with spaces
    cleaned = re.sub(r'[^\w\s]', ' ', normalized)
    tokens = [
        word for word in cleaned.split()
        if len(word) >= 2 and word not in SINDHI_STOPWORDS
    ]
    return tokens


def compute_grounding_similarity(query: str, document: str) -> float:
    """Compute normalized token overlap similarity between student query and curriculum passage.
    Returns float score between 0.0 and 1.0.
    """
    query_tokens = set(tokenize_sindhi_query(query))
    if not query_tokens:
        return 0.0

    doc_normalized = normalize_sindhi_text(document.lower(), strip_diacritics=True)
    doc_tokens = set(tokenize_sindhi_query(doc_normalized))
    if not doc_tokens:
        return 0.0

    intersection = query_tokens & doc_tokens
    # Jacquard overlap weighted by query completeness
    recall = len(intersection) / len(query_tokens)
    overlap_count = len(intersection)
    
    # Base confidence score
    score = recall * (0.8 + 0.2 * min(1.0, overlap_count / 3.0))
    return min(1.0, round(score, 4))
