"""Unit tests for Sindhi Unicode Normalization and Heuristic Retrieval Scoring.
Authored under agency-ai-engineer and agency-rag-pipeline-engineer.

Verifies:
1. All standard 52 letters of the Sindhi Perso-Arabic alphabet survive normalization intact.
2. Dialectal and typographic variations (Kaf, Yeh, Heh, Tatweel) map safely without corrupting valid words.
3. Eastern Arabic and Persian/Urdu numerals standardize to ASCII digits without breaking normal words.
4. Diacritic stripping operates safely on vowel marks while retaining root letters.
5. Heuristic retrieval scoring and the 'Introduction to Sets' regression query succeed reliably.
"""

import pytest
from src.services.sindhi_nlp import normalize_sindhi_text, tokenize_sindhi_query, compute_grounding_similarity
from src.services.ai_tutor_service import ai_tutor_service
from src.models.schemas import TutorAskRequest


# The canonical 52 letters of the Sindhi Perso-Arabic Alphabet
SINDHI_52_LETTERS = [
    "ا", "ب", "ٻ", "ڀ", "ت", "ٿ", "ٽ", "ٺ", "ث", "پ",
    "ج", "ڄ", "جھ", "ڃ", "چ", "ڇ", "ح", "خ", "د", "ڌ",
    "ڏ", "ڊ", "ڍ", "ذ", "ر", "ڙ", "ز", "ژ", "س", "ش",
    "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ڦ", "ق", "ڪ",
    "ک", "گ", "ڳ", "گھ", "ڱ", "ل", "م", "ن", "ڻ", "و",
    "ه", "ء", "ي"
]


def test_sindhi_52_letter_inventory_preservation():
    """Verify that all 52 letters of the Sindhi alphabet pass through normalization intact."""
    for letter in SINDHI_52_LETTERS:
        normalized = normalize_sindhi_text(letter)
        assert normalized == letter, f"Letter {letter} was altered during normalization to {normalized}"


def test_sindhi_typographic_variant_mapping():
    """Verify non-standard Persian/Arabic/Urdu variants map safely to canonical Sindhi characters."""
    # Arabic Kaf (ك) -> Sindhi Swash Kaf (ڪ)
    assert normalize_sindhi_text("كتاب") == "ڪتاب"
    
    # Persian Yeh (ی) -> Sindhi/Arabic Yeh (ي)
    assert normalize_sindhi_text("پاڻی") == "پاڻي"
    
    # Urdu Goal Heh (ہ) -> Sindhi Heh (ه)
    assert normalize_sindhi_text("شہر") == "شهر"
    
    # Tatweel / Kashida (ـ) removal
    assert normalize_sindhi_text("ســـنڌي") == "سنڌي"


def test_sindhi_numeral_standardization():
    """Verify Eastern Arabic and Urdu numerals convert accurately to ASCII digits."""
    # Eastern Arabic numerals: ٠١٢٣٤٥٦٧٨٩
    assert normalize_sindhi_text("ڪلاس ٦") == "ڪلاس 6"
    assert normalize_sindhi_text("١٠٠ گرام") == "100 گرام"

    # Persian/Urdu numerals: ۰۱۲۳۴۵۶۷۸۹
    assert normalize_sindhi_text("سبق ۸") == "سبق 8"
    assert normalize_sindhi_text("۵۰ سيڪڙو") == "50 سيڪڙو"


def test_sindhi_diacritic_stripping():
    """Verify decorative Arabic/Sindhi diacritics are stripped without mangling root characters."""
    # "سِنڌِي" with Kasra and Tashdid -> "سنڌي"
    vowel_text = "سِنڌِي ڊِجِيٽَل"
    clean_text = normalize_sindhi_text(vowel_text, strip_diacritics=True)
    assert clean_text == "سنڌي ڊجيٽل"


def test_sets_query_heuristic_retrieval_success():
    """Regression test: Ensure 'Introduction to Sets' is not falsely rejected by the tutor."""
    # 1. Direct question with lesson context
    req1 = TutorAskRequest(question="سيٽ ڇا آهي ۽ ان جا رڪن ڇا هوندا آهن؟", lesson_id="lesson-math-6-1")
    resp1 = ai_tutor_service.answer_student_question("usr-stu-101", req1)
    assert resp1.is_refused is False
    assert len(resp1.citations) >= 1
    assert resp1.citations[0].lesson_id == "lesson-math-6-1"

    # 2. General question without lesson_id
    req2 = TutorAskRequest(question="سيٽ جا بنيادي تصور بيان ڪريو")
    resp2 = ai_tutor_service.answer_student_question("usr-stu-101", req2)
    assert resp2.is_refused is False
    assert any(c.lesson_id == "lesson-math-6-1" for c in resp2.citations)

    # 3. Bilingual question (English + Sindhi)
    req3 = TutorAskRequest(question="What is a set in class 6 mathematics? سيٽ ڇا آهي؟")
    resp3 = ai_tutor_service.answer_student_question("usr-stu-101", req3)
    assert resp3.is_refused is False
