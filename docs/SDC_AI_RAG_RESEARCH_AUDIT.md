# SDC AI & RAG RESEARCH AUDIT REPORT
**Conducted by Agency Subagents: `agency-ai-engineer`, `agency-rag-pipeline-engineer`, `agency-prompt-engineer`**
**Repository:** `D:\Ai Agents\agency-agents\sindhi-digital-classroom`
**Date:** 2026-10-17

---

## 1. Executive Summary

This audit evaluates the current artificial intelligence, retrieval-augmented generation (RAG), and prompt engineering architecture of the Sindhi Digital Classroom (SDC). The platform features robust groundwork with Unicode-safe Sindhi NLP tokenization and calibrated refusal thresholds, but operates in a constrained hybrid mode pending external PDF textbooks and remote inference credentials.

---

## 2. Specialized Subagent Findings

### A. AI Engineering Audit (`agency-ai-engineer`)
1. **Script Normalization (`src/services/sindhi_nlp.py`):**
   - Correctly handles all 52 letters of the Sindhi Perso-Arabic alphabet.
   - Converts non-standard variants:
     - Arabic Kaf (`ك`, U+0643) $\rightarrow$ Sindhi Swash Kaf (`ڪ`, U+06AA)
     - Persian Yeh (`ی`, U+06CC) $\rightarrow$ Sindhi Yeh (`ي`, U+064A)
     - Urdu Heh (`ہ`, U+06C1) $\rightarrow$ Sindhi Heh (`ه`, U+0647)
   - Converts Eastern Arabic and Urdu numerals (`٠-٩`, `۰-۹`) to standard ASCII digits for deterministic math parsing.
2. **Deterministic Evaluation:**
   - Objective questions (MCQs) use verified option keys.
   - Mathematical and numerical problems extract numbers via regex and compute exact floating-point tolerances via `math.isclose(rel_tol=1e-2)` rather than relying on hallucination-prone LLM token generation.
3. **Model Infrastructure:**
   - Architecture has pluggable adapters for `shaikhsalman/Sindhi-Qwen2.5-7B`.
   - Local CPU runtime avoids loading 7B unquantized weights directly into host memory, which prevents memory exhaustion on developer machines.

### B. RAG Pipeline Audit (`agency-rag-pipeline-engineer`)
1. **Retrieval Mechanism:**
   - Uses weighted Jaccard token overlap similarity with diacritic stripping and Sindhi educational stopwords elimination.
   - Refusal threshold is calibrated at `0.25`: queries falling below this similarity score trigger strict, respectful refusals in Sindhi (`معاف ڪجو، هي سوال سبق جي دائري کان ٻاهر آهي...`).
2. **Ingestion Pipeline Architecture:**
   - Defined directory structure: `data/curriculum_pdfs/class_<N>/<subject>/`.
   - Ingestion manifest schema defined in `data/curriculum_manifest.json`.
   - **Current Limitation:** Official STBB textbook PDFs have not yet been provided by the user. The system currently searches against curated synthetic chunks for Class 6 units. Full textbook RAG remains incomplete until real PDFs are deposited and parsed.

### C. Prompt Engineering Audit (`agency-prompt-engineer`)
1. **System Prompt Formulation (`src/services/ai_provider.py`):**
   - Role defined clearly as an expert Sindh Textbook Board educator.
   - Explicit guardrails against hallucinating outside approved lesson text.
   - Demands step-by-step reasoning for science and math inquiries.
2. **Quality Assurance Gate:**
   - Submissions receiving low evaluation confidence are set to `NEEDS_RETRY` rather than assigning simulated or arbitrary grades.
   - Background worker idempotently re-processes retries without duplicating grade records or spamming student notifications.

---

## 3. Prioritized Recommendations for Full Production

1. **Textbook Corpus Deployment:**
   - User must supply official STBB textbook PDFs into `data/curriculum_pdfs/`.
   - Install `pypdf` or `pdfplumber` for automated text extraction and chapter indexing.
2. **Cloud AI Inference Activation:**
   - Configure `HF_API_TOKEN` or `GEMINI_API_KEY` in `.env` to enable remote generative answers while retaining the local rule-based engine as an automatic fallback.
3. **Vector Embeddings Migration:**
   - When moving from prototype to high-concurrency production (>10,000 students), migrate the sparse token overlap index to dense multilingual embeddings (e.g. `multilingual-e5-small` or `text-embedding-3-small` in SQLite via `sqlite-vec`).
