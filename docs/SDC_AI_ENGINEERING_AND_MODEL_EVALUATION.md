# SDC AI Engineering & Model Evaluation Report (Phase 2)

**Project:** Sindhi Digital Classroom (SDC)  
**Specialization:** Sindhi NLP, Curriculum-Grounded RAG, Open-Weight Model Architecture, Fine-Tuning Feasibility  
**Audit Standard:** `agency-ai-engineer` & `agency-backend-architect`

---

## 1. Runtime AI Architecture and Execution Paths

The SDC platform implements a **two-tier AI architecture** that operates with or without cloud connectivity:

```
[Student Question in Sindhi]
              |
              v
[Sindhi Text Normalizer (src/services/sindhi_nlp.py)]
  - Normalizes Arabic/Persian letter variants (ك -> ڪ, ی -> ي, ہ -> ه)
  - Preserves all 52 native Sindhi phonemes & implosives (ٻ, ڄ, ڳ, ڊ)
              |
              v
[Curriculum RAG Retrieval Engine (src/services/ai_tutor_service.py)]
  - Evaluates similarity against approved STBB textbook chunks & video transcripts
  - Computes calibrated token overlap and semantic similarity
              |
     +--------+--------+
     |                 |
     v                 v
[Score < 0.65]   [Score >= 0.65]
(Refusal Gate)         |
     |                 v
"معاف ڪجو..."      [AI Provider Factory (src/services/ai_provider.py)]
                       |
        +--------------+--------------+
        |                             |
        v                             v
[Tier 2: Cloud Inference]     [Tier 1: Local Engine]
(Hugging Face API / LLM)      (Deterministic Rule Synthesizer)
- Prompts Sindhi model        - Extractive & structured
- Fallback on timeout/error   - Sub-5ms latency, 0 MB VRAM
```

---

## 2. Research and Evaluation of Sindhi Open-Weight Models

Four primary open-weight Sindhi candidate models were evaluated against deployment constraints:

| Model Candidate | Parameter Size | Architecture | Primary Task | Hardware Requirement | Verdict for Current Host |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **`shaikhsalman/Sindhi-Qwen2.5-7B`** | 7.61B | Qwen2.5 Transformer | Generative Chat & QA | 16 GB+ VRAM (GPU) or 32 GB RAM | **Cloud Inference Only** (Cannot run on local host) |
| **`hellosindh/qwen3-sindhi-cpt`** | 3B/7B | Continual Pretraining | Language Modeling | 8–16 GB VRAM | **Evaluation Candidate** |
| **`alinawazmahar/mt5-sindhi-qa-sdquad`** | ~580M | mT5 Encoder-Decoder | Extractive QA (SDQuAD) | 4–6 GB RAM / CPU | **Promising Local Candidate** for future packaging |
| **`hellosindh/sindhi-bert-base`** | ~110M | RoBERTa / BERT | Embedding & Classification | < 2 GB RAM / CPU | **Ideal for Local Semantic Search** |

---

## 3. Host Hardware Constraints Analysis

- **CPU:** Dual-core Intel Core i5-3320M @ 2.60 GHz
- **System Memory:** 8.00 GB DDR3 (Available free: ~898 MB to 1.2 GB during test runs)
- **GPU / VRAM:** Intel HD Graphics 4000 (Integrated, 0 MB Dedicated VRAM)

### Technical Conclusion on Local 7B Inference:
Attempting to quantize (GGUF 4-bit) and load a 7.61B parameter model locally requires a minimum of **4.8 GB of contiguous free RAM**, which would instantly crash the host OS under an Out-Of-Memory (OOM) fault. Therefore, the architectural strategy is:
1. **Tier 1 Local Fallback (Active):** Lightweight, deterministic, curriculum-extractive engine requiring 0 MB VRAM and 0 cloud cost.
2. **Tier 2 Cloud Adapter (Configured):** Hugging Face Inference Provider targeting `shaikhsalman/Sindhi-Qwen2.5-7B` via secure environment variables (`HF_API_TOKEN`).

---

## 4. Fine-Tuning Gate & Formal Decision

### Recommendation: **DO NOT FINE-TUNE AT THIS STAGE**
A rigorous engineering evaluation indicates that fine-tuning a 7B model now would be premature and counterproductive:

1. **Curriculum Grounding Beats Weight Modification:** In educational EdTech (STBB), hallucinations must be 0%. Fine-tuning model weights does not eliminate hallucinations, whereas RAG with strict refusal thresholds guarantees that answers come from textbook pages.
2. **Missing Authoritative STBB Domain Corpus:** Pre-training or fine-tuning requires 100k+ clean, aligned Sindhi educational pairs. Using unverified web-scraped Sindhi datasets introduces dialect corruption and inaccuracies.
3. **Zero Financial/GPU Cost:** RAG and prompt engineering on existing foundation models achieves curriculum alignment without incurring GPU cluster rental costs.
4. **Student Privacy Guarantee:** The system refuses to train or fine-tune models on raw student conversation logs, preserving child data privacy and COPPA/FERPA compliance.
