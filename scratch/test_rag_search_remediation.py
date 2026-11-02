import sys
sys.path.insert(0, ".")
from src.services.sdc_rag_service import sdc_rag_service
import json

tests = [
    ("Pure Math Query 'سيٽ'", {"query": "سيٽ", "subject_id": None}),
    ("Math Query with math subject 'سيٽ'", {"query": "سيٽ", "subject_id": "math-6"}),
    ("Science Satellite Query 'پاڪ سيٽ'", {"query": "پاڪ سيٽ", "subject_id": None}),
    ("Science Query 'فوٽوسنٿيسز'", {"query": "فوٽوسنٿيسز", "subject_id": "science-6"}),
    ("Math Integers Query 'سڄا عدد'", {"query": "سڄا عدد", "subject_id": "math-6"}),
]

results = []
for name, params in tests:
    chunks = sdc_rag_service.search_chunks(params["query"], subject_id=params["subject_id"], limit=5)
    glossary = sdc_rag_service.search_glossary(params["query"], subject_id=params["subject_id"], limit=3)
    chunk_summaries = [f"[{c.get('subject_id', 'sci')}] ch{c['chapter_id']} {c['chunk_id']}: {c['topic_title_sd']}" for c in chunks]
    glossary_summaries = [f"[{g.get('subject_id', 'sci')}] {g['term_sd']} ({g['term_en']})" for g in glossary]
    results.append({
        "test": name,
        "query": params["query"],
        "subject_filter": params["subject_id"],
        "chunks_found": len(chunks),
        "top_chunks": chunk_summaries,
        "glossary_matches": glossary_summaries
    })

with open("scratch/rag_search_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Completed RAG search tests. Written to scratch/rag_search_test_results.json")
