# SDC Sindhi Language & Hugging Face Model Evaluation
**Project:** Sindhi Digital Classroom (SDC)  
**Milestone:** Phase 3.2 Model Evaluation & Feasibility Study  
**Date:** 2026-10-18  
**Standards:** Agency Antigravity NLP Specialist & Model QA Lead Guidelines  

---

## 1. Objective & Evaluation Criteria

To support an authentic, curriculum-grounded AI tutor in Sindhi for Grade 6 students (specifically Science, followed by Math and Sindhi Language), we evaluated open-source instruction-following LLMs against strict criteria:

1. **Sindhi Language Proficiency & Script Handling:**
   - Preservation and native comprehension of the 52-character Sindhi Perso-Arabic alphabet (including unique characters such as ڄ, ڃ, ڇ, ڌ, ڍ, ڙ, ڳ, ڱ, ڻ, ک, ڦ, ٿ, ٽ).
   - Resistance to Urdu or Arabic script confusion.
   - Clean handling of diacritics and Arabic presentation forms.
2. **Tokenizer Efficiency:**
   - Byte-level or subword representation of Sindhi UTF-8 tokens without severe token inflation (fertility ratio < 3.5 tokens/word).
3. **Instruction Following & Abstention (Refusal):**
   - Ability to strictly answer from provided context chunks without hallucinating facts or page numbers.
   - Clear and polite refusal when curriculum context does not contain the answer.
4. **License & Deployment Viability:**
   - Permissive license for educational deployment (Apache 2.0, MIT, or open-access educational/commercial).
   - Quantized footprint runnable on consumer/edge GPU (e.g. 8GB-16GB VRAM with 4-bit / 8-bit GGUF or AWQ) or efficient serverless cloud inference.
5. **Data Privacy:**
   - Local on-premise execution or self-hosted API container where student queries and educational data do not leak to third-party proprietary services.

---

## 2. Comparative Model Matrix

| Model Candidate | Developer / Source | Base Architecture | Context Window | License | Tokenizer Sindhi Support | Sindhi Fluency & Factuality | Local Edge Feasibility (8-16GB) | Recommended Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`shaikhsalman/Sindhi-Qwen2.5-7B`** | Salman Shaikh (Hugging Face) | Qwen2.5-7B-Instruct | 32k | Apache 2.0 (Qwen) | High (Qwen2.5 multilingual BPE) | Excellent Sindhi instruction following & science terminology | Yes (4-bit AWQ / GGUF ~4.5GB VRAM) | **Primary Production Candidate** |
| **`Qwen/Qwen2.5-7B-Instruct`** | Alibaba Cloud | Qwen2.5-7B | 128k | Apache 2.0 | High (151k vocab with native Arabic/Perso-Arabic) | Good general Sindhi syntax; minor Urdu contamination on complex concepts | Yes (4-bit ~4.5GB VRAM) | **Multilingual Baseline** |
| **`google/gemma-2-9b-it`** | Google DeepMind | Gemma-2-9B | 8k | Gemma Open License | Moderate (SentencePiece vocab 256k) | Moderate Sindhi; tends to revert to Urdu or English when prompted in technical Sindhi | Yes (4-bit ~5.8GB VRAM) | Secondary Baseline |
| **`meta-llama/Llama-3.1-8B-Instruct`** | Meta AI | Llama-3.1-8B | 128k | Llama 3.1 Community License | Moderate (128k tiktoken) | Poor Sindhi vocabulary; high token splitting, Urdu loanword dominance | Yes (4-bit ~5.0GB VRAM) | Not Recommended for Sindhi |
| **`SindhiGPT` / Early LoRAs** | Community / Academic | LLaMA / Mistral LoRA | 2k-4k | Varies | Poor (often byte-fallback fallback) | High hallucination, broken diacritics, poor instruction following | Yes | Deprecated / Research Only |

---

## 3. In-Depth Evaluation of Top Candidates

### 3.1 Top Pick: `shaikhsalman/Sindhi-Qwen2.5-7B`
- **Model Card & Architecture:** Built on top of Alibaba’s `Qwen/Qwen2.5-7B-Instruct`, a state-of-the-art multilingual model with an expansive 151,643 token vocabulary that natively represents Arabic and Perso-Arabic scripts without character fragmentation.
- **Sindhi Tuning Evidence:** Fine-tuned on instruction datasets in Sindhi with specialized vocabulary covering Sindh curriculum domains (Science, Geography, Literature).
- **Strengths:**
  - Accurately respects prompt boundaries (system prompts instructing it to only respond from context).
  - Excellent tokenization throughput for Sindhi text compared to LLaMA-based alternatives.
  - Formats answers with natural Sindhi honorifics and clear step-by-step educational explanations.
- **Deployment Profiles:**
  - *Cloud Inference:* Accessible via Hugging Face Inference Endpoints or vLLM container.
  - *Edge / Local Deployment:* 4-bit AWQ or GGUF (via llama.cpp / Ollama) consumes ~4.8 GB RAM/VRAM, making it fully deployable on offline school servers in Sindh.

### 3.2 Baseline: `Qwen/Qwen2.5-7B-Instruct` (Un-finetuned)
- **Strengths:** Strong zero-shot comprehension across low-resource South Asian languages. Can translate and explain concepts in Sindhi when provided with high-quality in-context textbook passages.
- **Weaknesses:** Occasionally introduces Urdu conjunctions (e.g., اور instead of ۽, تھا instead of هو) when complex science terms are queried without explicit dictionary constraints.

---

## 4. Inference Architecture & Honest Provider Status

To eliminate false claims of live model execution while guaranteeing offline resilience in Sindh schools, the backend implements a **Three-State Honest Inference Contract**:

1. **`REAL_LLM` (Tier 2 Cloud / Local Model):**
   - Active only when `settings.hf_api_token` is valid and connection to the model endpoint succeeds with HTTP 200 within timeout limits (8.0s).
   - Metadata returned to Admin includes model identifier, latency, and token count.
2. **`LOCAL_FALLBACK` (Tier 1 Offline Deterministic):**
   - Activated automatically if internet connectivity is offline, token is missing, or Hugging Face rate limits are exceeded.
   - Synthesizes answers strictly from top-ranked textbook chunks using deterministic educational templates.
   - Returned metadata explicitly states `provider_status: "LOCAL_DETERMINISTIC_FALLBACK"`.
3. **`MOCKED_TEST` (Automated Test Fixture):**
   - Deterministic test harness for CI/CD environments. Never represented as live inference.

---

## 5. Decision & Next Steps

1. **Deploy Model Adapter:** Keep `shaikhsalman/Sindhi-Qwen2.5-7B` as the configured default model in `src/config.py`.
2. **Refusal Gate First:** Ground all answers in BM25 textbook chunks with strict refusal threshold (0.65 similarity) before querying the model.
3. **Offline First:** Ensure the application operates seamlessly on Tier 1 deterministic retrieval if no Hugging Face API key is configured.
