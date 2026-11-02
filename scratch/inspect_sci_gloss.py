import sqlite3
import json

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

sci_gloss = [dict(r) for r in cur.execute("SELECT term_sd, term_en, definition_sd, pdf_page, citation_formatted FROM sdc_glossary WHERE subject_id = 'science-6' LIMIT 10").fetchall()]
with open('scratch/sci_gloss_sample.json', 'w', encoding='utf-8') as f:
    json.dump(sci_gloss, f, ensure_ascii=False, indent=2)

print('Dumped 10 sci gloss')
