import sys
sys.path.insert(0, '.')
import sqlite3
from src.services.sdc_rag_service import sdc_rag_service

res = sdc_rag_service.search_chunks('سيٽ')
with open('scratch/search_out.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total chunks returned: {len(res)}\n")
    for c in res:
        f.write(f"chunk_id: {c.get('chunk_id')}, subject_id: {c.get('subject_id')}, chapter_id: {c.get('chapter_id')}, topic: {c.get('topic_sindhi')}\n")
print("Done writing scratch/search_out.txt")
