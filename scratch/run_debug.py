import sys
import os
import traceback

sys.path.insert(0, os.path.abspath("."))

try:
    from src.services.sdc_rag_service import sdc_rag_service
    res = sdc_rag_service.generate_grounded_answer("گهرڙو (Cell) ڇا آهي؟")
    with open("scratch/res.txt", "w", encoding="utf-8") as f:
        f.write(f"STATUS: {res['status']}\n")
        f.write(f"PROVIDER: {res.get('ai_provider_used')}\n")
        f.write(f"ANSWER: {res['answer_sd']}\n")
    print("SUCCESS")
except Exception as e:
    with open("scratch/res_err.txt", "w", encoding="utf-8") as f:
        traceback.print_exc(file=f)
    print("FAILED")
