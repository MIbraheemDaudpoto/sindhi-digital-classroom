import sqlite3, sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row

chapters = conn.execute('SELECT chapter_id, COUNT(*) as cnt FROM sdc_chunks GROUP BY chapter_id ORDER BY chapter_id').fetchall()
print('Science Chapters in sdc_chunks:')
for c in chapters:
    cid = c['chapter_id']
    cnt = c['cnt']
    row = conn.execute('SELECT topic_title_sd, topic_title_en FROM sdc_chunks WHERE chapter_id = ? LIMIT 1', (cid,)).fetchone()
    print(f"  Ch {cid}: {cnt} chunks | {row['topic_title_sd']} ({row['topic_title_en']})")

lessons = conn.execute("SELECT id, course_id, unit_number, title_sindhi, title_english FROM lessons ORDER BY course_id, unit_number").fetchall()
print("\nAll Lessons in lessons table:")
for l in lessons:
    q_cnt = conn.execute("SELECT COUNT(*) FROM questions WHERE lesson_id = ? AND status = 'APPROVED'", (l['id'],)).fetchone()[0]
    print(f"  {l['id']} ({l['course_id']} U{l['unit_number']}): {l['title_sindhi']} | {l['title_english']} -> {q_cnt} approved questions")

