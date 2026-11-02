import sqlite3
conn = sqlite3.connect('data/sdc_platform.db')
print('Questions by lesson:')
for r in conn.execute('SELECT lesson_id, status, count(*) FROM questions GROUP BY lesson_id, status').fetchall():
    print(' ', r)

print('\nCheck for duplicate question texts in DB:')
dupes = conn.execute('SELECT text_sindhi, count(*) c FROM questions GROUP BY text_sindhi HAVING c > 1').fetchall()
print(f'Duplicates in questions table: {len(dupes)}')
for d in dupes[:10]:
    print(' ', d)

