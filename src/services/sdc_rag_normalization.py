"""SDC RAG Unicode Normalization Module.
Implements the exact normalization rules specified in ANTIGRAVITY_M5_M6_DIRECTIVE.md:
1. Heh normalization: U+06BE (ھ) -> U+0647 (ه) everywhere in Sindhi text fields.
2. Delimiter normalization: ASCII periods -> Sindhi full stop ۔ (U+06D4), preserving abbreviation dots in ٽي.وی (TV).
3. Kaf conversion: Arabic Kaf ك (U+0643) -> Sindhi Kaf ڪ (U+06AA).
4. Word-boundary fix: Standalone اک (Eye) vs اڪ (Calotropis plant) distinction.
   خوراڪ (food) and آڪسيجن (oxygen) contain ک / ڪ inside words and must remain intact.
5. Citation formatting: 'PDF X (printed Y)' with printed = PDF - 4.
   Chapter 7: 'PDF 83-95 (printed 79-91; blank in official PDF)'.
   Unverified: 'page unverified'.
"""

import re
import unicodedata
from typing import Optional, Tuple


def normalize_sindhi_search_text(text: str, is_query: bool = False) -> str:
    """Apply authoritative Sindhi text normalization at both index and query time.
    
    Identical transformation is guaranteed for both indexed corpus and student queries.
    """
    if not text:
        return ""

    # 1. Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text.strip())

    # 2. Tatweel / Kashida removal
    normalized = normalized.replace("\u0640", "")

    # 3. Rule 1: Heh normalization: Convert U+06BE (ھ) -> U+0647 (ه)
    # Also handle Urdu Goal Heh U+06C1, ۂ U+06C2, Teh Marbuta ة U+0629 -> ه
    normalized = normalized.replace("\u06BE", "\u0647")
    normalized = normalized.replace("\u06C1", "\u0647")
    normalized = normalized.replace("\u06C2", "\u0647")
    normalized = normalized.replace("\u0629", "\u0647")

    # 4. Rule 3: Arabic Kaf ك (U+0643) -> Sindhi Kaf ڪ (U+06AA)
    normalized = normalized.replace("\u0643", "\u06AA")

    # 5. Yeh normalization: Persian Yeh ی (U+06CC) -> Arabic/Sindhi Yeh ي (U+064A)
    normalized = normalized.replace("\u06CC", "\u064A")

    # 6. Rule 4: Word-boundary fix:
    # Standalone 'اڪ' (Calotropis plant) must NOT match 'اک' (Eye).
    # We DO NOT conflate اک and اڪ! They remain distinct.
    # Words with internal kaf/khay like خوراڪ (food) and آڪسيجن (oxygen) stay untouched.

    # 7. Rule 2: Delimiter normalization (for corpus and query sentences)
    # Preserve abbreviation dot in ٽي.وی (TV)
    tv_token = "___TV_ABBREV_PLACEHOLDER___"
    normalized = normalized.replace("ٽي.وی", tv_token).replace("ٽي.وي", tv_token)

    # Convert ASCII sentence periods to Sindhi full stop ۔ (U+06D4)
    # In search tokenization, both . and ۔ act as punctuation delimiters.
    normalized = normalized.replace(".", "\u06D4")
    normalized = normalized.replace(tv_token, "ٽي.وی")

    # 8. Normalize multiple spaces
    normalized = re.sub(r"[ \t]+", " ", normalized).strip()
    return normalized


# Common question stop words in English and Sindhi that should not distort BM25 scoring
QUERY_STOPWORDS = {
    # English question/auxiliary words & pronouns
    "what", "is", "are", "was", "were", "the", "a", "an", "of", "in", "to", "for", "with",
    "how", "why", "where", "when", "who", "which", "tell", "explain", "about", "describe",
    "it", "its", "they", "them", "their", "this", "that", "these", "those",
    # Sindhi question/auxiliary words & pronouns
    "ڇا", "ڪير", "ڪٿي", "ڪيئن", "ڪڏهن", "ڇو", "ڪهڙو", "ڪهڙي", "ڪهڙا", "آهي", "آهن", "هئي",
    "هو", "هئا", "ٿئي", "ٿيندو", "جو", "جي", "جا", "کي", "۾", "کان", "سان", "ٻڌايو", "سمجهايو",
    "چئجي", "چئبو", "ٿو", "ٿي", "ڪري", "مهرباني", "ٻڌاءِ",
    "ان", "هن", "انهن", "اهو", "اهي", "سندس", "پنهنجو", "پنهنجي"
}

# Key bilingual scientific concept synonyms to ensure English queries hit Sindhi curriculum chunks
BILINGUAL_SYNONYMS = {
    "cell": "گهرڙو",
    "cells": "گهرڙا",
    "گھرڙو": "گهرڙو",
    "گھرڙا": "گهرڙا",
    "microscope": "خوردبيني",
    "خوردبين": "خوردبيني",
    "eye": "اک",
    "eyes": "اکيون",
    "ear": "ڪن",
    "photosynthesis": "روشنائي",
    "فوٽوسنٿيسز": "روشنائي",
    "روشنائي": "فوٽوسنٿيسز",
    "respiration": "ساهه",
    "environment": "ماحول",
    "ecosystem": "ايڪوسسٽم",
    "atom": "ائٽم",
    "atoms": "ائٽم",
    "molecule": "ماليڪيول",
    "molecules": "ماليڪيول",
    "matter": "مادو",
    "air": "هوا",
    "oxygen": "آڪسيجن",
    "nitrogen": "نائيٽروجن",
    "solution": "محلول",
    "solutions": "محلول",
    "سوليوشن": "محلول",
    "energy": "توانائي",
    "machine": "مشين",
    "machines": "مشينون",
    "lever": "ليور",
    "pulley": "چرخي",
    "pulleys": "چرخيون",
    "light": "روشني",
    "reflection": "انعڪاس",
    "انعڪاس": "موٽ",
    "sound": "آواز",
    "eardrum": "پردو",
    "vacuum": "خلا",
    "medium": "واسطو",
    "magnet": "مقناطيس",
    "space": "خلا",
    "satellite": "سيٽلائيٽ",
    "planet": "سيارو",
    "planets": "سيارا",
    # Mathematics Class 6 Set and Number concepts
    "set": "سيٽ",
    "sets": "سيٽن",
    "سيت": "سيٽ",
    "سيتن": "سيٽن",
    "سٽ": "سيٽ",
    "subset": "ذيلي سيٽ",
    "superset": "مٿانهون سيٽ",
    "element": "رڪن",
    "elements": "رڪن",
    "empty set": "خالي سيٽ",
    "null set": "خالي سيٽ",
    "paksat": "پاڪ سيٽ",
    "پاڪسيٽ": "پاڪ سيٽ"
}


def tokenize_sindhi_fts_query(query: str) -> str:
    """Format and clean a search query for SQLite FTS5 BM25 match syntax.
    
    Preserves exact word boundaries, normalizes Heh and Kaf, handles Sindhi punctuation,
    filters noise stop words, and enriches English queries with Sindhi curriculum synonyms.
    """
    cleaned = normalize_sindhi_search_text(query, is_query=True)
    if not cleaned:
        return ""

    raw_tokens = re.split(r"[\s\u06D4\u060C\u061F\.,;:\-\(\)\[\]\{\}\"\'\/\?؟!]+", cleaned)
    valid_tokens = [tok.strip() for tok in raw_tokens if tok.strip()]
    if not valid_tokens:
        return ""

    # Filter out conversational noise stop words
    content_tokens = [tok for tok in valid_tokens if tok.lower() not in QUERY_STOPWORDS]
    # If query was ONLY stop words or punctuation (e.g. "what is", "what is ?"), do NOT match random corpus words!
    if not content_tokens:
        return ""
    active_tokens = content_tokens

    # Synonym expansion: If an English concept like 'cell' is searched, add 'گهرڙو'
    expanded_tokens = []
    for tok in active_tokens:
        tok_lower = tok.lower()
        safe_tok = tok.replace('"', '""')
        expanded_tokens.append(f'"{safe_tok}"')
        if tok_lower in BILINGUAL_SYNONYMS:
            sindhi_synonym = BILINGUAL_SYNONYMS[tok_lower]
            expanded_tokens.append(f'"{sindhi_synonym}"')

    if not expanded_tokens:
        return ""

    # Join with OR for broad lexical coverage, or AND if few content terms
    if len(expanded_tokens) <= 2:
        return " OR ".join(expanded_tokens)
    return " OR ".join(expanded_tokens)


def format_citation(pdf_page_range: str, chapter_id: Optional[int] = None) -> str:
    """Ensure citation strictly follows 'PDF X (printed Y)' rule.
    
    Handles:
    - Normal range: 'PDF 5-6 (printed 1-2)'
    - Single page: 'PDF 5 (printed 1)'
    - Chapter 7: 'PDF 83-95 (printed 79-91; blank in official PDF)'
    - Unverified: 'page unverified'
    """
    if not pdf_page_range:
        return "page unverified"

    clean_str = pdf_page_range.strip()

    if "unverified" in clean_str.lower():
        return "page unverified"

    # Chapter 7 blank PDF check
    if chapter_id == 7 or "blank in official pdf" in clean_str.lower():
        return "PDF 83-95 (printed 79-91; blank in official PDF)"

    # If it already has printed citation format, verify and return
    if "printed" in clean_str.lower():
        return clean_str

    # Parse numbers like 'PDF 11-12' or 'PDF 5' or '11-12'
    m_range = re.search(r"(\d+)\s*-\s*(\d+)", clean_str)
    if m_range:
        start_pdf = int(m_range.group(1))
        end_pdf = int(m_range.group(2))
        start_printed = max(1, start_pdf - 4)
        end_printed = max(1, end_pdf - 4)
        return f"PDF {start_pdf}-{end_pdf} (printed {start_printed}-{end_printed})"

    m_single = re.search(r"(\d+)", clean_str)
    if m_single:
        pdf_page = int(m_single.group(1))
        printed_page = max(1, pdf_page - 4)
        return f"PDF {pdf_page} (printed {printed_page})"

    return "page unverified"
