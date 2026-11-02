import json
from pathlib import Path
from src.services.sindhi_nlp import compute_grounding_similarity, normalize_sindhi_text, tokenize_sindhi_query

with open("data/stbb_math_6_complete.json", "r", encoding="utf-8") as f:
    data = json.load(f)

chunks = data["chunks"]
glossary = data["glossary"]

test_queries = [
    "سيٽ ڇا آهي؟",
    "خالي سيٽ جي وصف ڇا آهي؟",
    "سڄا عدد ڇا آهن؟",
    "BODMAS اصول ڇا آهي؟",
    "نسبت ۽ تناسب ۾ ڇا فرق آهي؟",
    "عمودي وچولي ليڪ ڇا آهي؟",
    "احاطو ڇا آهي؟"
]

with open("scratch/test_math_match.log", "w", encoding="utf-8") as out:
    for q in test_queries:
        norm_q = normalize_sindhi_text(q, strip_diacritics=True)
        best_chunk = None
        best_sim = 0.0
        for c in chunks:
            cand_text = c["summary_sd"] + " " + c["topic_title_sd"] + " " + c.get("topic_title_en", "")
            sim = compute_grounding_similarity(norm_q, cand_text)
            for t in tokenize_sindhi_query(norm_q):
                if t in c["topic_title_sd"]:
                    sim = max(sim, 0.85)
            if sim > best_sim:
                best_sim = sim
                best_chunk = c

        for g in glossary:
            if g["term_sd"] in q:
                sim = 0.90
                if sim > best_sim:
                    best_sim = sim
                    best_chunk = {"topic_title_sd": g["term_sd"], "summary_sd": g["definition_sd"], "citation_formatted": g["citation"]}

        out.write(f"Query: {q}\n")
        out.write(f"  Best Match: {best_chunk['topic_title_sd'] if best_chunk else 'None'} (Score: {best_sim:.2f})\n")
        out.write(f"  Citation: {best_chunk.get('citation_formatted') if best_chunk else 'None'}\n")
print("Done writing results")

