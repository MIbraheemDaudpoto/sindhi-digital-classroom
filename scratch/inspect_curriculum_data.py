import sqlite3
import json

conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('PRAGMA table_info(sdc_chunks)')
chunks_cols = [dict(r) for r in cur.fetchall()]

cur.execute('PRAGMA table_info(sdc_glossary)')
glossary_cols = [dict(r) for r in cur.fetchall()]

chunks = [dict(r) for r in cur.execute('SELECT * FROM sdc_chunks LIMIT 5').fetchall()]
glossary = [dict(r) for r in cur.execute('SELECT * FROM sdc_glossary WHERE chapter_id IS NOT NULL LIMIT 5').fetchall()]

with open('scratch/curriculum_sample.json', 'w', encoding='utf-8') as f:
    json.dump({
        'chunks_cols': chunks_cols,
        'glossary_cols': glossary_cols,
        'chunks': chunks,
        'glossary': glossary
    }, f, ensure_ascii=False, indent=2)

print('Sample dumped to scratch/curriculum_sample.json')
