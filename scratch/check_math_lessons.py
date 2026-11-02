import sqlite3

con = sqlite3.connect('data/sdc_platform.db')
con.row_factory = sqlite3.Row
rows = con.execute("SELECT id, course_id, status FROM lessons WHERE course_id = 'crs-math-6'").fetchall()
print('Math lessons in DB count:', len(rows))
for r in rows[:5]:
    print(dict(r))

# Check all courses and lesson counts
all_crs = con.execute("SELECT course_id, status, count(*) FROM lessons GROUP BY course_id, status").fetchall()
print('All lessons grouped:')
for a in all_crs:
    print(dict(a))
con.close()

