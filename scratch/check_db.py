import sqlite3
import sys

con = sqlite3.connect('data/sdc_platform.db')
integrity = con.execute('PRAGMA integrity_check').fetchall()
print('Integrity:', integrity)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f'Total tables: {len(tables)}')
for t in ['questions', 'quiz_attempts', 'lessons', 'progress', 'sdc_chunks', 'sdc_glossary', 'sdc_videos', 'users']:
    if t in tables:
        count = con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
        print(f'{t}: {count}')
con.close()

