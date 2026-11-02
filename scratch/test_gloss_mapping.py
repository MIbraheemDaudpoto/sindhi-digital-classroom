import sqlite3
import re

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

chapter_ranges = [
    (1, 5, 22),
    (2, 23, 36),
    (3, 37, 44),
    (4, 45, 58),
    (5, 59, 73),
    (6, 74, 82),
    (7, 83, 95),
    (8, 96, 112),
    (9, 113, 126),
    (10, 127, 141),
    (11, 142, 155),
    (12, 156, 170)
]

rows = cur.execute("SELECT id, pdf_page FROM sdc_glossary WHERE subject_id = 'science-6'").fetchall()
mapped = 0
for r in rows:
    pdf = r['pdf_page'] or ''
    m = re.search(r'PDF\s*(\d+)', pdf)
    if m:
        page_num = int(m.group(1))
        for ch_id, p_start, p_end in chapter_ranges:
            if p_start <= page_num <= p_end:
                mapped += 1
                break

print(f"Total science glossary: {len(rows)}, successfully mapped to chapters: {mapped}")
