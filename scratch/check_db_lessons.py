import sqlite3
conn = sqlite3.connect('data/sdc_platform.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, course_id, unit_number, title_sindhi, status FROM lessons WHERE course_id = 'crs-math-6'").fetchall()
print('Math lessons count:', len(rows))
for r in rows:
    print(r['id'], r['unit_number'], r['status'])

