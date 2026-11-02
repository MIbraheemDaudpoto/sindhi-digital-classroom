import sqlite3

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Query for "سيٽ"
cur.execute('''
    SELECT chunk_id, bm25(sdc_chunks_fts) as score
    FROM sdc_chunks_fts
    WHERE sdc_chunks_fts MATCH '"سيٽ"'
    ORDER BY score ASC
    LIMIT 10
''')
rows = cur.fetchall()

with open('scratch/test_set_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Results for 'سيٽ' (total {len(rows)}):\n")
    for r in rows:
        cid = r["chunk_id"]
        score = r["score"]
        c_info = cur.execute("SELECT topic_title_sd, subject_id, chapter_id FROM sdc_chunks WHERE chunk_id = ?", (cid,)).fetchone()
        f.write(f"[{c_info['subject_id']}] ch{c_info['chapter_id']} | ID={cid} | score={score:.3f} | {c_info['topic_title_sd']}\n")

print("Done. Output written to scratch/test_set_output.txt")
