# SDC Fine-Tuning Feasibility & Post-Training Proposal
**Project:** Sindhi Digital Classroom (SDC)  
**Milestone:** Phase 3.2 Post-Baseline Architecture Strategy  
**Date:** 2026-10-18  
**Standards:** Agency Antigravity LLM Post-Training Engineer & AI Data Remediation Guidelines  
**Status:** PROPOSAL ONLY — DO NOT INITIATE TRAINING OR DOWNLOAD WEIGHTS WITHOUT EXPLICIT APPROVAL  

---

## 1. Executive Feasibility Assessment

### Current Baseline Verdict:
The current **RAG-first architecture** with transparent lexical retrieval and strict prompt grounding achieves 100% precision on refusal and zero citation hallucination on verified test items. 

**Immediate Fine-Tuning is NOT Justified at this stage.** Fine-tuning must not be used as a substitute for supplying the actual textbook. RAG remains the mandatory single source of truth for textbook facts, page numbers, and lesson citations.

### When Fine-Tuning Will Become Justified:
Fine-tuning (specifically Parameter-Efficient Fine-Tuning via LoRA/QLoRA) should only be approved when:
1. The full Grade 6 Science textbook PDF is ingested into the database.
2. A human-in-the-loop review of the base model reveals persistent stylistic awkwardness, Urdu loanword bleeding, or failure to follow student-friendly pedagogical tone despite system prompting.

---

## 2. Technical Fine-Tuning Architecture (If Approved)

### 2.1 Base Model & License
- **Base Model:** `Qwen/Qwen2.5-7B-Instruct` or `shaikhsalman/Sindhi-Qwen2.5-7B`
- **License:** Apache 2.0 (Permissive for commercial, non-profit, and educational deployment).
- **Justification:** Native 151k token vocabulary with high Perso-Arabic token density and strong multilingual grounding.

### 2.2 Supervised Fine-Tuning (SFT / QLoRA) Specifications
- **Target Modules:** `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- **LoRA Hyperparameters:**
  - `r = 16`, `lora_alpha = 32`, `lora_dropout = 0.05`
  - Quantization: 4-bit NormalFloat (NF4) with Double Quantization via `bitsandbytes`
- **Hardware Requirements:** Single 24GB VRAM GPU (NVIDIA RTX 3090 / 4090 or A10G cloud instance). Estimated training time for 1,500 instruction pairs: ~2.5 hours. Estimated cloud cost: < $5.00.

### 2.3 Training Dataset Construction & Quality Rubric
- **Target Size:** 1,200 - 1,800 verified Sindhi educational instruction pairs.
- **Dataset Composition:**
  - 40% Grade 6 Science concept explanations with step-by-step reasoning.
  - 25% Textbook-grounded Question-Answering pairs citing explicit paragraphs.
  - 20% Strict refusal examples (polite rejection of out-of-scope, unverified, or harmful queries).
  - 15% Conversational student encouragement and clarification dialogues in culturally authentic Sindhi.
- **Data Remediation Rules:**
  - Strictly enforce NFKC Unicode normalization.
  - Remove all broken diacritics.
  - Require native Sindhi speaker review for each QA pair.
  - Split: 80% Train, 10% Validation, 10% Held-Out Test.

---

## 3. Evaluation & Rollback Plan

1. **Before/After Automated Benchmark:**
   - Run the 10-item Grade 6 Science Grounding Benchmark (`docs/SDC_GRADE_6_SCIENCE_RAG_EVALUATION.md`).
   - SFT candidate must achieve >= 95% refusal precision and zero citation hallucination.
2. **Human Evaluation Rubric:**
   - 3 native Sindhi educators score 50 blinded answers for:
     - Factuality (1-5)
     - Sindhi Linguistic Naturalness (1-5)
     - Pedagogical Appropriateness for 11-12 year old students (1-5)
3. **Rollback Safety:**
   - The LoRA adapter will exist as an optional pluggable weight file. If regression occurs in production, disabling the adapter reverts the system to Tier 1 / Base Model within 1 configuration flag change (`settings.ai_lora_enabled = False`).

---

## 4. Next Step
**Await explicit project owner approval.** Do not start training runs, download model checkpoints, or incur external GPU billing.
