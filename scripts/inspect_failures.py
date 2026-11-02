import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

path = sys.argv[1] if len(sys.argv) > 1 else 'reports/ai_model_test_post_change.json'
with open(path, 'r', encoding='utf-8') as f:
    d = json.load(f)

print(f"REPORT: {d['run_label']} | Total: {d['total_queries_executed']}, Passed: {d['overall_passed']}, Failed: {d['overall_failed']} ({d['overall_pass_rate_pct']}%)")
print(f"Search & Ask: {d['feature_metrics']['search_and_ask']['passed']}/{d['feature_metrics']['search_and_ask']['total']} ({d['feature_metrics']['search_and_ask']['pass_rate_pct']}%)")
print(f"AI Tutor:     {d['feature_metrics']['ai_tutor']['passed']}/{d['feature_metrics']['ai_tutor']['total']} ({d['feature_metrics']['ai_tutor']['pass_rate_pct']}%)")
print("=" * 80)

for r in d['results']:
    ev = r['evaluation']
    if not ev['passed']:
        reason = []
        if not ev['retrieval_passed']: reason.append("RETRIEVAL")
        if not ev['refusal_correct']: reason.append("REFUSAL")
        if not ev['citation_correct']: reason.append("CITATION")
        if ev['factual_correctness'] < 0.5: reason.append(f"FACTS({ev['factual_correctness']})")
        if ev.get('leaked_secrets'): reason.append("SECURITY")
        
        print(f"FAIL: [{r['feature']}] {r['base_case_id']} -> {','.join(reason)}")
        print(f"   Q: {r['question']}")
        print(f"   Citations: {r['citations']}")
        print(f"   Ans: {r['response_text'][:100]}...")
        print("-" * 60)
