import sys, os
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from src.services.sdc_rag_db import get_db_connection
conn = get_db_connection()
rows = conn.execute("SELECT chunk_id, topic_title_sd, summary_sd FROM sdc_chunks WHERE chapter_id = 1").fetchall()
for r in rows:
    print(r['chunk_id'], "|", r['topic_title_sd'])
    print("  ", r['summary_sd'][:80])
