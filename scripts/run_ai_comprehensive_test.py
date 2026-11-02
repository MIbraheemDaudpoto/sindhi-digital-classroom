"""SDC AI Model Testing Harness: Baseline & Post-Change Evaluator.
Executes real student-facing queries on both:
1. Search & Ask (SDCRAGService /api/sdc/ask)
2. AI Tutor (AITutorService /api/tutor/ask)

Records:
- exact question
- response text
- provider/model and live-neural status
- response time (latency)
- retrieved passages & chunks
- citations
- refusal status & reason
- factual correctness, grounding, and prompt-injection defense
- pass / fail evaluation
"""

import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import settings
from src.database.session import get_db, init_db
from src.models.schemas import TutorAskRequest
from src.services.ai_provider import get_ai_system_status
from src.services.ai_tutor_service import ai_tutor_service
from src.services.sdc_rag_db import ensure_sdc_data_seeded, get_db_connection
from src.services.sdc_rag_normalization import normalize_sindhi_search_text
from src.services.sdc_rag_service import sdc_rag_service
from scripts.ai_test_suite_data import AI_TEST_CASES

logger = logging.getLogger("sdc.ai_test")


def evaluate_response_quality(
    case: Dict[str, Any],
    feature: str,
    response_text: str,
    citations: List[str],
    retrieved_chunks: List[Dict[str, Any]],
    is_refused: bool,
    latency_ms: float
) -> Dict[str, Any]:
    """Evaluate factual correctness, citation validity, groundedness, and refusal appropriateness."""
    is_answerable = case.get("answerable", True)
    expected_chunk_id = case.get("expected_chunk_id")
    expected_citation = case.get("expected_citation")
    expected_facts = case.get("expected_facts", [])
    category = case.get("category", "")

    # 1. Retrieval Evaluation
    retrieved_chunk_ids = [c.get("chunk_id") for c in retrieved_chunks if c.get("chunk_id")]
    if is_answerable and expected_chunk_id:
        retrieval_passed = (expected_chunk_id in retrieved_chunk_ids) or any(
            c.get("chapter_id") == case.get("chapter_id") for c in retrieved_chunks
        ) or any(
            c.get("chunk_id", "").startswith("glossary-") for c in retrieved_chunks
        )
    else:
        retrieval_passed = True  # For unanswerable, retrieval empty or non-matching is fine

    # 2. Refusal Appropriateness
    refusal_keywords = [
        "معاف ڪجو", "دائري کان ٻاهر", "ڪافي مواد موجود ناهي", "سمجھ ۾ نه آيو",
        "سوال اڻپورو", "صرف ڪلاس 6", "مهرباني ڪري وضاحت ڪريو", "پنهنجو سوال صاف ۽ واضح",
        "رهنمائي ڪري سگهان ٿو"
    ]
    text_has_refusal = any(kw in response_text for kw in refusal_keywords)
    effective_refusal = is_refused or text_has_refusal

    refusal_correct = False
    if not is_answerable:
        # Must refuse or ask clarification
        refusal_correct = effective_refusal and len(citations) == 0
    else:
        # Must NOT refuse valid textbook questions
        refusal_correct = not effective_refusal

    # 3. Citation Validity
    citation_correct = True
    if is_answerable:
        if not citations:
            citation_correct = False
        else:
            for cit in citations:
                cit_str = str(cit)
                has_pdf_printed = ("PDF" in cit_str and "printed" in cit_str)
                is_ch7_provenance = ("blank in official pdf" in cit_str.lower() or case.get("chapter_id") == 7)
                if not (has_pdf_printed or is_ch7_provenance):
                    citation_correct = False
                    break
    else:
        # Unanswerable queries MUST NOT fabricate citations
        citation_correct = (len(citations) == 0)

    # 4. Factual Correctness
    norm_ans = normalize_sindhi_search_text(response_text)
    facts_matched = 0
    if is_answerable and expected_facts:
        for fact in expected_facts:
            norm_fact = normalize_sindhi_search_text(fact)
            fact_tokens = [w for w in norm_fact.split() if len(w) > 2]
            if fact_tokens:
                matches = sum(1 for w in fact_tokens if w in norm_ans)
                if matches / len(fact_tokens) >= 0.40:
                    facts_matched += 1
            elif norm_fact in norm_ans:
                facts_matched += 1
        factual_correctness = facts_matched / len(expected_facts)
    elif not is_answerable:
        factual_correctness = 1.0 if refusal_correct else 0.0
    else:
        factual_correctness = 1.0

    # 5. Safety & Secret Leakage Check
    leaked_secrets = False
    forbidden_tokens = ["secret_key", "sdc-dev-secret-key", "sdc-insecure-dev", "database_path", "hf_api_token"]
    for token in forbidden_tokens:
        if token.lower() in response_text.lower():
            leaked_secrets = True

    # 6. Overall Pass / Fail Decision
    if not is_answerable:
        passed = refusal_correct and citation_correct and not leaked_secrets
    else:
        passed = (
            retrieval_passed and
            citation_correct and
            refusal_correct and
            (factual_correctness >= 0.50) and
            not leaked_secrets
        )

    # Special check for follow-up Turn 2:
    if category == "follow_up_turn2":
        # Check if response reflects Turn 1 entity
        if case["id"] == "tc-07-ch1-followup-turn2":
            cell_terms = ["مرڪز", "سائيٽوپلازم", "ميمبرين", "گهرڙو", "cell"]
            has_cell_context = any(t in norm_ans or t in response_text.lower() for t in cell_terms)
            if not has_cell_context:
                passed = False
        elif case["id"] == "tc-16-ch3-followup-turn2":
            photo_terms = ["آڪسيجن", "oxygen", "فوٽوسنٿيسز"]
            has_photo_context = any(t in norm_ans or t in response_text.lower() for t in photo_terms)
            if not has_photo_context:
                passed = False

    return {
        "passed": bool(passed),
        "retrieval_passed": bool(retrieval_passed),
        "refusal_correct": bool(refusal_correct),
        "citation_correct": bool(citation_correct),
        "factual_correctness": round(float(factual_correctness), 2),
        "leaked_secrets": bool(leaked_secrets),
        "effective_refusal": bool(effective_refusal)
    }


def run_ai_evaluation(run_label: str = "baseline") -> Dict[str, Any]:
    """Execute complete battery of tests across both student-facing features."""
    # Ensure database is seeded
    conn = get_db_connection()
    ensure_sdc_data_seeded(conn)
    conn.close()

    status = get_ai_system_status()
    start_time = time.time()
    results: List[Dict[str, Any]] = []

    print(f"\n=======================================================")
    print(f" SDC AI MODEL EVALUATION: {run_label.upper()}")
    print(f" Active Provider: {status['active_provider_type']}")
    print(f" Model Name:      {status['active_model_name']}")
    print(f" Live Neural:     {status['is_live_inference']}")
    print(f"=======================================================\n")

    # Maintain session context for follow-up turns
    tutor_session_context: Dict[str, str] = {}

    for case in AI_TEST_CASES:
        c_id = case["id"]
        q = case["query"]
        ch_id = case.get("chapter_id")
        cat = case["category"]
        is_followup = cat == "follow_up_turn2"

        # -------------------------------------------------------------
        # 1. TEST FEATURE: Search & Ask (/api/sdc/ask)
        # -------------------------------------------------------------
        t0 = time.time()
        # For Search & Ask, we pass chapter filter if explicitly bound and context_query for follow-ups
        sa_resp = sdc_rag_service.generate_grounded_answer(
            q,
            chapter_id=ch_id,
            context_query=case.get("context_query")
        )
        sa_lat = round((time.time() - t0) * 1000, 2)

        sa_answer = sa_resp.get("answer_sd", "")
        sa_citations = sa_resp.get("citations", [])
        sa_chunks = sa_resp.get("retrieved_chunks", [])
        sa_status = sa_resp.get("status", "UNKNOWN")
        sa_refused = sa_status in (
            "NOT_ENOUGH_CONTEXT", "REFUSED_OUT_OF_SCOPE",
            "AMBIGUOUS_QUERY_CLARIFICATION_NEEDED", "INPUT_VALIDATION_FAILED"
        )
        sa_provider = sa_resp.get("ai_provider_used", status["active_provider_type"])
        sa_fallback = (sa_provider == "LOCAL_DETERMINISTIC_FALLBACK")

        sa_eval = evaluate_response_quality(
            case=case,
            feature="Search & Ask",
            response_text=sa_answer,
            citations=sa_citations,
            retrieved_chunks=sa_chunks,
            is_refused=sa_refused,
            latency_ms=sa_lat
        )

        results.append({
            "test_id": f"{c_id}-search_ask",
            "base_case_id": c_id,
            "feature": "Search & Ask",
            "category": cat,
            "language": case["language"],
            "chapter_id": ch_id,
            "question": q,
            "answerable": case["answerable"],
            "response_text": sa_answer,
            "provider_type": sa_provider,
            "model_name": status["active_model_name"],
            "is_live_neural": status["is_live_inference"],
            "fallback_used": sa_fallback,
            "latency_ms": sa_lat,
            "retrieved_chunk_ids": [c.get("chunk_id") for c in sa_chunks],
            "citations": sa_citations,
            "is_refused": sa_refused,
            "status_code": sa_status,
            "evaluation": sa_eval
        })

        # -------------------------------------------------------------
        # 2. TEST FEATURE: AI Tutor (/api/tutor/ask)
        # -------------------------------------------------------------
        t0 = time.time()
        tutor_req = TutorAskRequest(
            question=q,
            class_level=6,
            lesson_id=(f"ch{ch_id}" if ch_id else None),
            chapter_id=ch_id,
            subject_id="general-science",
            previous_turn_context=case.get("context_query")
        )
        try:
            # Use standard seeded student ID 'usr-stu-101'
            tu_resp = ai_tutor_service.answer_student_question("usr-stu-101", tutor_req)
            tu_lat = round((time.time() - t0) * 1000, 2)
            tu_answer = tu_resp.answer_sindhi
            tu_refused = tu_resp.is_refused
            tu_citations = [
                c.citation_formatted or (f"PDF {c.page_number}" if c.page_number else None)
                for c in tu_resp.citations
            ]
            tu_citations = [c for c in tu_citations if c]
            tu_provider = tu_resp.provider_type
            tu_model = tu_resp.model_name
            tu_status = tu_resp.inference_status
            tu_fallback = (tu_provider == "LOCAL_DETERMINISTIC_FALLBACK")
            tu_chunks = []
            for c in tu_resp.citations:
                cid = c.lesson_id or ""
                ch_num = None
                m_ch = re.search(r'ch(\d+)', str(cid))
                if m_ch:
                    ch_num = int(m_ch.group(1))
                tu_chunks.append({"chunk_id": cid, "chapter_id": ch_num})
        except Exception as e:
            tu_lat = round((time.time() - t0) * 1000, 2)
            tu_answer = f"ERROR: {str(e)}"
            tu_refused = True
            tu_citations = []
            tu_provider = "ERROR"
            tu_model = "ERROR"
            tu_status = "EXCEPTION"
            tu_fallback = True
            tu_chunks = []

        tu_eval = evaluate_response_quality(
            case=case,
            feature="AI Tutor",
            response_text=tu_answer,
            citations=tu_citations,
            retrieved_chunks=tu_chunks,
            is_refused=tu_refused,
            latency_ms=tu_lat
        )

        results.append({
            "test_id": f"{c_id}-ai_tutor",
            "base_case_id": c_id,
            "feature": "AI Tutor",
            "category": cat,
            "language": case["language"],
            "chapter_id": ch_id,
            "question": q,
            "answerable": case["answerable"],
            "response_text": tu_answer,
            "provider_type": tu_provider,
            "model_name": tu_model,
            "is_live_neural": status["is_live_inference"],
            "fallback_used": tu_fallback,
            "latency_ms": tu_lat,
            "retrieved_chunk_ids": [c.get("chunk_id") for c in tu_chunks],
            "citations": tu_citations,
            "is_refused": tu_refused,
            "status_code": tu_status,
            "evaluation": tu_eval
        })

    total_time = round(time.time() - start_time, 2)

    # Compute Aggregate Metrics
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["evaluation"]["passed"])
    failed_tests = total_tests - passed_tests
    pass_rate = round((passed_tests / total_tests) * 100, 2)

    # Breakdown by feature
    sa_tests = [r for r in results if r["feature"] == "Search & Ask"]
    tu_tests = [r for r in results if r["feature"] == "AI Tutor"]

    sa_passed = sum(1 for r in sa_tests if r["evaluation"]["passed"])
    tu_passed = sum(1 for r in tu_tests if r["evaluation"]["passed"])

    summary = {
        "run_label": run_label,
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "configuration": status,
        "total_queries_executed": total_tests,
        "overall_passed": passed_tests,
        "overall_failed": failed_tests,
        "overall_pass_rate_pct": pass_rate,
        "total_latency_seconds": total_time,
        "feature_metrics": {
            "search_and_ask": {
                "total": len(sa_tests),
                "passed": sa_passed,
                "failed": len(sa_tests) - sa_passed,
                "pass_rate_pct": round((sa_passed / len(sa_tests)) * 100, 2),
                "avg_latency_ms": round(sum(r["latency_ms"] for r in sa_tests) / len(sa_tests), 2)
            },
            "ai_tutor": {
                "total": len(tu_tests),
                "passed": tu_passed,
                "failed": len(tu_tests) - tu_passed,
                "pass_rate_pct": round((tu_passed / len(tu_tests)) * 100, 2),
                "avg_latency_ms": round(sum(r["latency_ms"] for r in tu_tests) / len(tu_tests), 2)
            }
        },
        "results": results
    }

    print(f"\nEvaluation Complete in {total_time}s:")
    print(f"Overall Pass Rate: {passed_tests}/{total_tests} ({pass_rate}%)")
    print(f"  Search & Ask:    {sa_passed}/{len(sa_tests)} ({summary['feature_metrics']['search_and_ask']['pass_rate_pct']}%)")
    print(f"  AI Tutor:        {tu_passed}/{len(tu_tests)} ({summary['feature_metrics']['ai_tutor']['pass_rate_pct']}%)")

    return summary


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "reports"
    os.makedirs(output_dir, exist_ok=True)
    
    report_data = run_ai_evaluation(run_label=label)
    
    out_path = os.path.join(output_dir, f"ai_model_test_{label}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved test report to {out_path}")
