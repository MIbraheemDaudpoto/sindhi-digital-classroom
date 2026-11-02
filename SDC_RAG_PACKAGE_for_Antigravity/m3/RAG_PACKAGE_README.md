# SDC RAG Package — STBB Class 6 Science (Sindhi) — built 2026-10-24
Lawful structured companion. NO verbatim textbook text is included anywhere in these files.
All summaries/definitions are original paraphrases from curriculum.md topics + BOOK_COMPANION.md
structure/terms. Retrieval design: lightweight text chunks + PDF page citations only, for
offline Raspberry Pi 5 use. NO query-time screenshot/VLM reading in the retrieval path.

Files:
- rag_chunks_sindhi.jsonl (90 chunks, Ch1 8, Ch2 7, Ch3 6, Ch4 8, Ch5 8, Ch6 7, Ch7 8, Ch8 6, Ch9 7, Ch10 8, Ch11 8, Ch12 9)
  Fields: chunk_id, chapter_id, topic_title_en, topic_title_sd, pdf_page_range, summary_sd, source
  Pagination: printed page = PDF page - 4. pdf_page_range is in PDF pages.
- sindhi_science_glossary.csv (201 rows; 8 terms repeat across chapters with different page refs, e.g. Microscope in Ch1 and Ch10 — intentional per-chapter entries)
  Fields: term_en, term_sd, definition_sd, pdf_page. 20 rows marked pdf_page="unverified" (section page not in companion — never guessed).
- exercise_page_map.csv (39 rows)
  Fields: chapter_id, item_type, topic_en, pdf_page, sos_video_id, sos_video_title
  6 rows have blank sos_video_id (no close-matching SOS video — left blank, not forced).
  2 rows (both Ch8) have pdf_page="unverified" (companion gives no Ch8 exercise page).
  All non-blank video IDs verified to exist in research/videos.csv (11-char IDs, 0 invalid).

Chapter 7 special case:
  Official PDF pages 83-95 (printed 79-91) are blank. All 8 Ch7 chunks carry
  pdf_page_range="PDF 83-95 (blank in official PDF)" and source="curriculum.md SLOs + SOS Ch7 videos (NOT from PDF pages)".
  Ch7 glossary/exercise rows carry the same blank flag. RAG has no blind spot, and nothing claims Ch7 was read from the PDF.

Validation (2026-10-24, merge script):
- JSONL parses: 90 objects, exact field set, every summary_sd contains Sindhi script, 0 Arabic kaf (U+0643) in chunk titles/summaries.
- Exercise video IDs: 0 invalid, 6 blank (deliberate).
- Sources: curriculum.md + BOOK_COMPANION.md + videos.csv only.

Licensing note (separate from these original summaries):
  These files are original summaries, not the book. Using SOS video AUDIO for model training still
  needs SOS written permission (see m3/licensing_review_DRAFT.md: SOS Terms prohibit commercial
  redistribution, no CC licence found). Linking to SOS videos and using these summaries does not
  by itself grant audio-training rights.

## Normalization pass (2026-10-24, pre-M6 vector indexing)
1. Eye: standalone اڪ -> اک (ch2-02, ch2-03 titles + ch2-02 summary, glossary Eye term + definition, companion Ch2 headings). Unit: بنيادي اڪو -> بنيادي ايڪو (ch1-01). Word-boundary only: خوراڪ (18x) and آڪسيجن (17x) untouched, as they correctly contain ک inside the word.
2. Heh: U+06BE (ھ) -> U+0647 (ه) in all Sindhi fields of chunks + glossary (and companion). گھرڙو -> گهرڙو, so a student typing گهرڙو matches BM25. Post-fix U+06BE count = 0 in all RAG files.
3. Delimiter: ASCII sentence periods -> Sindhi full stop ۔ (U+06D4) in Sindhi summaries/definitions (189 chunk periods + 83 glossary periods converted; ch10-12 already used ۔). Exceptions kept deliberately: the abbreviation dots in ٽي.وی (TV, ch8-04) and the sentence terminator after the chemical symbol C in ch5-03, which was also converted to ۔. Post-fix ASCII periods in summaries = 1, the single abbreviation dot in ٽي.وی (TV, ch8-04).
4. Pages: every non-unverified citation normalized to "PDF X (printed Y)" with Printed = PDF - 4, arithmetic verified for all 90 chunks (e.g. PDF 5-6 (printed 1-2); Ch7: PDF 83-95 (printed 79-91; blank in official PDF)). Glossary: 181 normalized + 20 unverified. Exercise map: 37 normalized + 2 unverified. UI display rule for rural students/teachers: always show BOTH numbers, e.g. "PDF 24 (printed 20)".
