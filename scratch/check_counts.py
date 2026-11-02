import sqlite3
conn = sqlite3.connect('data/sdc_platform.db')
for subj in ['math-6', 'science-6']:
    for ch in [1, 2, 3]:
        g = conn.execute('SELECT count(*) FROM sdc_glossary WHERE subject_id=? AND chapter_id=?', (subj, ch)).fetchone()[0]
        c = conn.execute('SELECT count(*) FROM sdc_chunks WHERE subject_id=? AND chapter_id=?', (subj, ch)).fetchone()[0]
        print(f'{subj} ch {ch}: glossary={g}, chunks={c}')

