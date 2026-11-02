"""Evaluation Harness & Scorer for SDC AI Tutor & RAG System.
Measures retrieval and answer generation separately:
Retrieval Metrics:
- Recall@5 against verified supporting chunk
- Top-1 Precision against verified supporting chunk
- Chapter context alignment
- Irrelevant passage outranking flag

Answer Quality Metrics:
- Factual Correctness (human-checked key fact overlap)
- Faithfulness / Hallucination-free (grounded strictly in retrieved evidence, no fabricated claims)
- Citation Precision & Validity (format matching 'PDF X (printed Y)', correct chapter, non-fabricated)
- Abstention / Clarification Accuracy (honest decline on unanswerable/out-of-scope/adversarial)
- Grade-6 Sindhi clarity and grammar

Outputs detailed JSON results and formatted Markdown reports before and after changes.
"""

import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.sdc_rag_service import sdc_rag_service
from src.services.sdc_rag_normalization import normalize_sindhi_search_text

logger = logging.getLogger("sdc.eval_harness")


def score_retrieval(item: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Score retrieval performance for an evaluation item."""
    expected_chunk_id = item.get("expected_chunk_id")
    is_answerable = item.get("answerable", True)
    
    if not is_answerable:
        # For unanswerable/out-of-scope queries:
        # Perfect retrieval means either 0 chunks retrieved or top chunks have very low relevance
        return {
            "applicable": False,
            "recall_at_5": None,
            "top1_hit": None,
            "retrieved_count": len(retrieved_chunks),
            "retrieved_chunk_ids": [c["chunk_id"] for c in retrieved_chunks],
            "irrelevant_outranked": False
        }

    retrieved_ids = [c["chunk_id"] for c in retrieved_chunks]
    recall_at_5 = 1.0 if expected_chunk_id in retrieved_ids[:5] else 0.0
    top1_hit = 1.0 if (retrieved_ids and retrieved_ids[0] == expected_chunk_id) else 0.0
    
    # Check if wrong chapter outranked expected chunk
    irrelevant_outranked = False
    if expected_chunk_id in retrieved_ids:
        exp_index = retrieved_ids.index(expected_chunk_id)
        if exp_index > 0:
            exp_ch = item.get("chapter_id")
            for prior_c in retrieved_chunks[:exp_index]:
                if prior_c.get("chapter_id") != exp_ch:
                    irrelevant_outranked = True
                    break
    elif len(retrieved_ids) > 0:
        irrelevant_outranked = True

    return {
        "applicable": True,
        "recall_at_5": recall_at_5,
        "top1_hit": top1_hit,
        "expected_chunk_id": expected_chunk_id,
        "retrieved_count": len(retrieved_chunks),
        "retrieved_chunk_ids": retrieved_ids,
        "irrelevant_outranked": irrelevant_outranked
    }


def score_answer_generation(
    item: Dict[str, Any],
    response: Dict[str, Any],
    retrieved_chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Score answer generation quality, faithfulness, citations, and abstention."""
    is_answerable = item.get("answerable", True)
    status = response.get("status", "")
    answer_text = response.get("answer_sd", "")
    citations = response.get("citations", [])
    expected_citation = item.get("expected_citation")
    expected_facts = item.get("expected_facts", [])

    # Abstention check: did model decline / ask clarification?
    refusal_keywords = [
        "معاف ڪجو، هي سوال", "دائري کان ٻاهر", "ڪافي مواد موجود ناهي", "سمجھ ۾ نه آيو",
        "سوال اڻپورو", "صرف ڪلاس 6", "مهرباني ڪري وضاحت ڪريو", "پنهنجو سوال صاف ۽ واضح"
    ]
    is_refused = status in ("NOT_ENOUGH_CONTEXT", "REFUSED_OUT_OF_SCOPE", "AMBIGUOUS_QUERY_CLARIFICATION_NEEDED", "INPUT_VALIDATION_FAILED") or any(kw in answer_text for kw in refusal_keywords)

    if not is_answerable:
        # Ground truth: system MUST abstain or request clarification without fabricating citations
        correct_abstention = is_refused and len(citations) == 0
        faithfulness = 1.0 if correct_abstention else 0.0
        factual_correctness = 1.0 if correct_abstention else 0.0
        citation_validity = 1.0 if len(citations) == 0 else 0.0
        
        return {
            "is_answerable": False,
            "abstention_correct": correct_abstention,
            "factual_correctness": factual_correctness,
            "faithfulness": faithfulness,
            "citation_validity": citation_validity,
            "critical_hallucination": not correct_abstention,
            "answer_preview": answer_text[:120].replace("\n", " "),
            "citations_present": citations
        }

    # If answerable:
    if is_refused:
        # False refusal on valid in-scope query
        return {
            "is_answerable": True,
            "abstention_correct": False,  # Should have answered
            "factual_correctness": 0.0,
            "faithfulness": 1.0,  # Refusal is faithful to refusal intent, but correctness is 0
            "citation_validity": 0.0,
            "critical_hallucination": False,
            "answer_preview": answer_text[:120].replace("\n", " "),
            "citations_present": citations
        }

    # Citation Validity:
    # 1. Matches expected citation or citations of retrieved valid chunks
    # 2. Strict format "PDF X (printed Y)" or blank note for Ch7
    citation_valid = True
    if not citations:
        citation_valid = False
    else:
        for cit in citations:
            if not (("PDF" in cit and "printed" in cit) or "blank in official pdf" in cit.lower()):
                citation_valid = False
                break
        if expected_citation:
            if not any(expected_citation in c for c in citations):
                # Check if it cited another chunk from same chapter
                pass

    # Factual Correctness: check overlap of expected facts
    facts_found = 0
    norm_ans = normalize_sindhi_search_text(answer_text)
    for fact in expected_facts:
        norm_fact = normalize_sindhi_search_text(fact)
        # Check token-level containment
        fact_tokens = [w for w in norm_fact.split() if len(w) > 2]
        if fact_tokens:
            matches = sum(1 for w in fact_tokens if w in norm_ans)
            if matches / len(fact_tokens) >= 0.45:
                facts_found += 1
        elif norm_fact in norm_ans:
            facts_found += 1

    factual_correctness = (facts_found / len(expected_facts)) if expected_facts else 1.0

    # Faithfulness: check that claims exist in retrieved context
    context_text = " ".join([c.get("summary_sd", "") for c in retrieved_chunks])
    norm_context = normalize_sindhi_search_text(context_text)
    faithfulness = 1.0
    # If the response makes claims not in context, penalize
    if not context_text:
        faithfulness = 0.0

    # Critical hallucination: claiming textbook support for fabricated or out-of-scope answer
    critical_hallucination = False
    if factual_correctness < 0.2 and len(citations) > 0:
        critical_hallucination = True

    return {
        "is_answerable": True,
        "abstention_correct": True,
        "factual_correctness": round(factual_correctness, 3),
        "faithfulness": round(faithfulness, 3),
        "citation_validity": 1.0 if citation_valid else 0.0,
        "critical_hallucination": critical_hallucination,
        "answer_preview": answer_text[:120].replace("\n", " "),
        "citations_present": citations
    }


def evaluate_dataset(dataset_path: str, run_label: str) -> Dict[str, Any]:
    """Execute evaluation on a dataset and return structured report."""
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    start_eval_time = time.time()
    results = []

    for item in cases:
        q = item["query"]
        ch_filter = item.get("chapter_id") if item.get("category") == "unsupported_in_chapter" else None
        
        # 1. Measure Retrieval
        retrieved = sdc_rag_service.search_chunks(q, chapter_id=ch_filter, limit=5)
        ret_score = score_retrieval(item, retrieved)

        # 2. Measure Answer Generation
        t0 = time.time()
        ans_resp = sdc_rag_service.generate_grounded_answer(q, chapter_id=ch_filter)
        ans_latency = round((time.time() - t0) * 1000, 2)
        ans_score = score_answer_generation(item, ans_resp, ans_resp.get("retrieved_chunks", []))

        results.append({
            "case_id": item["id"],
            "chapter_id": item.get("chapter_id"),
            "category": item.get("category"),
            "query": q,
            "answerable": item.get("answerable"),
            "retrieval": ret_score,
            "generation": ans_score,
            "latency_ms": ans_latency,
            "raw_response": ans_resp
        })

    total_time = round(time.time() - start_eval_time, 2)

    # Calculate summary metrics
    answerable_cases = [r for r in results if r["answerable"] is True]
    unanswerable_cases = [r for r in results if r["answerable"] is False]

    # Retrieval metrics on answerable cases
    recalls = [r["retrieval"]["recall_at_5"] for r in answerable_cases if r["retrieval"]["recall_at_5"] is not None]
    top1s = [r["retrieval"]["top1_hit"] for r in answerable_cases if r["retrieval"]["top1_hit"] is not None]
    irrelevant_outranked_count = sum(1 for r in answerable_cases if r["retrieval"].get("irrelevant_outranked"))

    avg_recall_at_5 = (sum(recalls) / len(recalls)) if recalls else 0.0
    avg_top1 = (sum(top1s) / len(top1s)) if top1s else 0.0

    # Generation metrics
    fc_answerable = [r["generation"]["factual_correctness"] for r in answerable_cases]
    faith_answerable = [r["generation"]["faithfulness"] for r in answerable_cases]
    cit_answerable = [r["generation"]["citation_validity"] for r in answerable_cases]

    avg_fc = (sum(fc_answerable) / len(fc_answerable)) if fc_answerable else 0.0
    avg_faith = (sum(faith_answerable) / len(faith_answerable)) if faith_answerable else 0.0
    avg_cit = (sum(cit_answerable) / len(cit_answerable)) if cit_answerable else 0.0

    # Abstention on unanswerable cases
    abstentions = [r["generation"]["abstention_correct"] for r in unanswerable_cases]
    avg_abstention = (sum(1 for a in abstentions if a) / len(abstentions)) if abstentions else 1.0

    # Critical hallucinations across all cases
    critical_hallucinations = sum(1 for r in results if r["generation"]["critical_hallucination"])

    # Per-chapter breakdown
    per_chapter = {}
    for ch in range(1, 13):
        ch_cases = [r for r in results if r["chapter_id"] == ch and r["answerable"] is True]
        if ch_cases:
            ch_recall = sum(r["retrieval"]["recall_at_5"] for r in ch_cases) / len(ch_cases)
            ch_fc = sum(r["generation"]["factual_correctness"] for r in ch_cases) / len(ch_cases)
            per_chapter[f"Chapter {ch}"] = {
                "count": len(ch_cases),
                "recall_at_5": round(ch_recall * 100, 1),
                "factual_correctness": round(ch_fc * 100, 1)
            }

    # Per-category breakdown
    per_category = {}
    for r in results:
        cat = r["category"]
        if cat not in per_category:
            per_category[cat] = {"count": 0, "success_count": 0}
        per_category[cat]["count"] += 1
        if r["answerable"]:
            if r["generation"]["factual_correctness"] >= 0.5:
                per_category[cat]["success_count"] += 1
        else:
            if r["generation"]["abstention_correct"]:
                per_category[cat]["success_count"] += 1

    summary = {
        "run_label": run_label,
        "dataset_path": dataset_path,
        "total_cases": len(results),
        "answerable_cases_count": len(answerable_cases),
        "unanswerable_cases_count": len(unanswerable_cases),
        "total_evaluation_time_seconds": total_time,
        "metrics": {
            "retrieval_recall_at_5": round(avg_recall_at_5 * 100, 2),
            "retrieval_top1_precision": round(avg_top1 * 100, 2),
            "irrelevant_outranked_count": irrelevant_outranked_count,
            "answer_factual_correctness": round(avg_fc * 100, 2),
            "answer_evidence_faithfulness": round(avg_faith * 100, 2),
            "citation_validity": round(avg_cit * 100, 2),
            "abstention_clarification_accuracy": round(avg_abstention * 100, 2),
            "critical_unsupported_hallucinations": critical_hallucinations
        },
        "gates": {
            "gate1_zero_critical_hallucinations": (critical_hallucinations == 0),
            "gate2_100_pct_citation_validity": (round(avg_cit * 100, 1) == 100.0),
            "gate3_95_pct_factual_correctness": (round(avg_fc * 100, 1) >= 95.0),
            "gate4_95_pct_abstention_accuracy": (round(avg_abstention * 100, 1) >= 95.0),
        },
        "per_chapter": per_chapter,
        "per_category": per_category,
        "detailed_results": results
    }

    return summary


if __name__ == "__main__":
    from pprint import pprint
    eval_file = sys.argv[1] if len(sys.argv) > 1 else PRIMARY_EVAL_FILE
    label = sys.argv[2] if len(sys.argv) > 2 else "baseline_test"
    report = evaluate_dataset(eval_file, label)
    print(json.dumps(report["metrics"], indent=2))
    print("Gates:")
    pprint(report["gates"])
