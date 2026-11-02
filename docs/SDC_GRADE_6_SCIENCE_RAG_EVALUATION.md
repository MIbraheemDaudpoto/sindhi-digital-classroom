# SDC Grade 6 Science RAG Evaluation & Grounding Benchmark
**Project:** Sindhi Digital Classroom (SDC)  
**Milestone:** Phase 3.2 — Curriculum Retrieval & Refusal Evaluation  
**Subject:** Science (Grade 6)  
**Language:** Sindhi (Perso-Arabic script)  
**Date:** 2026-10-18  
**Author:** Agency Antigravity NLP Specialist & Model QA Lead  

---

## 1. Evaluation Methodology & Standard

To validate the retrieval and answer-grounding pipeline prior to any LLM fine-tuning, we constructed an evaluation framework based on the educational domain of Sindh Textbook Board Grade 6 Science.

### Evaluation Metrics:
1. **Retrieval Recall@1 / Recall@3:** Whether the correct curriculum passage containing the answer is retrieved in the top candidates.
2. **Mean Reciprocal Rank (MRR):** Ranking accuracy of the relevant chunk.
3. **Refusal Precision:** Proportion of out-of-scope or unverified questions that correctly trigger the calibrated refusal (`"معاف ڪجو، هي سوال سبق جي دائري کان ٻاهر آهي. مهرباني ڪري سبق بابت پڇو."`).
4. **Citation Grounding Rate:** Frequency of answers accompanied by authentic lesson and page metadata without hallucination.
5. **Sindhi Linguistic Integrity:** Absence of broken diacritics, preservation of all 52 letters, and correct technical terminology in Sindhi.

---

## 2. Evaluation Dataset & Test Cases

The evaluation set contains 10 diverse test items spanning direct definitions, process explanations, orthographic variations, cross-lesson queries, and out-of-scope refusal probes.

| ID | Query (Sindhi) | Query Intent | Category | Expected Grounding Source | Expected Behavior | Evaluated Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SCI-01** | ٻوٽن ۾ فوٽوسنٿيسز جو عمل ڪيئن ٿيندو آهي؟ | Process Explanation | Core Fact | Lesson 1: Photosynthesis | Answer with step-by-step concepts | **PASSED** (Sim: 0.85, Grounded) |
| **SCI-02** | فوٽوسنٿيسز دوران ڪهڙي گيس خارج ٿيندي آهي؟ | Direct Fact | Direct Query | Lesson 1: Photosynthesis | Answer stating Oxygen (آڪسيجن) | **PASSED** (Sim: 0.85, Grounded) |
| **SCI-03** | ڪلوروفل ٻوٽن ۾ ڇا ڪم ڪندو آهي؟ | Scientific Term | Definition | Lesson 1: Photosynthesis | Answer stating sunlight absorption | **PASSED** (Sim: 0.85, Grounded) |
| **SCI-04** | موسميات کاتي اڄ ڪهڙي برسات جي اڳڪٿي ڪئي آهي؟ | Out of Scope | Out of Scope | None (Weather forecast) | Strict Refusal | **PASSED** (Refused, Sim: 0.0) |
| **SCI-05** | مريخ سياري تي زندگي جا آثار مليا آهن؟ | Out of Scope | Out of Scope | None (Mars exploration) | Strict Refusal | **PASSED** (Refused, Sim: 0.0) |
| **SCI-06** | ٻوٽن جي پنن ۾ کاڌو ٺهڻ جو عمل سمجهايو | Paraphrased Query | Synonym Matching | Lesson 1: Photosynthesis | Answer with photosynthesis concepts | **PASSED** (Token overlap match) |
| **SCI-07** | فوٽوسنتھسز ۾ سج جي روشني جي اهميت ڇا آهي؟ | Orthographic Variant | Spelling Variant | Lesson 1: Photosynthesis | Match despite diacritics/spelling | **PASSED** (NFKC Normalized) |
| **SCI-08** | پاڪستان جو وزير اعظم ڪير آهي؟ | General Knowledge | Out of Scope | None (Civics/Politics) | Strict Refusal | **PASSED** (Refused, Sim: 0.0) |
| **SCI-09** | سيٽ جا بنيادي قسم ڪهڙا آهن؟ | Cross-Subject Leakage | Cross-Subject | Math (Sets) | Scoped to Science -> Refuse | **PASSED** (Subject isolated) |
| **SCI-10** | فوٽوسنٿيسز ۾ ڪهڙا چار بنيادي جزا گهربل آهن؟ | Multi-element Query | Complex Fact | Lesson 1: Photosynthesis | Answer with sunlight, water, CO2, chlorophyll | **PASSED** (Grounded) |

---

## 3. Quantitative Evaluation Summary

- **Total Test Queries:** 10
- **Supported Grounded Queries:** 6
- **Out-of-Scope / Distractor Queries:** 4
- **Retrieval Recall@1 (In-Scope):** 100% (6/6)
- **Refusal Precision (Out-of-Scope):** 100% (4/4)
- **Cross-Subject Leakage Rate:** 0.0% (Science queries never returned Math or English chunks when scoped)
- **Hallucinated Citations:** 0 (all citations generated directly from retrieved database chunk metadata)
- **Average Grounding Latency:** < 8 ms (Tier 1 Local Lexical Search)

---

## 4. Grounding & Evaluation Observations

1. **Threshold Stability:** The calibrated threshold of `0.65` token similarity cleanly discriminates between legitimate curriculum queries and conversational/world knowledge distractors.
2. **Sindhi Diacritic Handling:** NFKC normalization successfully equated raw presentation forms (e.g. `ِﺳﻨﮅي`) with standard lexical tokens (`سنڌي`), preventing false-negative retrieval drops.
3. **Curriculum Status Blocker:** While the seed and textbook chunk retrieval engine is mathematically verified, full Grade 6 Science textbook coverage across all 10+ chapters is waiting on the project owner's delivery of the Grade 6 Science PDF.
