import sqlite3

conn = sqlite3.connect('data/sdc_platform.db')
cur = conn.cursor()
cur.execute("SELECT count(*) FROM questions WHERE options_json LIKE '%غير ضروري معلومات%' OR text_sindhi LIKE '%اسلام جو ڪهڙو ڪردار%'")
print('Bad whisper questions:', cur.fetchone()[0])
